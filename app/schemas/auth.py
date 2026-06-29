from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=72)  # bcrypt 72 bayt sınırı

    @field_validator("email", mode="after")
    @classmethod
    def email_basic(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or "." not in value:
            raise ValueError("geçerli bir e-posta gir")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
