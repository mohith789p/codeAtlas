# Code Atlas Implementation Status

Updated: 2026-09-11

## Milestone 1: Ingestion

Verified with the `visual-interpreter` public repository:

- GitHub acquisition, size pre-check, streamed download, extraction, filtering, and Tree-sitter chunking.
- Gemini `gemini-embedding-001` embeddings with 768 dimensions.
- Supabase chunk and normalized metadata persistence.
- Content-hash embedding reuse on repeated ingestion.
- Honest `ready`/`failed` lifecycle transitions.

## Milestone 2: Retrieval

Verified against persisted Supabase data:

- Same-space Gemini query embeddings.
- Repository-scoped semantic cache.
- Dense HNSW `match_chunks` top-20 RPC.
- Sparse full-text/exact-symbol `search_chunks` top-20 RPC.
- Parallel dense and sparse retrieval.
- Deterministic RRF, top-15 truncation.
- LangChain `HuggingFaceCrossEncoder` using `cross-encoder/ms-marco-MiniLM-L-6-v2`, top-5 output.
- Structural metadata preserved through final results.

## Milestone 3: Generation, Memory, Citations, Validation

Implemented and live-verified:

- Generation pipeline consumes only retrieval Top-5 results.
- Provider fallback order: Gemini, Groq, Cerebras, OpenRouter.
- Gemini generation uses `gemini-2.5-flash`; summary uses `gemini-2.5-flash-lite`.
- Session-scoped recent-turn memory with bounded context and older-turn summary support.
- Structured Markdown prompt with complete source metadata.
- Deterministic citation validation for filepath, line range, retrieved chunk, and symbol.
- Deterministic grounding check requiring retrieved prose evidence in addition to citations.
- Chat API returns frontend-compatible citations: `file`, `line_start`, `line_end`, `symbol`, and `chunk_id`.
- Provider selection, fallback, generation latency, validation, and completion events are logged to Supabase.
- No-retrieval behavior remains: `I couldn't find relevant information in this project.`

Live generation smoke test passed through the existing ready repository and produced a validated source citation.

## Known Issues

The API's in-memory repository registry is not hydrated from Supabase after a backend restart. This is a pre-existing infrastructure limitation and is intentionally tracked separately from the completed retrieval and generation slices.

Generation live verification currently exercises the configured Gemini provider. Fallback providers have deterministic unit coverage but require their own credentials for live provider testing.

Generation is complete for this milestone. Offline evaluation is also implemented and verified below.

## Milestone 4: Offline Evaluation

Implemented and live-verified against the ready `visual-interpreter` repository:

- `EvaluationService` runs the existing production `RetrievalService` for evaluation questions.
- Dataset generation uses the separate configured Gemini summary model and a bounded repository evidence set.
- Dataset validation rejects missing files, mismatched symbols, duplicate questions, and low embedding similarity examples.
- Ground truth uses content hash, filepath, symbol, symbol type, and source line metadata; it never uses chunk row IDs.
- Recall@5, Precision@5, MRR, per-query rank contributions, and latency statistics are calculated.
- `eval_golden_set` and `eval_results` persistence is defined in migration 0003.
- Evaluation claims are unique by `(repo_id, eval_version)` for restart-safe exactly-once behavior.
- READY ingestion automatically invokes the injected evaluation worker; evaluation failures are logged without changing READY back to FAILED.
- A controlled five-question live test is available at `tests/test_live_evaluation.py`.

The evaluation schema migrations were applied and the persisted evaluation result and golden-set rows were audited. Standard evaluation tests do not require live services.

## Evaluation Pipeline Correction

Diagnosis found that the deployed semantic-cache RPC returned stale results for unrelated queries because its parameter names were ambiguous. Migration 0004 replaces it with explicitly qualified parameters and the persistence adapter now sends those names.

Evaluation validation now checks both question and answer embedding similarity and rejects unsupported concrete factual anchors such as absent numbers, identifiers, or code literals. The stable content-hash ground-truth design and metric formulas are unchanged.

Migration 0004 was applied and the corrected semantic-cache RPC was live-verified. Evaluation now uses the separate LangChain HuggingFace embedding model for validation, the separate Gemini summary model for candidate generation, and disables semantic-cache reads and writes while invoking the production `RetrievalService`.

The frozen historical benchmark `full-100-20260910-v2` generated 100 candidates, accepted 51, and executed 51 retrieval queries with 0 failed queries. Its metrics were Recall@5 `0.9608`, Precision@5 `0.1922`, and MRR `0.8856`; average latency was `3359.75 ms`, median `2206.95 ms`, minimum `1502.22 ms`, and maximum `13546.84 ms`.

That benchmark was generated before the final evaluation-provider and cache-isolation corrections. It is preserved as historical validation evidence and was not rerun after those corrections.
