from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash-lite"

    database_url: str

    log_level: str = "INFO"
    app_access_token: str
    allowed_origins: list[str]

    history_window: int = 2
    max_input_chars: int = 2000
    rate_limit_window: float = 10.0
    rate_limit_max_messages: int = 5
    idle_timeout: float = 30.0

    @field_validator("gemini_api_key")
    @classmethod
    def validate_api_key(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("gemini_api_key is empty")
        return value

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        valid_levels = {
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
        }

        value = value.upper()

        if value not in valid_levels:
            raise ValueError("Invalid log level")

        return value

    @field_validator("app_access_token")
    @classmethod
    def validate_access_token(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("app_access_token is empty")
        return value

    @field_validator("history_window")
    @classmethod
    def validate_history_window(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("history_window must be greater than 0")
        return value

    @field_validator(
        "max_input_chars",
        "rate_limit_max_messages",
    )
    @classmethod
    def validate_positive_integer(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("value must be greater than 0")
        return value

    @field_validator(
        "rate_limit_window",
        "idle_timeout",
    )
    @classmethod
    def validate_positive_float(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("value must be greater than 0")
        return value

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value):
        if isinstance(value, str):
            return [
                origin.strip()
                for origin in value.split(",")
                if origin.strip()
            ]
        return value
