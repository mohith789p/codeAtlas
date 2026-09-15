from uuid import uuid4

import pytest

from app.main import hydrate_repository_registry
from app.models import Repository
from app.persistence import PersistenceError
from app.store import InMemoryStore


class FakeRepositoryPersistence:
    def __init__(self, repositories: list[Repository]) -> None:
        self.repositories = repositories
        self.calls = 0

    async def list_repositories(self) -> list[Repository]:
        self.calls += 1
        return self.repositories


@pytest.mark.asyncio
async def test_store_hydrates_repository_registry_after_restart():
    repository = Repository(
        id=uuid4(),
        name="recovered",
        url="https://github.com/example/recovered",
    )
    persistence = FakeRepositoryPersistence([repository])
    restarted_store = InMemoryStore(persistence=persistence)

    recovered = await restarted_store.hydrate_repositories()

    assert recovered == [repository]
    assert await restarted_store.get_repository(repository.id) == repository
    assert await restarted_store.list_repositories() == [repository]
    assert persistence.calls == 1


@pytest.mark.asyncio
async def test_startup_hydrates_the_application_registry(monkeypatch):
    repository = Repository(
        id=uuid4(),
        name="startup-recovered",
        url="https://github.com/example/startup-recovered",
    )
    persistence = FakeRepositoryPersistence([repository])
    restarted_store = InMemoryStore(persistence=persistence)
    monkeypatch.setattr("app.main.store", restarted_store)

    await hydrate_repository_registry()

    assert await restarted_store.get_repository(repository.id) == repository
    assert persistence.calls == 1


@pytest.mark.asyncio
async def test_store_without_persistence_keeps_local_behavior():
    store = InMemoryStore()

    assert await store.hydrate_repositories() == []
    assert await store.list_repositories() == []


@pytest.mark.asyncio
async def test_startup_keeps_local_fallback_when_persistence_is_unavailable(monkeypatch):
    class UnavailableStore:
        async def hydrate_repositories(self) -> list[Repository]:
            raise PersistenceError("database unavailable")

    monkeypatch.setattr("app.main.store", UnavailableStore())

    await hydrate_repository_registry()
