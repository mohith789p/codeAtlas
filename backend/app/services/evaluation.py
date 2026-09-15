import hashlib
import json
import math
import statistics
import re
import time
from dataclasses import dataclass, asdict
from typing import Any, Protocol
from uuid import UUID

from ..config import Settings
from ..logging_utils import redact_sensitive_text
from .embeddings import GeminiEmbeddingService, LangChainEvaluationEmbeddingService
from .generation import GenerationProvider, GeminiGenerationProvider
from .retrieval import RetrievalService, RetrievalResult
from .reranking import CrossEncoderReranker


class EvaluationError(RuntimeError):
    """Evaluation could not be completed."""


@dataclass(frozen=True)
class GroundTruth:
    content_hash: str
    filepath: str
    symbol: str | None
    symbol_type: str | None
    start_line: int | None
    end_line: int | None


@dataclass(frozen=True)
class EvaluationExample:
    question: str
    answer: str
    ground_truth: GroundTruth
    validation_score: float
    question_embedding: list[float] | None = None


@dataclass(frozen=True)
class EvaluationDecision:
    accepted: list[EvaluationExample]
    rejected: list[dict[str, str]]


class EvaluationPersistence(Protocol):
    async def claim_evaluation(self, repo_id: UUID, eval_version: str) -> bool: ...
    async def list_evaluation_chunks(self, repo_id: UUID) -> list[dict[str, Any]]: ...
    async def save_golden_examples(self, repo_id: UUID, eval_version: str, examples: list[EvaluationExample]) -> None: ...
    async def finish_evaluation(self, repo_id: UUID, eval_version: str, payload: dict[str, Any]) -> None: ...
    async def log_event(self, repository_id: UUID | None, stage: str, level: str, message: str, metadata: dict[str, Any] | None = None, latency_ms: float | None = None) -> None: ...


class DatasetGenerator(Protocol):
    async def generate(self, chunks: list[dict[str, Any]], target_count: int) -> list[dict[str, Any]]: ...


class GeminiEvaluationDatasetGenerator:
    def __init__(self, provider: GenerationProvider) -> None:
        self.provider = provider

    async def generate(self, chunks: list[dict[str, Any]], target_count: int) -> list[dict[str, Any]]:
        if not chunks:
            return []
        selected = chunks[:min(len(chunks), max(30, target_count))]
        if target_count <= 20:
            evidence_batches = [selected]
        else:
            batch_count = math.ceil(target_count / 15)
            evidence_batches = [selected[index % len(selected):index % len(selected) + min(10, len(selected))] for index in range(batch_count)]
        generated: list[dict[str, Any]] = []
        for evidence_batch in evidence_batches:
            remaining = target_count - len(generated)
            if remaining <= 0:
                break
            generated.extend(await self._generate_batch(evidence_batch, min(20, remaining)))
        return generated[:target_count]

    async def _generate_batch(self, selected: list[dict[str, Any]], target_count: int) -> list[dict[str, Any]]:
        evidence = [
            {"filepath": chunk["filepath"], "symbol": chunk.get("symbol"), "content": chunk["content"][:2000]}
            for chunk in selected
        ]
        prompt = (
            "Create repository-specific evaluation questions and concise answers from the supplied code evidence. "
            "Return ONLY a JSON array. Each item must have question, answer, filepath, symbol, symbol_type, start_line, end_line. "
            "Every item must be answerable from its referenced evidence and must not use outside knowledge. "
            f"Create up to {target_count} items, covering different evidence entries. Evidence:\n{json.dumps(evidence)}"
        )
        raw = await self.provider.generate(prompt)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise EvaluationError(f"Evaluation dataset provider returned malformed JSON: {exc}") from exc
        if not isinstance(parsed, list):
            raise EvaluationError("Evaluation dataset provider did not return a JSON array.")
        return [item for item in parsed if isinstance(item, dict)]


