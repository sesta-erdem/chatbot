from fastapi import APIRouter, HTTPException, Request, status

from app.db.repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.services.auth import create_access_token, hash_password, verify_password
from app.services.rate_limit import RateLimitExceeded

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    repo = UserRepository()
    if await repo.get_by_email(body.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu e-posta zaten kayıtlı")
    user = await repo.create_user(email=body.email, password_hash=hash_password(body.password))
    return TokenResponse(access_token=create_access_token(user.id, user.role))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request):
    # Login DoS / parola deneme saldırısına karşı kaba limit (e-posta anahtarıyla)
    try:
        request.app.state.rate_limiter.check(f"login:{body.email.strip().lower()}")
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Çok fazla deneme, biraz bekle",
        )

    repo = UserRepository()
    user = await repo.get_by_email(body.email.strip().lower())
    # Aynı hata mesajı: e-posta var mı yok mu sızdırma (kullanıcı sayımı saldırısı)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-posta veya parola hatalı")
    return TokenResponse(access_token=create_access_token(user.id, user.role))
