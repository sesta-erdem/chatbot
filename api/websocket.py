import json
import logging
import uuid

from fastapi import APIRouter, WebSocket
from pydantic import ValidationError
from starlette.websockets import WebSocketDisconnect

from core.logging import ConnectionLoggerAdapter
from core.metrics import ConnectionMetrics, GenerationMetrics
from models import (
    ChunkMessage,
    DoneMessage,
    ErrorMessage,
    SystemMessage,
    UserMessage,
)
from providers.errors import (
    ProviderError,
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderUnavailableError,
)
from repositories.chat import ChatRepository
from services.chat import ChatService
from services.rate_limit import SlidingWindowRateLimiter


router = APIRouter()
logger = logging.getLogger(__name__)


_PROVIDER_ERROR_RESPONSES = {
    ProviderUnavailableError: ("unavailable", "Sunucu yoğun."),
    ProviderRateLimitError: ("rate_limit", "Kota doldu."),
    ProviderRequestError: ("request", "İstek işlenemedi."),
}


def _validate_user_text(text: str, max_chars: int) -> str | None:
    if not text:
        return "Boş mesaj gönderemezsin"
    if len(text) > max_chars:
        return "Mesaj çok uzun"
    if "\x00" in text:
        return "Geçersiz karakter"
    return None


def _provider_error_response(error: ProviderError) -> tuple[str, str]:
    return _PROVIDER_ERROR_RESPONSES.get(
        type(error),
        ("unknown", "Sunucu hatası."),
    )


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    settings = websocket.app.state.settings

    origin = websocket.headers.get("origin")
    if origin not in settings.allowed_origins:
        logger.warning("Reddedilen origin: %s", origin)
        await websocket.close(code=1008)
        return

    access_token = websocket.query_params.get("token")
    if access_token != settings.app_access_token:
        logger.warning("Kullanıcı yanlış token ile bağlandı")
        await websocket.close(code=1008)
        return

    await websocket.accept()

    connection_metrics = ConnectionMetrics()
    connection_id = str(uuid.uuid4())
    ws_logger = ConnectionLoggerAdapter(
        logger,
        {"connection_id": connection_id},
    )

    try:
        repository = ChatRepository(websocket.app.state.pool)
        rate_limiter = SlidingWindowRateLimiter(
            window_seconds=settings.rate_limit_window,
            max_messages=settings.rate_limit_max_messages,
        )

        conversation_id = await repository.create_conversation(owner_id=1)
        chat_service = ChatService(
            provider=websocket.app.state.chat_provider,
            repository=repository,
            conversation_id=conversation_id,
            history_window=settings.history_window,
            idle_timeout=settings.idle_timeout,
        )

        ws_logger.info("Kullanıcı bağlandı")

        while True:
            try:
                raw = await websocket.receive_json()
                user_msg = UserMessage.model_validate(raw)
            except json.JSONDecodeError:
                await websocket.send_json(
                    ErrorMessage(content="Geçersiz mesaj formatı").model_dump()
                )
                continue
            except ValidationError:
                await websocket.send_json(
                    ErrorMessage(content="Mesaj şeması hatalı").model_dump()
                )
                continue

            data = user_msg.content.strip()
            validation_error = _validate_user_text(
                data,
                settings.max_input_chars,
            )
            if validation_error:
                await websocket.send_json(
                    SystemMessage(content=validation_error).model_dump()
                )
                continue

            if not rate_limiter.allow():
                await websocket.send_json(
                    SystemMessage(
                        content="Çok hızlı mesaj gönderiyorsun."
                    ).model_dump()
                )
                continue

            generation_metrics = GenerationMetrics()

            try:
                async for chunk in chat_service.stream_reply(data):
                    generation_metrics.record_first_token()
                    await websocket.send_json(
                        ChunkMessage(content=chunk).model_dump()
                    )

                generation_metrics.record_success()
                await websocket.send_json(DoneMessage().model_dump())

            except TimeoutError:
                ws_logger.warning("Provider idle timeout")
                generation_metrics.record_timeout()
                await websocket.send_json(
                    ErrorMessage(
                        content="Yanıt zaman aşımına uğradı."
                    ).model_dump()
                )

            except ProviderError as error:
                category, client_message = _provider_error_response(error)
                generation_metrics.record_provider_error(category)

                ws_logger.warning(
                    "Provider hatası: %s",
                    category,
                    exc_info=category == "unknown",
                )

                await websocket.send_json(
                    ErrorMessage(content=client_message).model_dump()
                )

            finally:
                generation_metrics.finish()

    except WebSocketDisconnect:
        ws_logger.info("Kullanıcı ayrıldı")

    except Exception:
        ws_logger.exception("Beklenmedik hata")

        try:
            await websocket.send_json(
                ErrorMessage(
                    content=f"Hata oluştu. ID: {connection_id}"
                ).model_dump()
            )
            await websocket.close(code=1011)
        except RuntimeError:
            pass

    finally:
        connection_metrics.finish()
        ws_logger.info("Bağlantı sonlandı")