class EvaluationDatasetValidator:
    def __init__(self, embedder: Any, similarity_threshold: float = 0.55) -> None:
        self.embedder = embedder
        self.similarity_threshold = similarity_threshold

    async def validate(self, raw_examples: list[dict[str, Any]], chunks: list[dict[str, Any]]) -> EvaluationDecision:
        by_identity = {(chunk["filepath"], chunk.get("symbol")): chunk for chunk in chunks}
        by_path = {chunk["filepath"]: chunk for chunk in chunks}
        accepted: list[EvaluationExample] = []
        rejected: list[dict[str, str]] = []
        seen_questions: set[str] = set()
        questions: list[str] = []
        candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for item in raw_examples:
            question = str(item.get("question", "")).strip()
            answer = str(item.get("answer", "")).strip()
            filepath = str(item.get("filepath", "")).strip()
            symbol = item.get("symbol")
            chunk = by_identity.get((filepath, symbol)) or by_path.get(filepath)
            question_key = question.casefold()
            if question_key in seen_questions:
                rejected.append({"reason": "duplicate question", "question": question})
            elif not question or not answer:
                rejected.append({"reason": "missing question or answer", "question": question})
            elif chunk is None:
                rejected.append({"reason": "ground truth chunk does not exist", "question": question})
            elif symbol and chunk.get("symbol") != symbol:
                rejected.append({"reason": "symbol does not match chunk metadata", "question": question})
            else:
                seen_questions.add(question_key)
                questions.append(question)
                candidates.append((item, chunk))
        if not candidates:
            return EvaluationDecision([], rejected)
        source_contents = [chunk["content"] for _, chunk in candidates]
        vectors = await self.embedder.embed_documents(
            questions + [item["answer"] for item, _ in candidates] + source_contents
        )
        question_vectors = vectors[:len(candidates)]
        answer_start = len(candidates)
        answer_vectors = vectors[answer_start:answer_start + len(candidates)]
        source_vectors = vectors[answer_start + len(candidates):]
        for (item, chunk), question_vector, answer_vector, source_vector in zip(
            candidates, question_vectors, answer_vectors, source_vectors, strict=True
        ):
            question_similarity = _cosine_similarity(question_vector, source_vector)
            answer_similarity = _cosine_similarity(answer_vector, source_vector)
            if question_similarity < self.similarity_threshold:
                rejected.append({"reason": f"question embedding similarity {question_similarity:.3f} below threshold {self.similarity_threshold}", "question": item["question"]})
                continue
            if answer_similarity < self.similarity_threshold:
                rejected.append({"reason": f"answer embedding similarity {answer_similarity:.3f} below threshold {self.similarity_threshold}", "question": item["question"]})
                continue
            unsupported = _unsupported_answer_terms(item["answer"], chunk["content"])
            if unsupported:
                rejected.append({"reason": f"answer claims unsupported evidence terms: {', '.join(unsupported)}", "question": item["question"]})
                continue
            accepted.append(EvaluationExample(
                question=item["question"],
                answer=item["answer"],
                ground_truth=GroundTruth(
                    content_hash=chunk["content_hash"], filepath=chunk["filepath"], symbol=chunk.get("symbol"),
                    symbol_type=chunk.get("symbol_type"), start_line=chunk.get("start_line"), end_line=chunk.get("end_line"),
                ),
                validation_score=min(question_similarity, answer_similarity),
                question_embedding=question_vector,
            ))
        return EvaluationDecision(accepted, rejected)


def calculate_metrics(evaluations: list[tuple[EvaluationExample, list[RetrievalResult], float]]) -> dict[str, Any]:
    if not evaluations:
        return {"query_count": 0, "recall_at_5": 0.0, "precision_at_5": 0.0, "mrr": 0.0, "latency_stats": {}}
    recall_values: list[float] = []
    precision_values: list[float] = []
    reciprocal_ranks: list[float] = []
    latencies = [latency for _, _, latency in evaluations]
    per_query = []
    for example, results, latency in evaluations:
        relevant = [result for result in results if _is_relevant(result, example.ground_truth)]
        top_five = results[:5]
        relevant_top_five = [result for result in top_five if _is_relevant(result, example.ground_truth)]
        recall = 1.0 if relevant_top_five else 0.0
        precision = len(relevant_top_five) / 5
        rank = next((index for index, result in enumerate(results, start=1) if _is_relevant(result, example.ground_truth)), None)
        reciprocal = 1.0 / rank if rank else 0.0
        recall_values.append(recall)
        precision_values.append(precision)
        reciprocal_ranks.append(reciprocal)
        per_query.append({"question": example.question, "ground_truth": asdict(example.ground_truth), "retrieved": [result.to_dict() for result in results], "recall_at_5": recall, "precision_at_5": precision, "reciprocal_rank": reciprocal, "latency_ms": latency})
    return {
        "query_count": len(evaluations), "recall_at_5": statistics.mean(recall_values),
        "precision_at_5": statistics.mean(precision_values), "mrr": statistics.mean(reciprocal_ranks),
        "latency_stats": {"average": statistics.mean(latencies), "median": statistics.median(latencies), "min": min(latencies), "max": max(latencies)},
        "per_query": per_query,
    }


