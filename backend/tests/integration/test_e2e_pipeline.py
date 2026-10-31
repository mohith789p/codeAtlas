from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import pytest

from app.database.repositories import DatabaseRepository
from app.embeddings.embedding_service import EmbeddingService
from app.generation.step_02_llm_client import LLMClientChain
from app.ingestion.step_05_chunker import ASTChunker
from app.retrieval.bm25_index import get_bm25_registry
from app.retrieval.step_04_rrf_fusion import RRFFusion
from app.schemas.query import QueryOptions
from app.services.query_service import QueryService
from app.services.repository_service import RepositoryService


@pytest.mark.asyncio
async def test_end_to_end_chunk_retrieve_and_answer():
    repo_id = uuid4()
    code = (
        "class AuthManager:\n"
        "    def authenticate(self, token: str) -> bool:\n"
        "        return token == 'valid-secret'\n"
    )

    # 1. Real AST Chunking
    chunker = ASTChunker()
    chunks = chunker.chunk_file("auth.py", code)
    assert len(chunks) >= 1

    # 2. Warm real BM25 Registry
    registry = get_bm25_registry()
    registry.register(repo_id, chunks)

    # 3. Setup QueryService with mocked external API dependencies
    mock_db = MagicMock(spec=DatabaseRepository)
    mock_db.dense_search = AsyncMock(return_value=[])
    mock_db.sparse_search = AsyncMock(return_value=[])
    mock_db.get_repo = AsyncMock(return_value={"id": str(repo_id), "name": "auth-repo", "status": "ready"})
    mock_db.get_semantic_cache = AsyncMock(return_value=None)
    mock_db.save_semantic_cache = AsyncMock()

    mock_embedder = MagicMock(spec=EmbeddingService)
    mock_embedder.embed_documents = AsyncMock(return_value=[[0.05] * 768])

    mock_llm = MagicMock(spec=LLMClientChain)
    mock_llm.generate = AsyncMock(return_value=(
        "The token is verified in [auth.py:2-3] inside function authenticate.",
        "groq",
        "llama-3.3-70b-versatile",
    ))

    repo_service = RepositoryService(db_repo=mock_db)
    query_service = QueryService(repo_service=repo_service)
    query_service.preprocessor.embedder = mock_embedder
    query_service.generator.llm_client = mock_llm

    # 4. Execute query
    response = await query_service.query(repo_id, "How does authentication work?", QueryOptions(use_cache=False))

    # 5. Assert citations and response
    assert response.provider == "groq"
    assert len(response.citations) >= 1
    assert response.citations[0].filepath == "auth.py"
    assert response.citations[0].symbol == "authenticate"
    registry.clear(repo_id)
