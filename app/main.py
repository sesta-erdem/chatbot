import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from google import genai

from app.config import settings
from app.logging_config import setup_logging
from app.routers import web, ws

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Uygulama başlıyor — Gemini client oluşturuluyor")
    app.state.genai_client = genai.Client(api_key=settings.gemini_api_key)
    yield
    logger.info("Uygulama kapanıyor")


app = FastAPI(lifespan=lifespan)
app.include_router(web.router)
app.include_router(ws.router)
