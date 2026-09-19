import tempfile
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

from langchain_core.documents import Document

from ..config import Settings
from ..models import IngestionStatus, ProcessingStats, Repository, RepositoryMetadata
from ..persistence import PersistenceError
from ..store import InMemoryStore
from .chunking import chunk_file
from .embeddings import EmbeddingProviderError, GeminiEmbeddingService
from .filtering import collect_text_files
from .github import GitHubRepository, GitHubRepositoryError, download_and_extract, inspect_repository
from .indexing import IndexingService


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def run_ingestion(
    repository: Repository,
    branch: str | None,
    store: InMemoryStore,
    settings: Settings,
    embedder: object | None = None,
    indexer: IndexingService | None = None,
    evaluation: object | None = None,
) -> dict[str, int] | None:
    """Orchestrate the end-to-end repository ingestion pipeline."""
    started = perf_counter()
    try:
        metadata = await _inspect_and_update_metadata(repository, branch, settings, store)
        files = await _download_and_extract_files(repository, metadata, branch, settings, store)
        documents = await _chunk_and_store_documents(repository, files, store)
        return await _index_and_finalize(
            repository=repository,
            documents=documents,
            store=store,
            settings=settings,
            embedder=embedder,
            indexer=indexer,
            evaluation=evaluation,
            started=started,
        )
    except (EmbeddingProviderError, PersistenceError, GitHubRepositoryError, OSError, ValueError) as exc:
        await _handle_ingestion_failure(repository, store, exc)
        return None


async def _inspect_and_update_metadata(
    repository: Repository,
    branch: str | None,
    settings: Settings,
    store: InMemoryStore,
) -> GitHubRepository:
    repository.metadata_ready = False
    repository.files_ready = False
    repository.processing = ProcessingStats()
    repository.status = IngestionStatus.DOWNLOADING
    repository.updated_at = _now()
    await store.save_repository(repository)

    metadata = await inspect_repository(repository.url, settings)
    repository.branch = branch or metadata.default_branch
    repository.description = metadata.description
    repository.language = metadata.language
    repository.full_name = f"{metadata.owner}/{metadata.name}"
    repository.contributors = metadata.contributors
    repository.stats.contributors = len(metadata.contributors)
    repository.stats.size_kb = metadata.size_kb
    repository.stats.stars = metadata.stars
    repository.stats.forks = metadata.forks
    repository.stats.open_issues = metadata.open_issues
    repository.stats.open_pull_requests = metadata.open_pull_requests
    repository.repository_metadata = RepositoryMetadata(
        visibility=metadata.visibility,
        github_created_at=metadata.github_created_at,
        github_updated_at=metadata.github_updated_at,
        pushed_at=metadata.pushed_at,
        languages=metadata.languages,
        topics=metadata.topics,
        license_name=metadata.license_name,
    )
    repository.metadata_ready = True
    repository.updated_at = _now()
    await store.save_repository(repository)
    return metadata


async def _download_and_extract_files(
    repository: Repository,
    metadata: GitHubRepository,
    branch: str | None,
    settings: Settings,
    store: InMemoryStore,
) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="codeatlas-") as temp_dir:
        try:
            archive_root = await download_and_extract(metadata, branch, settings, target_dir=Path(temp_dir))
        except TypeError:
            archive_root = await download_and_extract(metadata, branch, settings)

        repository.status = IngestionStatus.FILTERING
        repository.updated_at = _now()
        await store.save_repository(repository)

        extracted_root = next((path for path in archive_root.iterdir() if path.is_dir()), archive_root)
        files = collect_text_files(extracted_root, settings.max_file_size_bytes)
        for path, content in files.items():
            await store.save_file(repository.id, path, content)

    repository.files_ready = True
    repository.stats.files = len(files)
    repository.stats.folders = len({str(Path(path).parent) for path in files})
    repository.updated_at = _now()
    await store.save_repository(repository)
    return files


async def _chunk_and_store_documents(
    repository: Repository,
    files: dict[str, str],
    store: InMemoryStore,
) -> list[Document]:
    repository.status = IngestionStatus.CHUNKING
    repository.updated_at = _now()
    await store.save_repository(repository)

    documents = [document for path, content in files.items() for document in chunk_file(path, content)]
    repository.processing.chunks_created = len(documents)
    await store.save_repository(repository)
    await store.save_documents(repository.id, documents)
    return documents


async def _index_and_finalize(
    repository: Repository,
    documents: list[Document],
    store: InMemoryStore,
    settings: Settings,
    embedder: object | None,
    indexer: IndexingService | None,
    evaluation: object | None,
    started: float,
) -> dict[str, int]:
    async def update_stage(stage: str) -> None:
        repository.status = IngestionStatus(stage)
        repository.updated_at = _now()
        await store.save_repository(repository)

    active_indexer = indexer or IndexingService(store)
    active_embedder = embedder or GeminiEmbeddingService(settings)
    indexing_result = await active_indexer.index_documents(
        repository.id,
        documents,
        active_embedder,
        on_stage=update_stage,
    )

    repository.processing.embeddings_generated = indexing_result.get("embedded")
    repository.processing.duration_ms = (perf_counter() - started) * 1000
    repository.processing.last_indexed_at = _now()
    repository.status = IngestionStatus.READY
    repository.updated_at = _now()
    await store.save_repository(repository)
    await store.log_event(repository.id, "indexing", "info", "Repository indexed", indexing_result)

    if evaluation is not None:
        try:
            await evaluation.evaluate_once(repository.id)
        except Exception as exc:
            await store.log_event(
                repository.id,
                "evaluation_failed",
                "error",
                "Automatic evaluation failed",
                {"error": str(exc)},
            )

    return indexing_result


async def _handle_ingestion_failure(
    repository: Repository,
    store: InMemoryStore,
    exc: Exception,
) -> None:
    repository.status = IngestionStatus.FAILED
    repository.error = str(exc)
    repository.updated_at = _now()
    await store.save_repository(repository)
    await store.log_event(
        repository.id,
        "ingestion",
        "error",
        "Repository ingestion failed",
        {"error": str(exc)},
    )
