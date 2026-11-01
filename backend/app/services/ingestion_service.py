import logging
from pathlib import Path
import shutil
import time
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
        self.github = GitHubClient()
        self.extractor = ArchiveExtractor()
        self.filter = FileFilter()
        self.chunker = ASTChunker()
        self.dedup = ChunkDeduplicator(self.db)
        self.indexer = ChunkIndexer(db_repo=self.db)

    @safe_traceable(name="ingestion_pipeline", run_type="chain")
    async def run_pipeline(self, repo: Repository, branch: str | None = None) -> None:
        """Run complete ingestion pipeline from GitHub download to BM25 index hydration."""
        start_time, extract_dir = time.perf_counter(), None
        try:
            # Step 1: Verify & Fetch GitHub Metadata
            meta = await self.github.fetch_repository_metadata(repo.url)
            repo.owner = meta["owner"]
            repo.branch = branch or meta.get("default_branch")
            repo.description, repo.language = meta.get("description"), meta.get("language")
            repo.stars, repo.forks, repo.size_kb = meta.get("stars", 0), meta.get("forks", 0), meta.get("size_kb")
            raw_contribs = meta.get("contributors", [])
            repo.contributors, repo.metadata_ready = raw_contribs, True

            contrib_details = [c.model_dump() if hasattr(c, "model_dump") else c for c in raw_contribs]
            repo_meta = {"topics": meta.get("topics", []), "size_kb": repo.size_kb, "default_branch": meta.get("default_branch")}

            await self.db.update_repo_metadata(
                repo.id, owner=repo.owner, branch=repo.branch, description=repo.description,
                language=repo.language, stars=repo.stars, forks=repo.forks, size_kb=repo.size_kb,
                contributors=len(raw_contribs), contributor_details=contrib_details,
                repository_metadata=repo_meta, status=IngestionStatus.DOWNLOADING.value,
            )
            repo.status = IngestionStatus.DOWNLOADING

            # Step 2: Extract archive
            extract_dir = await self.extractor.download_and_extract(meta["owner"], meta["name"], repo.branch)
            await self._update_stage(repo, IngestionStatus.FILTERING)

            # Step 3: Filter files
            files = self.filter.filter_directory(extract_dir)
            repo.files, repo.files_ready = len(files), True
            folders = {str(Path(p).parent).replace("\\", "/") for p in files if Path(p).parent != Path(".")}
            repo.folders = len(folders)
            await self.db.update_repo(repo.id, {"files": repo.files, "folders": repo.folders, "files_ready": True, "status": IngestionStatus.CHUNKING.value})
            repo.status = IngestionStatus.CHUNKING

            # Step 4, 5, 6: Parse AST, Chunk & Deduplicate
            all_chunks = [c for p, content in files.items() for c in self.chunker.chunk_file(p, content)]
            repo.processing.chunks_created = len(all_chunks)
            new_chunks, existing_chunks = await self.dedup.deduplicate(repo.id, all_chunks)

            # Step 7: Index Chunks & Finalize
            await self._update_stage(repo, IngestionStatus.INDEXING)
            embedded_count = await self.indexer.index_chunks(repo.id, new_chunks, existing_chunks)
            repo.processing.files_total = repo.files
            repo.processing.embeddings_generated = embedded_count
            repo.processing.duration_ms = (time.perf_counter() - start_time) * 1000.0
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