class EvaluationService:
    def __init__(self, persistence: EvaluationPersistence, retrieval: RetrievalService, generator: DatasetGenerator, validator: EvaluationDatasetValidator, target_count: int = 100) -> None:
        self.persistence = persistence
        self.retrieval = retrieval
        self.generator = generator
        self.validator = validator
        self.target_count = target_count

    async def evaluate_once(self, repo_id: UUID, eval_version: str | None = None, limit: int | None = None) -> dict[str, Any] | None:
        chunks = await self.persistence.list_evaluation_chunks(repo_id)
        version = eval_version or evaluation_version(chunks)
        if not await self.persistence.claim_evaluation(repo_id, version):
            return None
        started = time.perf_counter()
        try:
            await self.persistence.log_event(repo_id, "evaluation_started", "info", "Evaluation started", {"eval_version": version})
            generation_started = time.perf_counter()
            raw = await self.generator.generate(chunks, limit or self.target_count)
            generation_ms = (time.perf_counter() - generation_started) * 1000
            validation_started = time.perf_counter()
            decision = await self.validator.validate(raw, chunks)
            validation_ms = (time.perf_counter() - validation_started) * 1000
            await self.persistence.log_event(repo_id, "evaluation_dataset_validation", "info", "Evaluation dataset validated", {"generated": len(raw), "accepted": len(decision.accepted), "rejected": len(decision.rejected), "rejection_reasons": decision.rejected, "generation_latency_ms": generation_ms, "validation_latency_ms": validation_ms, "embedding": _embedding_stats(self.validator.embedder)})
            await self.persistence.save_golden_examples(repo_id, version, decision.accepted)
            evaluations: list[tuple[EvaluationExample, list[RetrievalResult], float]] = []
            for example in decision.accepted[:limit or len(decision.accepted)]:
                query_started = time.perf_counter()
                result = await self.retrieval.retrieve(repo_id, example.question, allow_cache_hit=False)
                latency = (time.perf_counter() - query_started) * 1000
                evaluations.append((example, [_result_from_dict(item) for item in result["results"]], latency))
            metrics = calculate_metrics(evaluations)
            payload = {"status": "completed", "generated_count": len(raw), "accepted_count": len(decision.accepted), "rejected_count": len(decision.rejected), "successful_count": len(evaluations), "failed_count": len(decision.accepted) - len(evaluations), "rejection_reasons": decision.rejected, **metrics, "total_latency_ms": (time.perf_counter() - started) * 1000}
            await self.persistence.finish_evaluation(repo_id, version, payload)
            await self.persistence.log_event(repo_id, "evaluation_completed", "info", "Evaluation completed", {"eval_version": version, **{key: value for key, value in payload.items() if key in {"recall_at_5", "precision_at_5", "mrr", "query_count"}}, "generation_latency_ms": generation_ms, "validation_latency_ms": validation_ms, "embedding": _embedding_stats(self.validator.embedder)}, payload["total_latency_ms"])
            return payload
        except Exception as exc:
            safe_error = redact_sensitive_text(str(exc))
            payload = {"status": "failed", "error": safe_error, "total_latency_ms": (time.perf_counter() - started) * 1000}
            await self.persistence.finish_evaluation(repo_id, version, payload)
            await self.persistence.log_event(repo_id, "evaluation_failed", "error", "Evaluation failed", {"error": safe_error, "embedding": _embedding_stats(self.validator.embedder)}, payload["total_latency_ms"])
            raise EvaluationError(safe_error) from exc


def evaluation_version(chunks: list[dict[str, Any]]) -> str:
    identity = "|".join(sorted(chunk["content_hash"] for chunk in chunks))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def _embedding_stats(embedder: Any) -> dict[str, int]:
    return {key: int(getattr(embedder, key, 0)) for key in ("request_count", "retry_count", "rate_limit_count")}


def _is_relevant(result: RetrievalResult, truth: GroundTruth) -> bool:
    content_hash = hashlib.sha256(result.content.encode("utf-8")).hexdigest()
    return content_hash == truth.content_hash and result.filepath == truth.filepath and (truth.symbol is None or result.symbol == truth.symbol)


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left or not right:
        return 0.0
    denominator = math.sqrt(sum(value * value for value in left)) * math.sqrt(sum(value * value for value in right))
    return sum(a * b for a, b in zip(left, right)) / denominator if denominator else 0.0


