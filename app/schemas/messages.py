from typing import Literal

from pydantic import BaseModel


class ChunkMessage(BaseModel):
    type: Literal["chunk"] = "chunk"
    content: str


class DoneMessage(BaseModel):
    type: Literal["done"] = "done"
    sources: list[dict] = []  # RAG kaynakları: [{"file": ..., "page": ...}]


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    content: str


class SystemMessage(BaseModel):
    type: Literal["system"] = "system"
    content: str


class UserMessage(BaseModel):
    type: Literal["user_message"]
    content: str


class ConversationMessage(BaseModel):
    """Sunucu yeni bir konuşma açınca id'yi istemciye bildirir; istemci saklayıp reconnect'te geri yollar."""
    type: Literal["conversation"] = "conversation"
    conversation_id: str
