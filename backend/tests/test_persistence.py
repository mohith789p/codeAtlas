import json
from datetime import datetime, timezone
from uuid import uuid4

import httpx
import pytest

from app.config import Settings
from app.models import IngestionStatus, Repository
from app.persistence import SupabasePersistence
from app.services.indexing import ChunkRecord


@pytest.mark.asyncio
async def test_supabase_adapter_writes_chunk_and_normalized_metadata_rows():
    requests = []
    chunk_id = str(uuid4())

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/chunks"):
            body = json.loads(request.content)
            return httpx.Response(201, json=[{"id": chunk_id, "content_hash": body[0]["content_hash"]}])
        return httpx.Response(201, json=[])

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    persistence = SupabasePersistence(
        Settings(supabase_url="https://example.supabase.co", supabase_service_role_key="service-key"),
        client,
    )
    record = ChunkRecord(
        "a" * 64,
        "def run(): pass",
        [0.1, 0.2],
        {"filepath": "src/run.py", "language": "python", "symbol": "run", "imports": []},
    )

    await persistence.upsert_chunks(uuid4(), [record])
    await client.aclose()

    assert requests[0].url.path.endswith("/chunks")
    assert json.loads(requests[0].content)[0]["content_hash"] == "a" * 64
    metadata = json.loads(requests[1].content)[0]
    assert metadata["chunk_id"] == chunk_id
    assert metadata["filepath"] == "src/run.py"


@pytest.mark.asyncio
async def test_supabase_adapter_lists_repositories_with_nested_stats():
    repository_id = uuid4()
    created_at = datetime.now(timezone.utc).isoformat()
    updated_at = datetime.now(timezone.utc).isoformat()

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path.endswith("/repos")
        return httpx.Response(200, json=[{
            "id": str(repository_id),
            "name": "demo",
            "full_name": "owner/demo",
            "description": "A demo repository",
            "owner": "owner",
            "branch": "main",
            "language": "Python",
            "url": "https://github.com/owner/demo",
            "status": "ready",
            "error": None,
            "files": 4,
            "folders": 2,
            "contributors": 1,
            "size_kb": 12,
            "created_at": created_at,
            "updated_at": updated_at,
        }])

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    persistence = SupabasePersistence(
        Settings(supabase_url="https://example.supabase.co", supabase_service_role_key="service-key"),
        client,
    )

    repositories = await persistence.list_repositories()
    await client.aclose()

    assert repositories == [Repository(
        id=repository_id,
        name="demo",
        full_name="owner/demo",
        description="A demo repository",
        owner="owner",
        branch="main",
        language="Python",
        url="https://github.com/owner/demo",
        repository_key="https://github.com/owner/demo",
        status=IngestionStatus.READY,
        stats={"files": 4, "folders": 2, "contributors": 1, "size_kb": 12},
        created_at=created_at,
        updated_at=updated_at,
    )]