_TOKEN_PATTERN = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z_][A-Za-z0-9_]*(?:[./-][A-Za-z0-9_]+)*(?![A-Za-z0-9_])")
_NUMBER_PATTERN = re.compile(r"(?<![A-Za-z0-9_])(?:\d+x\d+|v?\d+(?:\.\d+)+(?:[-+][A-Za-z0-9.-]+)?|\d+(?:\.\d+)?%?)(?![A-Za-z0-9_])", re.IGNORECASE)
_ACRONYM_PATTERN = re.compile(r"(?<![A-Za-z0-9_])[A-Z]{2,}[A-Z0-9_]*(?![A-Za-z0-9_])")
_BACKTICK_PATTERN = re.compile(r"`([^`]+)`")
_LIST_PATTERN = re.compile(
    r"\b(?:libraries?|packages?|dependencies?|requirements?|modules?|frameworks?|tools?)\b"
    r"\s+(?:are|include|listed(?:\s+as)?|such\s+as)\s+([^.;]+)",
    re.IGNORECASE,
)


def _normalise_anchor(value: str) -> str:
    return value.strip().strip("`.,;:()[]{}").casefold()


def _content_tokens(content: str) -> set[str]:
    return {_normalise_anchor(match.group(0)) for match in _TOKEN_PATTERN.finditer(content)} | {
        _normalise_anchor(match.group(0)) for match in _NUMBER_PATTERN.finditer(content)
    }


def _answer_anchors(answer: str) -> set[str]:
    anchors = {_normalise_anchor(match.group(1)) for match in _BACKTICK_PATTERN.finditer(answer)}
    anchors.update(_normalise_anchor(match.group(0)) for match in _NUMBER_PATTERN.finditer(answer))
    anchors.update(_normalise_anchor(match.group(0)) for match in _ACRONYM_PATTERN.finditer(answer))
    for match in _TOKEN_PATTERN.finditer(answer):
        token = match.group(0)
        if any(character in token for character in "_/-.") or any(character.isdigit() for character in token) or re.search(r"[a-z][A-Z]", token):
            anchors.add(_normalise_anchor(token))
    for match in _LIST_PATTERN.finditer(answer):
        for item in re.split(r",|\band\b|\bor\b", match.group(1), flags=re.IGNORECASE):
            item_tokens = _TOKEN_PATTERN.findall(item)
            if item_tokens:
                anchors.add(_normalise_anchor(item_tokens[-1]))
    return {anchor for anchor in anchors if anchor}


def _unsupported_answer_terms(answer: str, content: str) -> list[str]:
    content_tokens = _content_tokens(content)
    return sorted(anchor for anchor in _answer_anchors(answer) if anchor not in content_tokens)


def _result_from_dict(value: dict[str, Any]) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=value["chunk_id"], repo_id=value["repo_id"], content=value["content"], filepath=value["filepath"],
        language=value.get("language"), symbol=value.get("symbol"), symbol_type=value.get("symbol_type"), class_name=value.get("class_name"),
        parent_symbol=value.get("parent_symbol"), start_line=value.get("start_line"), end_line=value.get("end_line"), imports=value.get("imports") or [],
        dense_score=value.get("dense_score"), dense_rank=value.get("dense_rank"), sparse_score=value.get("sparse_score"), sparse_rank=value.get("sparse_rank"),
        rrf_score=value.get("rrf_score"), rrf_rank=value.get("rrf_rank"), reranker_score=value.get("reranker_score"), reranker_rank=value.get("reranker_rank"),
    )


def build_evaluation_service(settings: Settings, persistence: EvaluationPersistence) -> EvaluationService:
    generator = GeminiEvaluationDatasetGenerator(GeminiGenerationProvider(settings, model=settings.gemini_summary_model))
    production_embedder = GeminiEmbeddingService(settings)
    evaluation_embedder = LangChainEvaluationEmbeddingService(settings.evaluation_embedding_model)
    retrieval = RetrievalService(persistence, production_embedder, CrossEncoderReranker(settings.reranker_model))
    return EvaluationService(
        persistence,
        retrieval,
        generator,
        EvaluationDatasetValidator(evaluation_embedder, settings.evaluation_embedding_similarity_threshold),
        settings.evaluation_target_count,
    )
