from fastapi import FastAPI, WebSocket, Request
from fastapi.templating import Jinja2Templates
from google import genai
from fastapi.responses import HTMLResponse
from starlette.websockets import WebSocketDisconnect
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging
from pydantic import field_validator
import uuid




class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    log_level: str = "INFO"

    @field_validator("gemini_api_key",  mode = 'after')
    @classmethod
    def gemini_api_key_validator(cls, value : str) -> str:
        if not value.strip():
            raise ValueError("gemini_api_key is Empty")
        return value

    @field_validator("log_level", mode = 'after')
    @classmethod
    def log_level_validator(cls, value : str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        value = value.upper()
        if value not in valid_levels:
            raise ValueError("log_level must be one of {}".format(valid_levels))
        return value


class ConnectionLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        connection_id = self.extra.get("connection_id", "-")
        return f'{connection_id}: {msg}', kwargs





settings = Settings()


logging.basicConfig(
    level = getattr(logging, settings.log_level),
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)





client = genai.Client(api_key=settings.gemini_api_key)

app = FastAPI()

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse(
        request=request, name="item.html"
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connection_id = str(uuid.uuid4())
    ws_logger = ConnectionLoggerAdapter(logger, {"connection_id": connection_id})

    chat = client.aio.chats.create(model=settings.gemini_model)

    try:
        ws_logger.info("Kullancı bağlandı")
        while True:
            data = await websocket.receive_text()
            async for chunk in await chat.send_message_stream(data):
                if chunk.text:
                    await websocket.send_text(chunk.text)

    except WebSocketDisconnect:

        ws_logger.info("Kullanıcı Ayrıldı")

    except Exception:
        ws_logger.exception("Beklenmedik bir hata oluştu")
        try:
            await websocket.send_text(
                f"Hata oluştu (ID: {connection_id}). Lütfen tekrar deneyin."
            )
            await websocket.close(code=1011)
        except RuntimeError:
            ws_logger.warning("Bağlantı zaten kapalı")
    finally:
        ws_logger.info("Bağlantı sonlandı")