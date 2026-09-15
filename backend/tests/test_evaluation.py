import hashlib
from uuid import uuid4

import pytest

from app.services.evaluation import (
    EvaluationDatasetValidator,
    EvaluationExample,
    EvaluationService,
    GroundTruth,
    calculate_metrics,
    evaluation_version,
)
from app.services.retrieval import RetrievalResult


class FakeEmbedder:
    async def embed_documents(self, texts):
        return [[1.0, 0.0] for _ in texts]


class FakeGenerator:
    async def generate(self, chunks, target_count):
        return [
            {"question": "What does run do?", "answer": "It returns 42.", "filepath": "src/run.py", "symbol": "run"},
            {"question": "What is missing?", "answer": "Unknown.", "filepath": "missing.py", "symbol": "nope"},
        ][:target_count]


class DuplicateGenerator:
    async def generate(self, chunks, target_count):
        return [
            {"question": "What does run do?", "answer": "It returns 42.", "filepath": "src/run.py", "symbol": "run"},
            {"question": "What does run do?", "answer": "It returns 42.", "filepath": "src/run.py", "symbol": "run"},
        ]


class FakePersistence:
    def __init__(self, chunks):
        self.chunks = chunks
        self.claims = set()
        self.golden = []
        self.finished = []
        self.events = []

    async def claim_evaluation(self, repo_id, eval_version):
        key = (repo_id, eval_version)
        if key in self.claims:
            return False
        self.claims.add(key)
        return True

    async def list_evaluation_chunks(self, repo_id):
        return self.chunks

    async def save_golden_examples(self, repo_id, eval_version, examples):
        self.golden.extend(examples)

    async def finish_evaluation(self, repo_id, eval_version, payload):
        self.finished.append(payload)

    async def log_event(self, repository_id, stage, level, message, metadata=None, latency_ms=None):
        self.events.append((stage, level, metadata, latency_ms))


class FakeRetrieval:
    async def retrieve(self, repo_id, query, allow_cache_hit=True):
        return {"results": [{
            "chunk_id": "row-recreated",
            "repo_id": str(repo_id),
            "content": "def run(): return 42",
            "filepath": "src/run.py",
            "symbol": "run",
            "symbol_type": "function_definition",
            "start_line": 1,
            "end_line": 1,
            "imports": [],
        }]}


def chunks():
    return [{
        "content_hash": hashlib.sha256(b"def run(): return 42").hexdigest(),
        "content": "def run(): return 42",
        "embedding": [1.0, 0.0],
        "filepath": "src/run.py",
        "language": "python",
        "symbol": "run",
        "symbol_type": "function_definition",
        "start_line": 1,
        "end_line": 1,
        "imports": [],
    }]


def example():
    return EvaluationExample("What does run do?", "It returns 42.", GroundTruth(hashlib.sha256(b"def run(): return 42").hexdigest(), "src/run.py", "run", "function_definition", 1, 1), 0.9)


@pytest.mark.asyncio
async def test_dataset_validation_accepts_grounded_and_rejects_missing_chunk():
    decision = await EvaluationDatasetValidator(FakeEmbedder(), similarity_threshold=0.5).validate(await FakeGenerator().generate(chunks(), 2), chunks())
    assert len(decision.accepted) == 1
    assert decision.accepted[0].ground_truth.content_hash == chunks()[0]["content_hash"]
    assert decision.rejected[0]["reason"] == "ground truth chunk does not exist"


@pytest.mark.asyncio
async def test_dataset_validation_rejects_duplicate_questions():
    decision = await EvaluationDatasetValidator(FakeEmbedder(), similarity_threshold=0.5).validate(await DuplicateGenerator().generate(chunks(), 2), chunks())
    assert len(decision.accepted) == 1
    assert decision.rejected[0]["reason"] == "duplicate question"


@pytest.mark.asyncio
async def test_dataset_validation_rejects_answer_claims_absent_from_ground_truth():
    raw = [{
        "question": "What resolution is recommended?",
        "answer": "The recommended resolution is 224x224.",
        "filepath": "README.md",
        "symbol": None,
    }]
    source = [{
        "content_hash": hashlib.sha256(b"Use frame_skip for performance.").hexdigest(),
        "content": "Use frame_skip for performance.",
        "embedding": [1.0, 0.0],
        "filepath": "README.md",
        "symbol": None,
        "symbol_type": None,
        "start_line": 1,
        "end_line": 1,
    }]

    decision = await EvaluationDatasetValidator(FakeEmbedder(), similarity_threshold=0.5).validate(raw, source)

    assert decision.accepted == []
    assert "unsupported evidence terms" in decision.rejected[0]["reason"]


