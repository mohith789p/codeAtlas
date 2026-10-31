from uuid import uuid4
import pytest
from pydantic import ValidationError

from app.schemas.query import QueryOptions, QueryRequest
from app.schemas.repository import Contributor, IngestRequest, IngestionStatus, Repository
from app.schemas.response import GenerationResponse, ValidatedCitation
from app.schemas.retrieval import CacheEntry, ChunkRecord, RetrievalResult


def test_repository_schemas():
    req = IngestRequest(repository_url="https://github.com/fastapi/fastapi")
    assert req.repository_url == "https://github.com/fastapi/fastapi"
    assert req.branch is None

    repo = Repository(name="fastapi", url="https://github.com/fastapi/fastapi")
    assert repo.status == IngestionStatus.QUEUED
    assert repo.stars == 0
    assert len(repo.contributors) == 0


def test_query_schemas():
    repo_id = uuid4()
    req = QueryRequest(repository_id=repo_id, query="Where is the router?")
    assert req.query == "Where is the router?"
    assert req.options.top_k == 4
    assert req.options.similarity_threshold == 0.92

    with pytest.raises(ValidationError):
        QueryRequest(repository_id=repo_id, query="")


def test_retrieval_and_response_schemas():
    chunk = ChunkRecord(
        content_hash="abc",
        content="def hello(): pass",
        filepath="main.py",
        start_line=1,
        end_line=1,
    )
    result = RetrievalResult(chunk=chunk, score=0.88, dense_score=0.9, sparse_score=0.8)
    assert result.score == 0.88
    assert result.chunk.filepath == "main.py"

    citation = ValidatedCitation(filepath="main.py", start_line=1, end_line=1, symbol="hello")
    res = GenerationResponse(
        answer="Found [main.py:1]",
        citations=[citation],
        provider="gemini",
        model="gemini-2.5-flash",
    )
    assert len(res.citations) == 1
    assert res.citations[0].symbol == "hello"
