import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_file_service
from app.schemas.files import FileTreeResponse, FileContentResponse
from app.services.file_service import FileService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["files"])


@router.get("/repositories/{repository_id}/tree", response_model=FileTreeResponse)
async def get_repository_tree(
    repository_id: UUID,
    file_service: FileService = Depends(get_file_service),
) -> FileTreeResponse:
    """Retrieve hierarchical file tree for an indexed repository."""
    try:
        return await file_service.get_tree(repository_id)
    except Exception as exc:
        logger.exception("Failed to build file tree for repo %s: %s", repository_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate file tree: {exc}",
        ) from exc


@router.get("/repositories/{repository_id}/files/{file_path:path}", response_model=FileContentResponse)
async def get_file_content(
    repository_id: UUID,
    file_path: str,
    file_service: FileService = Depends(get_file_service),
) -> FileContentResponse:
    """Retrieve raw file content and syntax language for a specific file in a repository."""
    try:
        return await file_service.get_file_content(repository_id, file_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to fetch file content for repo %s path %s: %s", repository_id, file_path, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch file content: {exc}",
        ) from exc
