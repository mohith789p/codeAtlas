from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.models import User, Repository
from app.schemas.schemas import SearchQuery, ChunkResult
from app.services.retrieval import RetrievalService

router = APIRouter(prefix="/search", tags=["Search"])

@router.post("/{repo_id}", response_model=List[ChunkResult])
async def search_repository(
    repo_id: int,
    query_in: SearchQuery,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = db.query(Repository).filter(Repository.id == repo_id, Repository.user_id == current_user.id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    results = await RetrievalService.search_relevant_chunks(
        repo_id=repo_id,
        query=query_in.query,
        top_k=query_in.top_k,
        db=db
    )
    return results
