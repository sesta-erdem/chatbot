import asyncio
from collections.abc import AsyncIterator

from providers.base import ChatMessage, ChatProvider
from repositories.chat import ChatRepository


class ChatService:
    def __init__(
        self,
        provider: ChatProvider,
        repository: ChatRepository,
        conversation_id: int,
        history_window: int,
        idle_timeout: float,
    ) -> None:
        self._provider = provider
        self._repository = repository
        self._conversation_id = conversation_id
        self._history_window = history_window
        self._idle_timeout = idle_timeout
        self._history: list[ChatMessage] = []

    async def stream_reply(
        self,
        user_text: str,
    ) -> AsyncIterator[str]:
        await self._repository.save_message(
            conversation_id=self._conversation_id,
            role="user",
            content=user_text,
        )

        context = self._build_context(user_text)
        response_parts: list[str] = []

        provider_stream = self._provider.stream(context)

        while True:
            try:
                # Timeout yalnızca provider'dan yeni chunk beklerken işler.
                chunk = await asyncio.wait_for(
                    anext(provider_stream),
                    timeout=self._idle_timeout,
                )
            except StopAsyncIteration:
                break

            response_parts.append(chunk)
            yield chunk

        response_text = "".join(response_parts)

        await self._repository.save_message(
            conversation_id=self._conversation_id,
            role="model",
            content=response_text,
        )

        self._commit_history(
            user_text=user_text,
            response_text=response_text,
        )

    def _build_context(
        self,
        user_text: str,
    ) -> list[ChatMessage]:
        max_history_items = self._history_window * 2
        windowed_history = self._history[-max_history_items:]

        return [
            *windowed_history,
            ChatMessage(
                role="user",
                content=user_text,
            ),
        ]

    def _commit_history(
        self,
        user_text: str,
        response_text: str,
    ) -> None:
        self._history.extend(
            [
                ChatMessage(
                    role="user",
                    content=user_text,
                ),
                ChatMessage(
                    role="model",
                    content=response_text,
                ),
            ]
        )

        max_history_items = self._history_window * 2
        self._history[:] = self._history[-max_history_items:]
