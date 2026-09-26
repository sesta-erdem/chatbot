from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: Literal["user", "model"]
    content: str


class ChatProvider(Protocol):
    def stream(
        self,
        messages: Sequence[ChatMessage],
    ) -> AsyncIterator[str]:
        ...
