import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_chat_service
from app.schemas.chat import (
    ChatMessage,
    ChatSession,
    CreateSessionRequest,
    StreamMessageRequest,
)
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/sessions", response_model=list[ChatSession])
async def list_sessions(
    repository_id: Optional[str] = Query(None),
    repositoryId: Optional[str] = Query(None),
    chat_service: ChatService = Depends(get_chat_service),
) -> list[ChatSession]:
    """Retrieve chat sessions for a repository."""
    repo_id = repository_id or repositoryId or ""
    return await chat_service.list_sessions(repo_id)


@router.post("/sessions", response_model=ChatSession, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: Optional[CreateSessionRequest] = None,
    repository_id: Optional[str] = Query(None),
    repositoryId: Optional[str] = Query(None),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatSession:
    """Create a new chat session for a repository."""
    repo_id = ""
    if payload and payload.repository_id:
        repo_id = payload.repository_id
    elif repository_id:
        repo_id = repository_id
    elif repositoryId:
        repo_id = repositoryId

    return await chat_service.create_session(repo_id)


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessage])
async def get_session_messages(
    session_id: str,
    chat_service: ChatService = Depends(get_chat_service),
) -> list[ChatMessage]:
    """Retrieve historical messages for a chat session."""
    return await chat_service.get_messages(session_id)


@router.post("/sessions/{session_id}/messages/stream")
async def stream_session_message(
    session_id: str,
    payload: StreamMessageRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """Stream response tokens for a message in a specific session using Server-Sent Events."""
    return StreamingResponse(
        chat_service.stream_answer(
            repo_id=payload.repository_id,
            query=payload.content,
            session_id=session_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/stream")
async def stream_message(
    payload: StreamMessageRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """Stream response tokens for a repository query using Server-Sent Events."""
    return StreamingResponse(
        chat_service.stream_answer(
            repo_id=payload.repository_id,
            query=payload.content,
            session_id=payload.session_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/sessions", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sessions(
    repository_id: Optional[str] = Query(None),
    repositoryId: Optional[str] = Query(None),
    chat_service: ChatService = Depends(get_chat_service),
) -> None:
    """Clear chat sessions and messages for a repository."""
    repo_id = repository_id or repositoryId or ""
    await chat_service.delete_sessions(repo_id)
