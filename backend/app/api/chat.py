import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.models import User, Repository, ChatSession, ChatMessage
from app.schemas.schemas import (
    CreateSessionRequest, ChatSessionResponse,
    ChatQueryRequest, ChatMessageResponse
)
from app.services.rag import RAGService

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/sessions", response_model=ChatSessionResponse)
def create_chat_session(
    req: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = db.query(Repository).filter(Repository.id == req.repo_id, Repository.user_id == current_user.id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    session = ChatSession(
        repo_id=req.repo_id,
        user_id=current_user.id,
        title=req.title or "New Conversation"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@router.get("/sessions", response_model=List[ChatSessionResponse])
def get_chat_sessions(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(ChatSession).filter(
        ChatSession.repo_id == repo_id,
        ChatSession.user_id == current_user.id
    ).order_by(ChatSession.created_at.desc()).all()

@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
def get_session_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()
    
    result = []
    for msg in messages:
        sources_data = None
        if msg.sources:
            try:
                sources_data = json.loads(msg.sources)
            except Exception:
                sources_data = []
        result.append({
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "sources": sources_data,
            "created_at": msg.created_at
        })
    return result

@router.post("/query", response_model=ChatMessageResponse)
async def query_chat(
    req: ChatQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(ChatSession).filter(ChatSession.id == req.session_id, ChatSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    response = await RAGService.answer_question(
        repo_id=session.repo_id,
        session_id=session.id,
        query=req.query,
        db=db
    )
    return response
