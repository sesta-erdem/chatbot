import logging

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request):
    try:
        pool = request.app.state.pool

        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")

        if result == 1:
            return {"status": "ready"}

        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready"},
        )

    except Exception:
        logger.exception("Readiness check failed")

        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready"},
        )