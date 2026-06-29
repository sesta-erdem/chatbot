import uuid

from sqlalchemy import select

from app.db.base import async_session
from app.db.models import Conversation, Message, User


class UserRepository:
    """Kullanıcı kayıt/okuma. Parolayı burada değil, çağrıdan önce hash'lenmiş alır."""

    async def create_user(self, email: str, password_hash: str, role: str = "user") -> User:
        async with async_session() as session:
            user = User(email=email, password_hash=password_hash, role=role)
            session.add(user)
            await session.commit()
            return user

    async def get_by_email(self, email: str) -> User | None:
        async with async_session() as session:
            result = await session.execute(select(User).where(User.email == email))
            return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        async with async_session() as session:
            return await session.get(User, user_id)


class ConversationRepository:
    """
    Konuşma ve mesajların TÜM DB erişimi burada toplanır.
    ChatService yalnızca bu metotları çağırır; SQL/ORM detayını görmez.

    Her metot kendi kısa session'ını açar (session-per-operation).
    WebSocket boyunca tek bir session'ı açık tutmak yerine bu desen,
    uzun-ömürlü session risklerini (kopuk bağlantı, lazy-load patlaması) önler.
    """

    async def create_conversation(self, user_id: uuid.UUID) -> uuid.UUID:
        async with async_session() as session:
            conversation = Conversation(user_id=user_id)
            session.add(conversation)
            await session.commit()
            return conversation.id

    async def belongs_to(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """IDOR koruması: konuşma var VE bu kullanıcıya ait mi?"""
        async with async_session() as session:
            conversation = await session.get(Conversation, conversation_id)
            return conversation is not None and conversation.user_id == user_id

    async def append_message(
        self,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        token_count: int = 0,
    ) -> None:
        async with async_session() as session:
            session.add(
                Message(
                    conversation_id=conversation_id,
                    role=role,
                    content=content,
                    token_count=token_count,
                )
            )
            await session.commit()

    async def get_history(self, conversation_id: uuid.UUID) -> list[Message]:
        """Konuşmanın TAM geçmişi, kronolojik sırayla. Pencereleme (D4) bunun üstünde yapılır."""
        async with async_session() as session:
            result = await session.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
            )
            return list(result.scalars().all())
