import uuid

from sqlalchemy import select

from app.db.base import async_session
from app.db.models import Conversation, Message


class ConversationRepository:
    """
    Konuşma ve mesajların TÜM DB erişimi burada toplanır.
    ChatService yalnızca bu metotları çağırır; SQL/ORM detayını görmez.

    Her metot kendi kısa session'ını açar (session-per-operation).
    WebSocket boyunca tek bir session'ı açık tutmak yerine bu desen,
    uzun-ömürlü session risklerini (kopuk bağlantı, lazy-load patlaması) önler.
    """

    async def create_conversation(self) -> uuid.UUID:
        async with async_session() as session:
            conversation = Conversation()
            session.add(conversation)
            await session.commit()
            return conversation.id

    async def exists(self, conversation_id: uuid.UUID) -> bool:
        async with async_session() as session:
            return await session.get(Conversation, conversation_id) is not None

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
