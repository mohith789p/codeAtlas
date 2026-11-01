import logging
from uuid import UUID

from app.database.repositories import DatabaseRepository
from app.schemas.repository import Contributor, IngestionStatus, ProcessingStats, Repository
from app.shared.exceptions import RetrievalError

logger = logging.getLogger(__name__)


class RepositoryService:
    """Manages repository status checks and metadata retrieval."""

    def __init__(self, db_repo: DatabaseRepository | None = None) -> None:
        self.db_repo = db_repo or DatabaseRepository()

    async def get_repository(self, repo_id: UUID) -> Repository | None:
        """Fetch repository record from database."""
        row = await self.db_repo.get_repo(repo_id)
        if not row:
            return None
        return self._row_to_model(row)

    async def list_repositories(self) -> list[Repository]:
        """Fetch all indexed repositories."""
        rows = await self.db_repo.list_repos()
        return [self._row_to_model(r) for r in rows]

    async def assert_ready(self, repo_id: UUID) -> Repository:
        """Check repository readiness before querying; raises RetrievalError if not ready."""
        repo = await self.get_repository(repo_id)
        if repo is None:
            raise RetrievalError(f"Repository '{repo_id}' not found.")
        if repo.status == IngestionStatus.FAILED:
            raise RetrievalError(f"Repository indexing failed: {repo.error or 'Unknown error'}")
        if repo.status != IngestionStatus.READY:
            raise RetrievalError(f"Repository is still indexing (status: {repo.status.value}). Please wait.")
        return repo

    def _row_to_model(self, row: dict) -> Repository:
        contribs = [Contributor(**c) if isinstance(c, dict) else c for c in row.get("contributor_details") or []]
        stats_dict = dict(row.get("processing_stats") or {})
        if not stats_dict.get("last_indexed_at") and row.get("updated_at"):
            stats_dict["last_indexed_at"] = str(row["updated_at"])
        if not stats_dict.get("files_total") and row.get("files"):
            stats_dict["files_total"] = int(row["files"])
        stats = ProcessingStats(**stats_dict)
        url = row.get("url") or row.get("repository_key") or f"https://github.com/{row.get('owner', 'local')}/{row.get('name', 'repo')}"
        meta = row.get("repository_metadata") or {}
        created_at = meta.get("github_created_at") or meta.get("created_at") or row.get("created_at")
        updated_at = meta.get("github_updated_at") or meta.get("updated_at") or row.get("updated_at")
        pushed_at = meta.get("pushed_at") or row.get("pushed_at")

        return Repository(
            id=row["id"],
            name=row["name"],
            url=url,
            status=IngestionStatus(row["status"]),
            owner=row.get("owner"),
            full_name=row.get("full_name"),
            description=row.get("description"),
            branch=row.get("branch"),
            default_branch=row.get("default_branch") or meta.get("default_branch") or row.get("branch"),
            language=row.get("language"),
            primary_language=row.get("primary_language") or meta.get("primary_language") or row.get("language"),
            error=row.get("error"),
            files=row.get("files", 0),
            folders=row.get("folders", 0),
            contributors=contribs,
            stars=row.get("stars", 0),
            forks=row.get("forks", 0),
            size_kb=row.get("size_kb") or meta.get("size_kb"),
            visibility=row.get("visibility") or meta.get("visibility"),
            topics=row.get("topics") or meta.get("topics") or [],
            languages=row.get("languages") or meta.get("languages") or {},
            metadata_ready=row.get("metadata_ready", False),
            files_ready=row.get("files_ready", False),
            processing=stats,
            repository_metadata=meta,
            created_at=created_at,
            updated_at=updated_at,
            pushed_at=pushed_at,
        )
