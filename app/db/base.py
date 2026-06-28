from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """Tüm ORM modellerinin ortak atası. Alembic şemayı buradan okur."""


# Async motor: asyncpg sürücüsüyle event loop'u bloklamadan DB'ye konuşur.
engine = create_async_engine(settings.database_url, echo=False)

# Session fabrikası. expire_on_commit=False önemli:
# commit'ten sonra nesne attribute'larına erişim YENİ bir DB sorgusu tetiklemez.
# WebSocket bağlamında session kapandıktan sonra lazy-load patlamasını önler.
async_session = async_sessionmaker(engine, expire_on_commit=False)
