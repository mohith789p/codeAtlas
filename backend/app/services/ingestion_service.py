from datetime import datetime, timezone
import logging, shutil, time
from pathlib import Path
from typing import Any
from uuid import UUID

from app.database.repositories import DatabaseRepository
from app.ingestion.step_01_github_client import GitHubClient
from app.ingestion.step_02_extractor import ArchiveExtractor
from app.ingestion.step_03_file_filter import FileFilter
from app.ingestion.step_05_chunker import ASTChunker
from app.ingestion.step_06_deduplicator import ChunkDeduplicator
from app.ingestion.step_07_indexer import ChunkIndexer
from app.schemas.repository import IngestionStatus, Repository
from app.shared.observability import safe_traceable

logger = logging.getLogger(__name__)


class IngestionService:
    """Orchestrates Steps 01 to 07 of repository ingestion."""

    def __init__(self, db_repo: DatabaseRepository | None = None) -> None:
        self.db = db_repo or DatabaseRepository()
        self.github, self.extractor = GitHubClient(), ArchiveExtractor()
        self.filter, self.chunker = FileFilter(), ASTChunker()
        self.dedup, self.indexer = ChunkDeduplicator(self.db), ChunkIndexer(db_repo=self.db)

    @safe_traceable(name="ingestion_pipeline", run_type="chain")
    async def run_pipeline(self, repo: Repository, branch: str | None = None) -> None:
        """Run complete ingestion pipeline from GitHub download to BM25 index hydration."""
        start_time, extract_dir = time.perf_counter(), None
        try:
            meta = await self.github.fetch_repository_metadata(repo.url)
            repo.owner = meta["owner"]
            repo.branch = branch or meta.get("default_branch")
            repo.description, repo.language = meta.get("description"), meta.get("language")
            repo.stars, repo.forks, repo.size_kb = meta.get("stars", 0), meta.get("forks", 0), meta.get("size_kb")
            raw_contribs = meta.get("contributors", [])
            repo.contributors, repo.metadata_ready = raw_contribs, True
            repo.created_at, repo.updated_at = meta.get("created_at"), meta.get("updated_at")
            repo.pushed_at, repo.visibility = meta.get("pushed_at"), meta.get("visibility")

            contrib_details = [c.model_dump() if hasattr(c, "model_dump") else c for c in raw_contribs]
            repo_meta = {
                "topics": meta.get("topics", []), "size_kb": repo.size_kb, "default_branch": meta.get("default_branch"),
                "github_created_at": meta.get("created_at"), "github_updated_at": meta.get("updated_at"),
                "pushed_at": meta.get("pushed_at"), "visibility": repo.visibility, "license_name": meta.get("license_name"),
            }
            update_fields: dict[str, Any] = {
                "owner": repo.owner, "branch": repo.branch, "description": repo.description,
                "language": repo.language, "stars": repo.stars, "forks": repo.forks, "size_kb": repo.size_kb,
                "contributors": len(raw_contribs), "contributor_details": contrib_details,
                "repository_metadata": repo_meta, "status": IngestionStatus.DOWNLOADING.value,
            }
            if meta.get("created_at"): update_fields["created_at"] = meta["created_at"]
            if meta.get("updated_at"): update_fields["updated_at"] = meta["updated_at"]
            await self.db.update_repo_metadata(repo.id, **update_fields)
            repo.status = IngestionStatus.DOWNLOADING

            extract_dir = await self.extractor.download_and_extract(meta["owner"], meta["name"], repo.branch)
            await self._update_stage(repo, IngestionStatus.FILTERING)

            files = self.filter.filter_directory(extract_dir)
            repo.files, repo.files_ready = len(files), True
            folders = {str(Path(p).parent).replace("\\", "/") for p in files if Path(p).parent != Path(".")}
            repo.folders = len(folders)
            await self.db.update_repo(repo.id, {"files": repo.files, "folders": repo.folders, "files_ready": True, "status": IngestionStatus.CHUNKING.value})
            repo.status = IngestionStatus.CHUNKING

            all_chunks = [c for p, content in files.items() for c in self.chunker.chunk_file(p, content)]
            repo.processing.chunks_created = len(all_chunks)
            new_chunks, existing_chunks = await self.dedup.deduplicate(repo.id, all_chunks)

            await self._update_stage(repo, IngestionStatus.INDEXING)
            embedded_count = await self.indexer.index_chunks(repo.id, new_chunks, existing_chunks)
            repo.processing.files_total = repo.files
            repo.processing.embeddings_generated = embedded_count
            repo.processing.duration_ms = (time.perf_counter() - start_time) * 1000.0
            repo.processing.last_indexed_at = datetime.now(timezone.utc).isoformat()
            repo.status = IngestionStatus.READY

            await self.db.complete_repo_ingestion(repo.id, repo.files, repo.folders, repo.processing.model_dump(), sorted(list(files.keys())))
            logger.info("Pipeline completed successfully for repo %s in %.1fms", repo.id, repo.processing.duration_ms)
        except Exception as exc:
            logger.exception("Ingestion failed for repository %s: %s", repo.id, exc)
            await self._update_stage(repo, IngestionStatus.FAILED, error=str(exc))
        finally:
            if extract_dir and extract_dir.exists():
                shutil.rmtree(extract_dir.parent if "codeatlas-extract-" in extract_dir.parent.name else extract_dir, ignore_errors=True)

    async def _update_stage(self, repo: Repository, status: IngestionStatus, error: str | None = None) -> None:
        repo.status, repo.error = status, error
        await self.db.update_repo_status(repo.id, status.value, error)
