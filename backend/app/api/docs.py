from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.models import User, Repository, GeneratedDoc
from app.schemas.schemas import GenerateDocRequest, GeneratedDocResponse
from app.services.rag import RAGService

router = APIRouter(prefix="/docs", tags=["Docs"])

@router.post("/generate", response_model=GeneratedDocResponse)
async def generate_document(
    req: GenerateDocRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = db.query(Repository).filter(Repository.id == req.repo_id, Repository.user_id == current_user.id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    if req.doc_type not in ["readme", "architecture"]:
        raise HTTPException(status_code=400, detail="Invalid doc_type. Must be 'readme' or 'architecture'")

    doc = await RAGService.generate_repository_doc(
        repo_id=req.repo_id,
        doc_type=req.doc_type,
        db=db
    )
    return doc

@router.get("/{repo_id}", response_model=List[GeneratedDocResponse])
def get_repository_docs(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = db.query(Repository).filter(Repository.id == repo_id, Repository.user_id == current_user.id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    return db.query(GeneratedDoc).filter(GeneratedDoc.repo_id == repo_id).order_by(GeneratedDoc.created_at.desc()).all()
