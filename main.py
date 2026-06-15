import asyncio
import json
import logging
import time
import uuid
from typing import Literal

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError
from pydantic import BaseModel, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.websockets import WebSocketDisconnect


class ChunkMessage(BaseModel):
    type: Literal["chunk"] = "chunk"
    content: str


class DoneMessage(BaseModel):
    type: Literal["done"] = "done"


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    content: str


class SystemMessage(BaseModel):
    type: Literal["system"] = "system"
    content: str


class UserMessage(BaseModel):
    type: Literal["user_message"]
    content: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    log_level: str = "INFO"
    app_access_token: str
    allowed_origins: list[str]

    @field_validator("gemini_api_key", mode="after")
    @classmethod
    def gemini_api_key_validator(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("gemini_api_key is empty")
        return value

    @field_validator("log_level", mode="after")
    @classmethod
    def log_level_validator(cls, value: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        value = value.upper()
        if value not in valid_levels:
            raise ValueError("log_level must be one of {}".format(valid_levels))
        return value

    @field_validator("app_access_token", mode="after")
    @classmethod
    def app_access_token_validator(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("app_access_token is empty")
        return value

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",")]
        return value


class ConnectionLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        connection_id = self.extra.get("connection_id", "-")
        return f"{connection_id}: {msg}", kwargs


settings = Settings()

RATE_LIMIT_WINDOW = 10.0
RATE_LIMIT_MAX_MESSAGES = 5
IDLE_TIMEOUT = 30.0

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

client = genai.Client(api_key=settings.gemini_api_key)

app = FastAPI()

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse(request=request, name="item.html")


@app.websocket("/ws")
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

    message_timestamps: list[float] = []

    connection_id = str(uuid.uuid4())
    ws_logger = ConnectionLoggerAdapter(logger, {"connection_id": connection_id})

    chat = client.aio.chats.create(
        model=settings.gemini_model,
        config=types.GenerateContentConfig(
            system_instruction=(
                "Sen sabırlı, deneyimli bir yazılım eğitmenisin. "
                "Karmaşık konuları gündelik benzetmelerle anlatırsın.\n\n"
                "Cevabının uzunluğunu ve biçimini soruya göre ayarla. "
                "Selamlaşma, sohbet veya basit sorulara KISA ve doğal cevap ver — başlık, liste, "
                "kod bloğu kullanma, sadece birkaç cümle yeter. "
                "Yalnızca konu gerçekten teknik veya çok parçalıysa Markdown biçimlendirme "
                "(başlık, kod bloğu, kalın vurgu) ve adım adım açıklama kullan.\n\n"
                "Kullanıcı kod gönderirse önce ne yaptığını açıkla, sonra varsa hatayı göster, "
                "en son iyileştirme öner.\n\n"
                "Emin olmadığın bilgilerde tahmin yürütme; 'bundan emin değilim' de. "
                "Kütüphane, fonksiyon veya sürüm adı uydurma. "
                "Uydurma bir cevap vermektense 'bilmiyorum' demek daha iyidir."
            ),
            temperature=0.2,
            max_output_tokens=3000,
        ),
    )

    try:
        ws_logger.info("Kullanıcı bağlandı")
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

            now = time.monotonic()
            message_timestamps = [t for t in message_timestamps if t > now - RATE_LIMIT_WINDOW]
            if len(message_timestamps) >= RATE_LIMIT_MAX_MESSAGES:
                await websocket.send_json(
                    SystemMessage(content="Çok hızlı mesaj gönderiyorsun, biraz yavaşla.").model_dump()
                )
                ws_logger.warning(f"Rate limit aşıldı: pencerede {len(message_timestamps)} mesaj")
                continue
            message_timestamps.append(now)

            try:
                loop = asyncio.get_running_loop()
                async with asyncio.timeout(IDLE_TIMEOUT) as timeout:
                    async for chunk in await chat.send_message_stream(data.strip()):
                        if chunk.text:
                            await websocket.send_json(ChunkMessage(content=chunk.text).model_dump())
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
                    await websocket.send_json(ErrorMessage(content="İsteğini anlayamadım.").model_dump())
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
        ws_logger.info("Bağlantı sonlandı")
