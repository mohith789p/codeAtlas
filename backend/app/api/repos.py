import os
import shutil
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.api.auth import get_current_user
from app.models.models import User, Repository, File as FileModel, CodeChunk, ChatSession, ChatMessage, GeneratedDoc
from app.schemas.schemas import RepositoryResponse, FileResponse, TreeNode
from app.services.embedding import EmbeddingService

router = APIRouter(prefix="/repositories", tags=["Repositories"])

@router.post("/upload", response_model=RepositoryResponse)
async def upload_repository(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are supported")

    repo_name = os.path.splitext(file.filename)[0]
    
    # Create DB Repository entry
    repo = Repository(
        name=repo_name,
        status="processing",
        user_id=current_user.id
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    # Save uploaded ZIP to uploads folder
    repo_dir = os.path.join(settings.UPLOAD_DIR, f"repo_{repo.id}")
    os.makedirs(repo_dir, exist_ok=True)
    zip_path = os.path.join(repo_dir, file.filename)
    extract_dir = os.path.join(repo_dir, "extracted")

    with open(zip_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Schedule background parsing & embedding process
    background_tasks.add_task(
        EmbeddingService.process_repository,
        repo_id=repo.id,
        zip_path=zip_path,
        extract_dir=extract_dir,
        db=db
    )

    return repo

@router.get("", response_model=List[RepositoryResponse])
def get_user_repositories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(Repository).filter(Repository.user_id == current_user.id).order_by(Repository.created_at.desc()).all()

@router.get("/{repo_id}", response_model=RepositoryResponse)
def get_repository(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = db.query(Repository).filter(Repository.id == repo_id, Repository.user_id == current_user.id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo

@router.get("/{repo_id}/tree")
def get_repository_tree(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = db.query(Repository).filter(Repository.id == repo_id, Repository.user_id == current_user.id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    files = db.query(FileModel).filter(FileModel.repo_id == repo_id).all()
    
    # Build tree hierarchy
    tree_root: Dict[str, Any] = {"name": repo.name, "path": "", "type": "dir", "children": {}}

    for f in files:
        parts = f.path.split("/")
        curr = tree_root
        accum_path = ""
        for i, part in enumerate(parts):
            accum_path = f"{accum_path}/{part}" if accum_path else part
            is_file = (i == len(parts) - 1)
            
            if is_file:
                curr["children"][part] = {
                    "id": f.id,
                    "name": part,
                    "path": f.path,
                    "type": "file",
                    "size_bytes": f.size_bytes
                }
            else:
                if part not in curr["children"]:
                    curr["children"][part] = {
                        "name": part,
                        "path": accum_path,
                        "type": "dir",
                        "children": {}
                    }
                curr = curr["children"][part]

    def format_node(node):
        if node["type"] == "file":
            return node
        children_list = [format_node(child) for child in node["children"].values()]
        # Sort directories first, then files
        children_list.sort(key=lambda x: (0 if x["type"] == "dir" else 1, x["name"]))
        return {
            "name": node["name"],
            "path": node["path"],
            "type": "dir",
            "children": children_list
        }

    return format_node(tree_root)

@router.get("/{repo_id}/files/{file_id}", response_model=FileResponse)
def get_repository_file(
    repo_id: int,
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    f = db.query(FileModel).filter(FileModel.id == file_id, FileModel.repo_id == repo_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    return f

@router.delete("/{repo_id}")
def delete_repository(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = db.query(Repository).filter(Repository.id == repo_id, Repository.user_id == current_user.id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Remove physical upload directory
    repo_dir = os.path.join(settings.UPLOAD_DIR, f"repo_{repo.id}")
    if os.path.exists(repo_dir):
        try:
            shutil.rmtree(repo_dir)
        except Exception as e:
            print(f"[Warning] Failed to delete repo directory {repo_dir}: {e}")

    try:
        # Delete code chunks and files
        db.query(CodeChunk).filter(CodeChunk.repo_id == repo_id).delete(synchronize_session=False)
        db.query(FileModel).filter(FileModel.repo_id == repo_id).delete(synchronize_session=False)
        
        # Delete chat messages before deleting chat sessions to satisfy foreign key constraint
        sessions = db.query(ChatSession.id).filter(ChatSession.repo_id == repo_id).all()
        session_ids = [s[0] for s in sessions]
        if session_ids:
            db.query(ChatMessage).filter(ChatMessage.session_id.in_(session_ids)).delete(synchronize_session=False)
            db.query(ChatSession).filter(ChatSession.repo_id == repo_id).delete(synchronize_session=False)

        # Delete generated docs
        db.query(GeneratedDoc).filter(GeneratedDoc.repo_id == repo_id).delete(synchronize_session=False)
        
        # Delete repository entity
        db.delete(repo)
        db.commit()
        return {"message": "Repository deleted successfully"}
    except Exception as e:
        db.rollback()
        print(f"[Error] Failed to delete repository {repo_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete repository: {str(e)}")
