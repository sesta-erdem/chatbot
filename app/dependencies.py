import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.models import User
from app.db.repository import UserRepository
from app.services.auth import TokenError, decode_token

bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> User:
    """HTTP uçlarında: Authorization: Bearer <jwt> başlığından kullanıcıyı çöz."""
    try:
        payload = decode_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (TokenError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya süresi geçmiş token",
        )

    user = await UserRepository().get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kullanıcı bulunamadı")
    return user


def require_role(role: str):
    """Rol kapısı: require_role('admin') gibi kullan."""

    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role != role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Yetkiniz yok")
        return user

    return checker
