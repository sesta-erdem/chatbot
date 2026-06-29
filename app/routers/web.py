from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Prod'da (Docker build) derlenmiş React buraya kopyalanır; varsa onu servis ederiz.
SPA_INDEX = Path("frontend/dist/index.html")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if SPA_INDEX.exists():
        return FileResponse(SPA_INDEX)
    # Dev/fallback: tek dosya Jinja sayfası (React ayrı 5173'te çalışıyorsa burası kullanılmaz)
    return templates.TemplateResponse(request=request, name="chat.html")


@router.get("/health")
async def health(request: Request):
    """Liveness probe: uygulama ayakta mı?"""
    gemini_ready = hasattr(request.app.state, "genai_client")
    return JSONResponse(
        status_code=200 if gemini_ready else 503,
        content={"status": "ok" if gemini_ready else "starting", "gemini_client": gemini_ready},
    )


@router.get("/metrics")
async def metrics(request: Request):
    """Basit gözlemlenebilirlik: aktif bağlantı (gauge) ve toplam mesaj (counter)."""
    manager = getattr(request.app.state, "connection_manager", None)
    if manager is None:
        return JSONResponse(status_code=503, content={"status": "starting"})
    return {
        "active_connections": manager.active_count,
        "total_messages": manager.total_messages,
    }
