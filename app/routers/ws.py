import asyncio
import json
import logging
import uuid

from fastapi import APIRouter
from fastapi import WebSocket
from pydantic import ValidationError
from starlette.websockets import WebSocketDisconnect

from app.config import settings
from app.db.repository import ConversationRepository
from app.logging_config import ConnectionLoggerAdapter
from app.schemas.messages import (
    ChunkMessage,
    ConversationMessage,
    DoneMessage,
    ErrorMessage,
    SystemMessage,
    UserMessage,
)
from app.services.chat_service import ChatService, RateLimitExceeded
from app.services.llm_provider import GeminiProvider
from google.genai.errors import ClientError, ServerError

IDLE_TIMEOUT = 30.0

router = APIRouter()
logger = logging.getLogger(__name__)


async def resolve_conversation(websocket, repo, ws_logger) -> uuid.UUID:
    """conversation_id query'den gelirse ve geçerliyse onu kullan; yoksa yeni konuşma aç ve id'yi bildir."""
    raw = websocket.query_params.get("conversation_id")
    if raw:
        try:
            cid = uuid.UUID(raw)
        except ValueError:
            cid = None
        if cid and await repo.exists(cid):
            ws_logger.info("Mevcut konuşma yüklendi")
            return cid

    cid = await repo.create_conversation()
    await websocket.send_json(ConversationMessage(conversation_id=str(cid)).model_dump())
    ws_logger.info("Yeni konuşma açıldı")
    return cid


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    origin = websocket.headers.get("origin")
    if origin not in settings.allowed_origins:
        logger.warning(f"Reddedilen origin: {origin}")
        await websocket.close(code=1008)
        return

    access_token = websocket.query_params.get("token")
    if access_token != settings.app_access_token:
        logger.warning("Kullanıcı yanlış token ile bağlandı")
        await websocket.close(code=1008)
        return

    await websocket.accept()

    connection_id = str(uuid.uuid4())
    ws_logger = ConnectionLoggerAdapter(logger, {"connection_id": connection_id})

    genai_client = websocket.app.state.genai_client
    manager = websocket.app.state.connection_manager
    provider = GeminiProvider(client=genai_client, model=settings.gemini_model)
    repo = ConversationRepository()

    # conversation_id: istemciden gelirse (reconnect) onu kullan, yoksa yeni konuşma aç.
    # connection_id her bağlantıda yeni (geçici); conversation_id kalıcı (geçmişin anahtarı).
    conversation_id = await resolve_conversation(websocket, repo, ws_logger)

    service = ChatService(
        provider=provider,
        history_window=settings.history_window,
        repo=repo,
        conversation_id=conversation_id,
    )

    manager.register(connection_id, websocket)

    try:
        ws_logger.info(f"Kullanıcı bağlandı (conversation={conversation_id})")
        while True:
            try:
                raw = await websocket.receive_json()
                user_msg = UserMessage.model_validate(raw)
            except json.JSONDecodeError:
                await websocket.send_json(ErrorMessage(content="Geçersiz mesaj formatı").model_dump())
                continue
            except ValidationError:
                await websocket.send_json(ErrorMessage(content="Mesaj şeması hatalı").model_dump())
                continue

            data = user_msg.content

            if not data.strip():
                await websocket.send_json(SystemMessage(content="Boş mesaj gönderemezsin").model_dump())
                continue
            if len(data) > 2000:
                await websocket.send_json(SystemMessage(content="Çok uzun mesaj atamazsınız").model_dump())
                ws_logger.warning("Karakter aşımı")
                continue
            if "\x00" in data:
                await websocket.send_json(SystemMessage(content="Bu tarz mesajlar atamazsınız").model_dump())
                ws_logger.warning("Karakter uyumsuzluğu")
                continue

            try:
                service.check_rate_limit()
            except RateLimitExceeded as exc:
                await websocket.send_json(
                    SystemMessage(content="Çok hızlı mesaj gönderiyorsun, biraz yavaşla.").model_dump()
                )
                ws_logger.warning(f"Rate limit aşıldı: {exc}")
                continue

            manager.record_message()
            ws_logger.info(f"Modele gönderilen turn sayısı: {await service.turns_in_window()}")

            try:
                loop = asyncio.get_running_loop()
                async with asyncio.timeout(IDLE_TIMEOUT) as timeout:
                    async for chunk in service.stream_response(data.strip()):
                        await websocket.send_json(ChunkMessage(content=chunk).model_dump())
                        timeout.reschedule(loop.time() + IDLE_TIMEOUT)
                await websocket.send_json(DoneMessage().model_dump())
            except asyncio.TimeoutError:
                ws_logger.warning("Gemini yanıt akışı durdu (idle timeout).")
                await websocket.send_json(ErrorMessage(content="Tekrar deneyiniz.").model_dump())
                continue
            except ServerError as error:
                if error.code == 503:
                    ws_logger.warning("Google API 503 yoğunluk hatası verdi.")
                    await websocket.send_json(ErrorMessage(content="Yoğunluk hatası").model_dump())
                else:
                    ws_logger.error(f"Google API sunucu hatası ({error.code}): {error}")
                    await websocket.send_json(ErrorMessage(content="Sunucu hatası").model_dump())
                continue
            except ClientError as error:
                if error.code == 429:
                    ws_logger.warning("Google API 429 kota aşımı.")
                    await websocket.send_json(ErrorMessage(content="Kotam doldu").model_dump())
                else:
                    ws_logger.error(f"Google API istemci hatası ({error.code}): {error}")
                    await websocket.send_json(ErrorMessage(content="İsteğimi anlayamadım.").model_dump())
                continue

    except WebSocketDisconnect:
        ws_logger.info("Kullanıcı ayrıldı")
    except Exception:
        ws_logger.exception("Beklenmedik bir hata oluştu")
        try:
            await websocket.send_json(
                ErrorMessage(content=f"Hata oluştu (ID: {connection_id}). Lütfen tekrar deneyin.").model_dump()
            )
            await websocket.close(code=1011)
        except RuntimeError:
            ws_logger.warning("Bağlantı zaten kapalı")
    finally:
        manager.unregister(connection_id)
        ws_logger.info("Bağlantı sonlandı")
