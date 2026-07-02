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
    history_token_budget: int = 4000  # modele giden bağlamın maksimum token bütçesi
    database_url: str
    jwt_secret: str
    # Uzun-ömürlü WebSocket: token handshake'te doğrulanır, bağlantı boyunca tekrar
    # kontrol edilmez. Bu yüzden makul uzun bir süre (7 gün) seçiyoruz.
    jwt_expire_minutes: int = 60 * 24 * 7

    # RAG ayarları
    # gemini-embedding-001: güncel model (text-embedding-004 API'den kaldırıldı → 404).
    # Varsayılan çıktısı 3072 boyut; DB şeması Vector(768) olduğundan embed çağrısında
    # output_dimensionality=embedding_dim ile 768 istenir.
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768
    chunk_size: int = 1000           # karakter (kaba); deney günlüğüyle ayarlanır
    chunk_overlap: int = 200
    rag_top_k: int = 4               # kaç parça getirilsin
    rag_distance_threshold: float = 0.65  # cosine distance; üstündeyse "bulamadım"
    max_upload_bytes: int = 5 * 1024 * 1024  # 5 MB

    @field_validator("gemini_api_key", mode="after")
    @classmethod
    def gemini_api_key_validator(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("gemini_api_key is empty")
        return value

    @field_validator("database_url", mode="after")
    @classmethod
    def database_url_validator(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("database_url is empty")
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "database_url async sürücü kullanmalı: 'postgresql+asyncpg://...' "
                "(düz 'postgresql://' senkron sürücüdür ve event loop'u bloklar)"
            )
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

    @field_validator("jwt_secret", mode="after")
    @classmethod
    def jwt_secret_validator(cls, value: str) -> str:
        if len(value.strip()) < 16:
            raise ValueError("jwt_secret en az 16 karakter olmalı (imza güvenliği)")
        return value

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",")]
        return value


settings = Settings()
