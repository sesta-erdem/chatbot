import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings

ALGORITHM = "HS256"


class TokenError(Exception):
    pass


def hash_password(password: str) -> str:
    """bcrypt ile parola hash'le. (bcrypt 72 bayt sınırı; parola uzunluğu şemada kısıtlanır.)"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    """İmzalı (şifreli DEĞİL) JWT. Payload herkesçe okunabilir → içine sır koyma."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Geçersiz/expired token → TokenError. Algoritma sabit (alg-confusion saldırısına karşı)."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc
