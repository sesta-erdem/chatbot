import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from google import genai

from app.config import settings
from app.logging_config import setup_logging
from app.routers import web, ws
from app.services.connection_manager import ConnectionManager

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Uygulama başlıyor — Gemini client oluşturuluyor")
    app.state.genai_client = genai.Client(api_key=settings.gemini_api_key)
    app.state.connection_manager = ConnectionManager()
    yield
    logger.info("Uygulama kapanıyor — açık bağlantılar bilgilendiriliyor")
    await app.state.connection_manager.close_all(code=1001)
    logger.info("Uygulama kapandı")


app = FastAPI(lifespan=lifespan)
app.include_router(web.router)
app.include_router(ws.router)
