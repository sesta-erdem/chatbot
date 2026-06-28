from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    log_level: str = "INFO"
    app_access_token: str
    allowed_origins: list[str]
    history_window: int = 10

    @field_validator("gemini_api_key", mode="after")
    @classmethod
    def gemini_api_key_validator(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("gemini_api_key is empty")
        return value

    @field_validator("log_level", mode="after")
    @classmethod
    def log_level_validator(cls, value: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        value = value.upper()
        if value not in valid_levels:
            raise ValueError("log_level must be one of {}".format(valid_levels))
        return value

    @field_validator("app_access_token", mode="after")
    @classmethod
    def app_access_token_validator(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("app_access_token is empty")
        return value

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",")]
        return value


settings = Settings()
