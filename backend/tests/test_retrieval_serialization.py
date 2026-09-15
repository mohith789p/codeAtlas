from uuid import uuid4

from app.services.retrieval import RetrievalResult


def test_retrieval_result_serializes_uuid_identity_for_cache_payloads():
    result = RetrievalResult(
        chunk_id=uuid4(),
        repo_id=uuid4(),
        content="def run(): pass",
        filepath="src/run.py",
        symbol="run",
    )

    serialized = result.to_dict()

    assert isinstance(serialized["chunk_id"], str)
    assert isinstance(serialized["repo_id"], str)
    assert serialized["filepath"] == "src/run.py"
    assert serialized["symbol"] == "run"