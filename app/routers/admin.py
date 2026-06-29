from fastapi import APIRouter, Depends, Request

from app.db.models import User
from app.dependencies import require_role

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
async def stats(request: Request, _admin: User = Depends(require_role("admin"))):
    """Yalnız admin. D11'deki yönetim paneli bunu besleyecek."""
    manager = request.app.state.connection_manager
    return {
        "active_connections": manager.active_count,
        "total_messages": manager.total_messages,
    }
