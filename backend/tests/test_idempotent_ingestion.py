import asyncio
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks

from app import main
from app.models import IngestionStatus, Repository
from app.persistence import PersistenceError
from app.store import InMemoryStore


def request_for(url: str):
    return main.IngestRequest(mode="url", url=url)


@pytest.mark.asyncio
async def test_first_submission_creates_one_repository_and_one_ingestion(monkeypatch):
    store = InMemoryStore()
    monkeypatch.setattr(main, "store", store)
    tasks = BackgroundTasks()

    repository = await main.create_repository(request_for("https://github.com/Example/Repo"), tasks)

    assert repository.id in store.repositories
    assert repository.repository_key == "https://github.com/example/repo"
    assert len(tasks.tasks) == 1


@pytest.mark.asyncio
async def test_ready_repository_is_reused_without_second_ingestion(monkeypatch):
    store = InMemoryStore()
    monkeypatch.setattr(main, "store", store)
    tasks = BackgroundTasks()

    first = await main.create_repository(request_for("https://github.com/example/repo"), tasks)
    first.status = IngestionStatus.READY
    second = await main.create_repository(request_for("https://github.com/example/repo.git/"), tasks)

    assert second.id == first.id
    assert second.status is IngestionStatus.READY
    assert len(tasks.tasks) == 1


@pytest.mark.asyncio
async def test_processing_repository_is_reused_without_second_ingestion(monkeypatch):
    store = InMemoryStore()
    monkeypatch.setattr(main, "store", store)
    tasks = BackgroundTasks()

    first = await main.create_repository(request_for("https://github.com/example/repo"), tasks)
    first.status = IngestionStatus.EMBEDDING
    second = await main.create_repository(request_for("https://github.com/example/repo/"), tasks)

    assert second.id == first.id
    assert second.status is IngestionStatus.EMBEDDING
    assert len(tasks.tasks) == 1


@pytest.mark.asyncio
async def test_failed_repository_retries_with_same_identity_and_id(monkeypatch):
    store = InMemoryStore()
    monkeypatch.setattr(main, "store", store)
    tasks = BackgroundTasks()

    first = await main.create_repository(request_for("https://github.com/example/repo"), tasks)
    first.status = IngestionStatus.FAILED
    first.error = "temporary failure"
    second = await main.create_repository(request_for("https://github.com/example/repo"), tasks)

    assert second.id == first.id
    assert second.status is IngestionStatus.QUEUED
    assert second.error is None
    assert len(tasks.tasks) == 2


@pytest.mark.asyncio
async def test_equivalent_github_urls_share_repository_identity(monkeypatch):
    store = InMemoryStore()
    monkeypatch.setattr(main, "store", store)
    tasks = BackgroundTasks()

    first = await main.create_repository(request_for("https://github.com/user/repo"), tasks)
    second = await main.create_repository(request_for("https://github.com/user/repo/"), tasks)
    third = await main.create_repository(request_for("https://github.com/user/repo.git"), tasks)

    assert first.id == second.id == third.id
    assert len(tasks.tasks) == 1


@pytest.mark.asyncio
async def test_concurrent_duplicate_submissions_schedule_one_ingestion(monkeypatch):
    store = InMemoryStore()
    monkeypatch.setattr(main, "store", store)
    tasks = BackgroundTasks()

    results = await asyncio.gather(*[
        main.create_repository(request_for("https://github.com/user/repo"), tasks)
        for _ in range(2)
    ])

    assert results[0].id == results[1].id
    assert len(store.repositories) == 1
    assert len(tasks.tasks) == 1


class RestartPersistence:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    async def list_repositories(self) -> list[Repository]:
        return [self.repository]


class RacingPersistence:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository
        self.upsert_attempted = False

    async def list_repositories(self) -> list[Repository]:
        return [self.repository] if self.upsert_attempted else []

    async def upsert_repository(self, repository: Repository) -> None:
        self.upsert_attempted = True
        raise PersistenceError("repository_key uniqueness conflict")


@pytest.mark.asyncio
async def test_duplicate_after_restart_reuses_hydrated_repository(monkeypatch):
    existing = Repository(
        id=uuid4(),
        name="repo",
        url="https://github.com/user/repo",
        repository_key="https://github.com/user/repo",
        status=IngestionStatus.READY,
    )
    store = InMemoryStore(persistence=RestartPersistence(existing))
    monkeypatch.setattr(main, "store", store)
    tasks = BackgroundTasks()

    reused = await main.create_repository(request_for("https://github.com/user/repo.git/"), tasks)

    assert reused.id == existing.id
    assert reused.status is IngestionStatus.READY
    assert len(tasks.tasks) == 0


@pytest.mark.asyncio
async def test_durable_uniqueness_conflict_reuses_winner(monkeypatch):
    existing = Repository(
        id=uuid4(),
        name="repo",
        url="https://github.com/user/repo",
        repository_key="https://github.com/user/repo",
        status=IngestionStatus.EMBEDDING,
    )
    store = InMemoryStore(persistence=RacingPersistence(existing))
    monkeypatch.setattr(main, "store", store)
    tasks = BackgroundTasks()

    reused = await main.create_repository(request_for("https://github.com/user/repo"), tasks)

    assert reused.id == existing.id
    assert len(tasks.tasks) == 0
