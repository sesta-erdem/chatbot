from typing import Literal

from pydantic import BaseModel


class ChunkMessage(BaseModel):
    type: Literal["chunk"] = "chunk"
    content: str


class DoneMessage(BaseModel):
    type: Literal["done"] = "done"


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    content: str


class SystemMessage(BaseModel):
    type: Literal["system"] = "system"
    content: str


class UserMessage(BaseModel):
    type: Literal["user_message"]
    content: str
