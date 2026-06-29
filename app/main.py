import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from google import genai

from app.config import settings
from app.logging_config import setup_logging
from app.routers import admin, auth, documents, web, ws
from app.services.connection_manager import ConnectionManager
from app.services.rate_limit import RateLimiter

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Uygulama başlıyor — Gemini client oluşturuluyor")
    app.state.genai_client = genai.Client(api_key=settings.gemini_api_key)
    app.state.connection_manager = ConnectionManager()
    app.state.rate_limiter = RateLimiter(window=10.0, max_events=5)
    yield
    logger.info("Uygulama kapanıyor — açık bağlantılar bilgilendiriliyor")
    await app.state.connection_manager.close_all(code=1001)
    logger.info("Uygulama kapandı")


app = FastAPI(lifespan=lifespan)

# React dev sunucusu farklı origin'den (5173) REST çağırır → CORS gerekir.
# allowed_origins (D2 validator'ının yeni müşterisi) hem CORS'u hem WS origin kontrolünü besler.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(web.router)
app.include_router(ws.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(documents.router)

# Prod: derlenmiş React'in statik asset'leri (index.html'i web.router servis ediyor).
# Router'lardan SONRA mount edilir ki /auth, /ws gibi API yolları gölgelenmesin.
_assets = Path("frontend/dist/assets")
if _assets.exists():
    app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")
