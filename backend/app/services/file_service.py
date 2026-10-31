import logging
from uuid import UUID

from app.database.repositories import DatabaseRepository
from app.ingestion.step_01_github_client import GitHubClient, parse_github_url
from app.retrieval.bm25_index import get_bm25_registry
from app.schemas.files import FileContentResponse, FileTreeResponse
from app.services.file_tree_builder import build_file_tree
from app.shared.languages import detect_language

logger = logging.getLogger(__name__)


class FileService:
    """Manages file hierarchy construction and source code file retrieval."""

    def __init__(
        self,
        db_repo: DatabaseRepository | None = None,
        github_client: GitHubClient | None = None,
    ) -> None:
        self.db = db_repo or DatabaseRepository()
        self.github = github_client or GitHubClient()

    async def get_repository_filepaths(self, repo_id: UUID) -> list[str]:
        """Collect all known relative filepaths for a given repository."""
        paths: set[str] = {
            c.filepath.replace("\\", "/")
            for c in get_bm25_registry().get_chunks(repo_id)
            if c.filepath
        }

        repo_row = await self.db.get_repo(repo_id)
        if repo_row:
            meta = repo_row.get("repository_metadata") or {}
            for p in meta.get("file_paths", []):
                paths.add(p.replace("\\", "/"))

        return sorted(list(paths))

    async def get_tree(self, repo_id: UUID) -> FileTreeResponse:
        """Build nested FileNode tree from repository filepaths."""
        filepaths = await self.get_repository_filepaths(repo_id)
        return FileTreeResponse(tree=build_file_tree(filepaths))

    async def get_file_content(self, repo_id: UUID, file_path: str) -> FileContentResponse:
        """Fetch file content from GitHub raw API with local chunk fallback."""
        clean_path = file_path.strip().lstrip("/")
        repo_row = await self.db.get_repo(repo_id)
        if not repo_row:
            raise FileNotFoundError(f"Repository '{repo_id}' not found.")

        owner = repo_row.get("owner")
        name = repo_row.get("name")
        branch = repo_row.get("branch") or repo_row.get("default_branch") or "main"
        url = repo_row.get("url", "")

        if not (owner and name) and url:
            try:
                owner, name = parse_github_url(url)
            except Exception:
                pass

        language = detect_language(clean_path)

        # 1. Attempt GitHub direct raw fetch
        if owner and name:
            try:
                raw_text = await self.github.fetch_file_content(owner, name, branch, clean_path)
                return FileContentResponse(content=raw_text, language=language, size=len(raw_text))
            except Exception as exc:
                logger.info("GitHub fetch failed for %s/%s/%s: %s; using fallback", owner, name, clean_path, exc)

        # 2. Chunk reconstruction fallback from BM25 hot registry
        matching_chunks = [
            c for c in get_bm25_registry().get_chunks(repo_id)
            if c.filepath and c.filepath.replace("\\", "/").lstrip("/") == clean_path
        ]
        if matching_chunks:
            matching_chunks.sort(key=lambda c: c.start_line)
            assembled_content = "\n\n".join(c.content for c in matching_chunks)
            return FileContentResponse(content=assembled_content, language=language, size=len(assembled_content))

        raise FileNotFoundError(f"File '{clean_path}' could not be located in repository '{repo_id}'.")
