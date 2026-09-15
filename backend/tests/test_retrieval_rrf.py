from uuid import uuid4

from app.services.retrieval import reciprocal_rank_fusion
from app.services.retrieval import RetrievalResult


def result(identifier: str, score: float = 1.0) -> RetrievalResult:
    return RetrievalResult(chunk_id=identifier, repo_id="repo", content=identifier, filepath=f"{identifier}.py", dense_score=score)


def test_rrf_boosts_overlap_and_is_deterministic():
    fused = reciprocal_rank_fusion([result("a"), result("b")], [result("b"), result("c")], limit=3)
    assert [item.chunk_id for item in fused] == ["b", "a", "c"]
    assert fused[0].dense_rank == 2
    assert fused[0].sparse_rank == 1


def test_rrf_handles_empty_inputs_and_limit():
    assert reciprocal_rank_fusion([], []) == []
    dense = [result(str(index)) for index in range(20)]
    assert len(reciprocal_rank_fusion(dense, [], limit=15)) == 15


def test_rrf_preserves_metadata_from_first_seen_candidate():
    dense_result = RetrievalResult(chunk_id=uuid4(), repo_id="repo", content="source", filepath="src/a.py", symbol="run")
    sparse_result = RetrievalResult(chunk_id=dense_result.chunk_id, repo_id="repo", content="source", filepath="src/a.py", symbol="run", sparse_score=4.0)
    fused = reciprocal_rank_fusion([dense_result], [sparse_result])
    assert fused[0].symbol == "run"
    assert fused[0].dense_rank == 1
    assert fused[0].sparse_rank == 1
