import logging
from uuid import UUID, uuid4
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.api.dependencies import get_ingestion_service, get_repository_service
from app.ingestion.step_01_github_client import parse_github_url
from app.schemas.repository import IngestRequest, IngestionStatus, Repository
from app.services.ingestion_service import IngestionService
from app.services.repository_service import RepositoryService
from app.shared.exceptions import IngestionError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.post("", response_model=Repository, status_code=status.HTTP_202_ACCEPTED)
async def ingest_repository(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    repo_service: RepositoryService = Depends(get_repository_service),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
) -> Repository:
    """Validate GitHub URL, register repository in database, and trigger background ingestion."""
    try:
        owner, repo_name = parse_github_url(request.repository_url)
    except IngestionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    # Create new repository record in QUEUED state
    repo = Repository(
        id=uuid4(),
        name=repo_name,
        owner=owner,
        full_name=f"{owner}/{repo_name}",
        url=request.repository_url,
        branch=request.branch,
        status=IngestionStatus.QUEUED,
    )
    payload = {
        "id": str(repo.id), "name": repo.name, "owner": repo.owner, "full_name": repo.full_name,
        "url": repo.url, "branch": repo.branch, "status": repo.status.value,
    }
    await repo_service.db_repo.upsert_repo(payload)

    # Hand off to background worker so HTTP request returns 202 immediately
    background_tasks.add_task(ingestion_service.run_pipeline, repo, request.branch)
    logger.info("Queued background ingestion for repo %s (%s)", repo.id, repo.full_name)
    return repo


@router.get("", response_model=list[Repository])
async def list_repositories(repo_service: RepositoryService = Depends(get_repository_service)) -> list[Repository]:
    """List all indexed repositories and their ingestion statuses."""
    return await repo_service.list_repositories()


@router.get("/{repository_id}", response_model=Repository)
async def get_repository(repository_id: UUID, repo_service: RepositoryService = Depends(get_repository_service)) -> Repository:
    """Retrieve metadata and ingestion progress for a specific repository."""
    repo = await repo_service.get_repository(repository_id)
    if repo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
    return repo
