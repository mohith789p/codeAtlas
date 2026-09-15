from pathlib import Path
from uuid import uuid4

import pytest
from langchain_core.documents import Document

from app.config import Settings
from app.models import IngestionStatus, Repository
from app.persistence import PersistenceError
from app.services.embeddings import EmbeddingProviderError
from app.services.github import GitHubRepository
from app.services.ingestion import run_ingestion
from app.store import InMemoryStore


class RecordingStore(InMemoryStore):
    def __init__(self) -> None:
        super().__init__()
        self.status_history = []

    async def save_repository(self, repository):
        self.status_history.append(repository.status)
        return await super().save_repository(repository)


class FakeEmbedder:
    async def embed_documents(self, texts):
        return [[1.0, 2.0] for _ in texts]


class FailingEmbedder:
    async def embed_documents(self, texts):
        raise EmbeddingProviderError("quota exhausted")


class FailingIndexer:
    async def index_documents(self, repository_id, documents, embedder, on_stage=None):
        raise PersistenceError("database unavailable")


class RecordingEvaluation:
    def __init__(self):
        self.calls = []

    async def evaluate_once(self, repository_id):
        self.calls.append(repository_id)
        return {"status": "completed"}


@pytest.fixture
def repository() -> Repository:
    return Repository(id=uuid4(), name="demo", url="https://github.com/example/demo")


def github_metadata() -> GitHubRepository:
    return GitHubRepository("example", "demo", "https://github.com/example/demo", "main", 4, "Demo", "Python")


@pytest.mark.asyncio
async def test_successful_ingestion_only_becomes_ready_after_indexing(monkeypatch, repository):
    store = RecordingStore()
    monkeypatch.setattr("app.services.ingestion.inspect_repository", lambda url, settings: _async_value(github_metadata()))
    monkeypatch.setattr("app.services.ingestion.download_and_extract", lambda metadata, branch, settings: _async_value(Path(".")))
    monkeypatch.setattr("app.services.ingestion.collect_text_files", lambda root, limit: {"main.py": "def run(): pass"})
    monkeypatch.setattr("app.services.ingestion.chunk_file", lambda path, content: [Document(page_content=content, metadata={"filepath": path, "symbol": "run"})])

    await run_ingestion(repository, None, store, Settings(), embedder=FakeEmbedder())

    assert repository.metadata_ready is True
    assert repository.files_ready is True
    assert repository.status is IngestionStatus.READY
    assert store.status_history[-3:] == [IngestionStatus.EMBEDDING, IngestionStatus.INDEXING, IngestionStatus.READY]
    assert len(store.chunks[repository.id]) == 1


@pytest.mark.asyncio
async def test_embedding_failure_marks_repository_failed_and_never_ready(monkeypatch, repository):
    store = RecordingStore()
    monkeypatch.setattr("app.services.ingestion.inspect_repository", lambda url, settings: _async_value(github_metadata()))
    monkeypatch.setattr("app.services.ingestion.download_and_extract", lambda metadata, branch, settings: _async_value(Path(".")))
    monkeypatch.setattr("app.services.ingestion.collect_text_files", lambda root, limit: {"main.py": "def run(): pass"})
    monkeypatch.setattr("app.services.ingestion.chunk_file", lambda path, content: [Document(page_content=content, metadata={"filepath": path})])

    await run_ingestion(repository, None, store, Settings(), embedder=FailingEmbedder())

    assert repository.metadata_ready is True
    assert repository.files_ready is True
    assert repository.status is IngestionStatus.FAILED
    assert IngestionStatus.READY not in store.status_history
    assert store.chunks[repository.id] == {}
    assert store.logs[-1]["level"] == "error"


@pytest.mark.asyncio
async def test_indexing_failure_marks_repository_failed_and_never_ready(monkeypatch, repository):
    store = RecordingStore()
    monkeypatch.setattr("app.services.ingestion.inspect_repository", lambda url, settings: _async_value(github_metadata()))
    monkeypatch.setattr("app.services.ingestion.download_and_extract", lambda metadata, branch, settings: _async_value(Path(".")))
    monkeypatch.setattr("app.services.ingestion.collect_text_files", lambda root, limit: {"main.py": "def run(): pass"})
    monkeypatch.setattr("app.services.ingestion.chunk_file", lambda path, content: [Document(page_content=content, metadata={"filepath": path})])

    await run_ingestion(repository, None, store, Settings(), embedder=FakeEmbedder(), indexer=FailingIndexer())

    assert repository.metadata_ready is True
    assert repository.files_ready is True
    assert repository.status is IngestionStatus.FAILED
    assert IngestionStatus.READY not in store.status_history
    assert store.logs[-1]["message"] == "Repository ingestion failed"


@pytest.mark.asyncio
async def test_ready_transition_triggers_injected_evaluation_worker(monkeypatch, repository):
    store = RecordingStore()
    evaluation = RecordingEvaluation()
    monkeypatch.setattr("app.services.ingestion.inspect_repository", lambda url, settings: _async_value(github_metadata()))
    monkeypatch.setattr("app.services.ingestion.download_and_extract", lambda metadata, branch, settings: _async_value(Path(".")))
    monkeypatch.setattr("app.services.ingestion.collect_text_files", lambda root, limit: {"main.py": "def run(): pass"})
    monkeypatch.setattr("app.services.ingestion.chunk_file", lambda path, content: [Document(page_content=content, metadata={"filepath": path})])

    await run_ingestion(repository, None, store, Settings(), embedder=FakeEmbedder(), evaluation=evaluation)

    assert repository.status is IngestionStatus.READY
    assert evaluation.calls == [repository.id]


async def _async_value(value):
    return value
