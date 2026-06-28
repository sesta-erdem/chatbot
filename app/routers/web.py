from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="chat.html")


@router.get("/health")
async def health(request: Request):
    """Liveness probe: uygulama ayakta mı?"""
    gemini_ready = hasattr(request.app.state, "genai_client")
    return JSONResponse(
        status_code=200 if gemini_ready else 503,
        content={"status": "ok" if gemini_ready else "starting", "gemini_client": gemini_ready},
    )
