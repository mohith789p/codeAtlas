from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import pytest

from app.database.repositories import DatabaseRepository
from app.schemas.query import QueryOptions
from app.schemas.repository import IngestionStatus, Repository
from app.services.query_service import QueryService
from app.services.repository_service import RepositoryService
from app.shared.exceptions import RetrievalError


@pytest.mark.asyncio
async def test_repository_service_assert_ready():
    mock_db = MagicMock(spec=DatabaseRepository)
    service = RepositoryService(db_repo=mock_db)

    repo_id = uuid4()
    # Case 1: Repo not found
    mock_db.get_repo = AsyncMock(return_value=None)
    with pytest.raises(RetrievalError, match="not found"):
        await service.assert_ready(repo_id)

    # Case 2: Repo still indexing
    mock_db.get_repo = AsyncMock(return_value={"id": str(repo_id), "name": "r", "url": "u", "status": "indexing"})
    with pytest.raises(RetrievalError, match="still indexing"):
        await service.assert_ready(repo_id)

    # Case 3: Repo ready
    mock_db.get_repo = AsyncMock(return_value={"id": str(repo_id), "name": "r", "url": "u", "status": "ready"})
    repo = await service.assert_ready(repo_id)
    assert repo.status == IngestionStatus.READY


@pytest.mark.asyncio
async def test_query_service_flow():
    mock_repo_svc = MagicMock(spec=RepositoryService)
    mock_repo_svc.assert_ready = AsyncMock()

    service = QueryService(repo_service=mock_repo_svc)
    service.preprocessor.preprocess = AsyncMock(return_value=("where is main", [0.1] * 768))
    service.cache.lookup = AsyncMock(return_value=None)
    service.retriever.retrieve = AsyncMock(return_value=([], []))
    service.cache.save = AsyncMock()

    repo_id = uuid4()
    response = await service.query(repo_id, "where is main", QueryOptions())

    assert response.provider == "guard"
    assert "not appear to be related" in response.answer
    mock_repo_svc.assert_ready.assert_called_once_with(repo_id)


@pytest.mark.asyncio
async def test_file_service_tree_and_content():
    from app.services.file_service import FileService
    from app.schemas.retrieval import ChunkRecord

    mock_db = MagicMock(spec=DatabaseRepository)
    repo_id = uuid4()
    mock_db.get_repo = AsyncMock(return_value={
        "id": str(repo_id),
        "owner": "test",
        "name": "project",
        "branch": "main",
        "repository_metadata": {
            "file_paths": ["src/index.ts", "src/components/App.tsx", "README.md"]
        }
    })

    file_service = FileService(db_repo=mock_db)
    tree_res = await file_service.get_tree(repo_id)
    assert len(tree_res.tree) == 2  # "src" dir and "README.md" file
    src_node = next(n for n in tree_res.tree if n.name == "src")
    assert src_node.type == "directory"
    assert len(src_node.children) == 2

    # Test chunk content fallback
    from app.retrieval.bm25_index import get_bm25_registry
    chunk = ChunkRecord(
        chunk_id=uuid4(),
        repo_id=repo_id,
        content="# Readme content",
        content_hash="h1",
        filepath="README.md",
        start_line=1,
        end_line=5,
    )
    get_bm25_registry().register(repo_id, [chunk])

    file_res = await file_service.get_file_content(repo_id, "README.md")
    assert file_res.content == "# Readme content"
    assert file_res.language == "markdown"


@pytest.mark.asyncio
async def test_chat_service_streaming_and_sessions():
    from app.services.chat_service import ChatService

    mock_query_svc = MagicMock()
    mock_query_svc.repo_service = MagicMock()
    mock_query_svc.repo_service.assert_ready = AsyncMock()
    mock_query_svc.preprocessor.preprocess = AsyncMock(return_value=("help", [0.1] * 768))
    mock_query_svc.retriever.retrieve = AsyncMock(return_value=([], []))
    mock_query_svc.fusion.fuse = MagicMock(return_value=[])
    mock_query_svc.reranker.rerank = MagicMock(return_value=[])

    chat_service = ChatService(query_service=mock_query_svc)
    valid_repo_id = str(uuid4())
    session = await chat_service.create_session(valid_repo_id)
    assert session.repository_id == valid_repo_id

    events = []
    async for event in chat_service.stream_answer(valid_repo_id, "explain codebase", session_id=session.id):
        events.append(event)

    assert len(events) >= 2
    assert "token" in events[0]
    assert "done" in events[-1]

    msgs = await chat_service.get_messages(session.id)
    assert len(msgs) == 2  # user message and assistant message
    assert msgs[0].role == "user"
    assert msgs[1].role == "assistant"
