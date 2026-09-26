import asyncpg


class ChatRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_conversation(
        self,
        owner_id: int,
    ) -> int:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO conversations (owner)
                VALUES ($1)
                RETURNING id
                """,
                owner_id,
            )

    async def save_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO messages (conversation_id, role, content)
                VALUES ($1, $2, $3)
                """,
                conversation_id,
                role,
                content,
            )
