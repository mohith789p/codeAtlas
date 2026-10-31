from pydantic import BaseModel, Field
from app.schemas.response import ValidatedCitation


class ChatMessage(BaseModel):
    id: str
    role: str  # 'user' | 'assistant'
    content: str
    citations: list[ValidatedCitation] = Field(default_factory=list)
    created_at: str


class ChatSession(BaseModel):
    id: str
    repository_id: str
    created_at: str
    updated_at: str | None = None


class CreateSessionRequest(BaseModel):
    repository_id: str


class StreamMessageRequest(BaseModel):
    repository_id: str
    content: str
    session_id: str | None = None
