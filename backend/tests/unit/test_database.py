from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import pytest

from app.database.connection import DatabaseConnection
from app.database.models import ChunkMetadataRow, ChunkRow, RepoRow, parse_embedding
from app.database.repositories import DatabaseRepository
from app.shared.config import Settings
from app.shared.exceptions import ConfigurationError, PersistenceError


def test_models_and_embedding_parser():
    assert parse_embedding("[0.1, 0.2, 0.3]") == [0.1, 0.2, 0.3]
    assert parse_embedding([0.4, 0.5]) == [0.4, 0.5]
    assert parse_embedding("invalid") == []

    repo_id = uuid4()
    row = RepoRow(id=repo_id, name="demo", url="https://github.com/a/b", status="ready")
    assert row.name == "demo"
    assert row.status == "ready"


def test_connection_url_and_headers():
    settings = Settings(supabase_url="https://xyz.supabase.co", supabase_service_role_key="key123")
    conn = DatabaseConnection(settings=settings)
    assert conn.is_configured is True
    assert conn.base_url == "https://xyz.supabase.co/rest/v1"
    assert conn.headers["apikey"] == "key123"

    unconfigured = DatabaseConnection(settings=Settings(supabase_url=None, supabase_service_role_key=None))
    assert unconfigured.is_configured is False
    with pytest.raises(ConfigurationError):
        _ = unconfigured.base_url


@pytest.mark.asyncio
async def test_repository_database_queries():
    conn = MagicMock(spec=DatabaseConnection)
    conn.execute = AsyncMock()
    repo = DatabaseRepository(connection=conn)

    # get_repo
    repo_id = uuid4()
    conn.execute.return_value = [{"id": str(repo_id), "name": "demo"}]
    res = await repo.get_repo(repo_id)
    assert res == {"id": str(repo_id), "name": "demo"}

    # upsert_repo
    await repo.upsert_repo({"id": str(repo_id), "name": "demo"})
    conn.execute.assert_called_with("POST", "repos?on_conflict=id", json=[{"id": str(repo_id), "name": "demo"}], headers={"Prefer": "resolution=merge-duplicates"})

    # dense_search RPC
    conn.execute.return_value = [{"id": str(uuid4()), "similarity": 0.95, "content": "def run(): pass"}]
    results = await repo.dense_search(repo_id, [0.1] * 768, limit=5)
    assert len(results) == 1
    assert results[0]["similarity"] == 0.95
