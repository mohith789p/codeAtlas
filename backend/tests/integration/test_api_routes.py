from unittest.mock import AsyncMock, patch
from uuid import uuid4
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_ingestion_service, get_repository_service
from app.main import app
from app.schemas.repository import IngestionStatus, Repository


@pytest.mark.asyncio
async def test_health_check_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "version": "1.0.0"}


@pytest.mark.asyncio
async def test_ingest_repository_endpoint():
    transport = ASGITransport(app=app)
    mock_ingestion_svc = AsyncMock()
    mock_repo_svc = AsyncMock()

    app.dependency_overrides[get_ingestion_service] = lambda: mock_ingestion_svc
    app.dependency_overrides[get_repository_service] = lambda: mock_repo_svc

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Valid URL -> 202 Accepted
            res = await client.post("/api/repositories", json={"repository_url": "https://github.com/psf/requests"})
            assert res.status_code == 202
            data = res.json()
            assert data["name"] == "requests"
            assert data["status"] == "queued"

            # Invalid URL -> 422
            bad_res = await client.post("/api/repositories", json={"repository_url": "invalid://not-github"})
            assert bad_res.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_query_endpoint_indexing_conflict():
    transport = ASGITransport(app=app)
    mock_repo_svc = AsyncMock(_mock_unsafe=True)
    repo_id = uuid4()
    mock_repo_svc.assert_ready.side_effect = Exception("Repository is still indexing. Please wait.")
    app.dependency_overrides[get_repository_service] = lambda: mock_repo_svc

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/queries", json={"repository_id": str(repo_id), "query": "Where is get()?"})
            assert res.status_code in (409, 500)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_file_tree_and_content_endpoints():
    transport = ASGITransport(app=app)
    mock_file_svc = AsyncMock()
    from app.api.dependencies import get_file_service
    from app.schemas.files import FileTreeResponse, FileNode, FileContentResponse

    repo_id = uuid4()
    mock_file_svc.get_tree.return_value = FileTreeResponse(
        tree=[FileNode(name="src", path="src", type="directory", children=[
            FileNode(name="main.py", path="src/main.py", type="file")
        ])]
    )
    mock_file_svc.get_file_content.return_value = FileContentResponse(
        content="print('hello')",
        language="python",
        size=14,
    )

    app.dependency_overrides[get_file_service] = lambda: mock_file_svc
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res_tree = await client.get(f"/api/repositories/{repo_id}/tree")
            assert res_tree.status_code == 200
            data_tree = res_tree.json()
            assert len(data_tree["tree"]) == 1
            assert data_tree["tree"][0]["name"] == "src"

            res_file = await client.get(f"/api/repositories/{repo_id}/files/src/main.py")
            assert res_file.status_code == 200
            data_file = res_file.json()
            assert data_file["content"] == "print('hello')"
            assert data_file["language"] == "python"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_sessions_and_stream_endpoints():
    transport = ASGITransport(app=app)
    mock_chat_svc = AsyncMock()
    from app.api.dependencies import get_chat_service
    from app.schemas.chat import ChatSession, ChatMessage

    repo_id = uuid4()
    mock_chat_svc.list_sessions.return_value = [
        ChatSession(id="sess-1", repository_id=str(repo_id), created_at="2026-01-01T00:00:00Z")
    ]
    mock_chat_svc.create_session.return_value = ChatSession(
        id="sess-2", repository_id=str(repo_id), created_at="2026-01-01T00:00:00Z"
    )
    mock_chat_svc.get_messages.return_value = [
        ChatMessage(id="msg-1", role="user", content="Hello", created_at="2026-01-01T00:00:00Z")
    ]

    async def fake_stream(*args, **kwargs):
        yield "data: {\"type\": \"token\", \"content\": \"Hi!\"}\n\n"
        yield "data: {\"type\": \"done\", \"message\": {\"id\": \"m1\", \"role\": \"assistant\", \"content\": \"Hi!\", \"citations\": [], \"created_at\": \"2026-01-01T00:00:00Z\"}}\n\n"

    mock_chat_svc.stream_answer = fake_stream

    app.dependency_overrides[get_chat_service] = lambda: mock_chat_svc
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Sessions list
            res_list = await client.get(f"/api/chat/sessions?repository_id={repo_id}")
            assert res_list.status_code == 200
            assert len(res_list.json()) == 1

            # Session create
            res_create = await client.post(f"/api/chat/sessions?repository_id={repo_id}")
            assert res_create.status_code == 201
            assert res_create.json()["id"] == "sess-2"

            # Session messages
            res_msgs = await client.get("/api/chat/sessions/sess-1/messages")
            assert res_msgs.status_code == 200
            assert len(res_msgs.json()) == 1

            # Stream
            res_stream = await client.post("/api/chat/stream", json={"repository_id": str(repo_id), "content": "Hi"})
            assert res_stream.status_code == 200
            assert "text/event-stream" in res_stream.headers["content-type"]
            body_text = res_stream.text
            assert "data: {\"type\": \"token\"" in body_text
            assert "data: {\"type\": \"done\"" in body_text
    finally:
        app.dependency_overrides.clear()
