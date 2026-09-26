import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from google import genai
from prometheus_client import make_asgi_app

from api.health import router as health_router
from api.websocket import router as websocket_router
from config import Settings
from core.database import create_pool
from core.logging import configure_logging
from providers.gemini import GeminiProvider


settings = Settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await create_pool(settings.database_url)
    gemini_client = genai.Client(api_key=settings.gemini_api_key)

    app.state.settings = settings
    app.state.pool = pool
    app.state.chat_provider = GeminiProvider(
        client=gemini_client.aio,
        model=settings.gemini_model,
    )

    try:
        yield
    finally:
        logger.info("Application shutdown başladı")

        await pool.close()
        logger.info("PostgreSQL pool kapatıldı")

        await gemini_client.aio.aclose()
        gemini_client.close()
        logger.info("Gemini client kapatıldı")


app = FastAPI(lifespan=lifespan)
app.include_router(websocket_router)
app.include_router(health_router)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="item.html",
    )