def evidence_source(content):
    return [{
        "content_hash": hashlib.sha256(content.encode()).hexdigest(),
        "content": content,
        "embedding": [1.0, 0.0],
        "filepath": "README.md",
        "symbol": None,
        "symbol_type": None,
        "start_line": 1,
        "end_line": 4,
    }]


async def validate_answer(answer, content):
    raw = [{"question": "What does the evidence say?", "answer": answer, "filepath": "README.md", "symbol": None}]
    return await EvaluationDatasetValidator(FakeEmbedder(), similarity_threshold=0.5).validate(raw, evidence_source(content))


@pytest.mark.asyncio
async def test_validator_uses_exact_package_boundaries():
    absent = await validate_answer("The required libraries are torch.", "torchvision\ntransformers")
    present = await validate_answer("The required libraries are torch.", "torch\ntransformers")

    assert absent.accepted == []
    assert "torch" in absent.rejected[0]["reason"]
    assert len(present.accepted) == 1


@pytest.mark.asyncio
async def test_validator_checks_dimensions_without_substring_matching():
    absent = await validate_answer("The image size is 224x224.", "The image size is 512x512.")
    present = await validate_answer("The image size is 224x224.", "The image size is 224x224.")

    assert absent.accepted == []
    assert present.accepted


@pytest.mark.asyncio
async def test_validator_checks_backticked_identifiers_with_exact_boundaries():
    absent = await validate_answer("Call `run_pipeline`.", "Call `run_pipeline_v2`.")
    present = await validate_answer("Call `run_pipeline`.", "Call `run_pipeline`.")

    assert absent.accepted == []
    assert present.accepted


@pytest.mark.asyncio
async def test_validator_checks_uppercase_technical_acronyms():
    absent = await validate_answer("The service uses GPU acceleration.", "The service uses CPU acceleration.")
    present = await validate_answer("The service uses GPU acceleration.", "The service uses GPU acceleration.")

    assert absent.accepted == []
    assert present.accepted


def test_ground_truth_version_uses_content_hash_not_row_id():
    version_a = evaluation_version(chunks())
    changed = [{**chunks()[0], "content_hash": "b" * 64, "id": "different-row-id"}]
    assert version_a != evaluation_version(changed)


def test_metrics_recall_precision_and_mrr_are_mathematically_correct():
    truth = example()
    result = RetrievalResult("row", "repo", "def run(): return 42", "src/run.py", symbol="run", start_line=1, end_line=1)
    metrics = calculate_metrics([(truth, [result], 12.0)])
    assert metrics["recall_at_5"] == 1.0
    assert metrics["precision_at_5"] == 0.2
    assert metrics["mrr"] == 1.0
    assert metrics["latency_stats"]["average"] == 12.0


def test_metrics_zero_relevant_results():
    truth = example()
    result = RetrievalResult("other", "repo", "other", "other.py", symbol="other")
    metrics = calculate_metrics([(truth, [result], 4.0)])
    assert metrics["recall_at_5"] == 0.0
    assert metrics["precision_at_5"] == 0.0
    assert metrics["mrr"] == 0.0


@pytest.mark.asyncio
async def test_evaluation_service_uses_production_retrieval_and_is_exactly_once():
    persistence = FakePersistence(chunks())
    service = EvaluationService(persistence, FakeRetrieval(), FakeGenerator(), EvaluationDatasetValidator(FakeEmbedder()), target_count=2)
    repo_id = uuid4()

    first = await service.evaluate_once(repo_id, eval_version="version-1", limit=2)
    second = await service.evaluate_once(repo_id, eval_version="version-1", limit=2)

    assert first["accepted_count"] == 1
    assert first["query_count"] == 1
    assert first["recall_at_5"] == 1.0
    assert second is None
    assert len(persistence.finished) == 1
    assert any(event[0] == "evaluation_completed" for event in persistence.events)
    validation_event = next(event for event in persistence.events if event[0] == "evaluation_dataset_validation")
    assert "rejection_reasons" in validation_event[2]
