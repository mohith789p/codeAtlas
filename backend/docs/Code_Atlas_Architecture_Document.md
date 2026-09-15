# Code Atlas — System Architecture Document

**Project Type:** Individual GenAI portfolio project
**Purpose of this document:** Define the finalized architecture, data flow, and design rationale for Code Atlas, following an architecture review pass.

---

## 1. Overview

Code Atlas is a knowledge-representation platform that lets a user point at any public GitHub repository and interact with it through natural-language chat. Instead of treating the codebase as flat text, it parses code structurally (via tree-sitter), builds a hybrid dense + sparse retrieval index over semantically meaningful chunks, and answers questions with cited, line-accurate references back into the source.

**Design goals for this iteration:**
- Demonstrate structural code understanding, not generic document RAG.
- Use retrieval and generation techniques that are individually defensible in a technical interview (no "because it sounded good" choices).
- Be measurable — every stage of the pipeline produces a metric, not just a final answer.
- Explicitly scoped as a portfolio project: no auth, global logs, free-tier LLM providers — stated as intentional trade-offs, not oversights.

**Explicitly out of scope:** authentication/authorization, per-user data isolation, multi-tenant billing, production-grade horizontal scaling.

---

## 2. High-Level Architecture

```
┌──────────────────────────┐        ┌───────────────────────────┐
│      INGESTION PATH        │        │       RETRIEVAL PATH        │
│    (async background job)  │        │      (user chat query)      │
└──────────────────────────┘        └───────────────────────────┘

 GitHub URL / user_id+repo_id           User query (chat)
        │                                     │
        ▼                                     ▼
 Repo size pre-check (GitHub API)      Embed query (Gemini)
        │                                     │
        ▼                                     ▼
 Streamed zip download                Semantic cache check (per repo_id)
 (chunked, timeout 10/30, 1MB/chunk)     │hit → return cached answer
        │                                │miss ↓
        ▼                                     ▼
 Extract (zipfile)                Hybrid retrieval:
        │                          HNSW dense top-20  +  BM25 sparse top-20
        ▼                                     │
 Layered filtering                            ▼
 (.gitignore → static → size → binary)   Reciprocal Rank Fusion (RRF)
        │                                     │
        ▼                                     ▼
 Tree-sitter AST parsing                 Truncate to top-15
 (symbol/class/parent/import extraction)      │
        │                                     ▼
        ▼                          Cross-encoder rerank → top-5
 Chunk as LangChain Documents                 │
 (size tiers by file type, 10% overlap) ┌─────┴─────┐
        │                          top-5 empty?   top-5 found
        ▼                               │             │
 Embed chunks (Gemini, rate-limited)     ▼             ▼
        │                        "No relevant    Augment prompt
        ▼                         info found"    (query + top-5 + memory)
 Insert into Supabase                                  │
 (chunks table + metadata table,                       ▼
  content-hash keyed)                       LLM fallback chain:
        │                              Gemini → Groq → Cerebras → OpenRouter
        ▼                                            │
 Ingestion job marked "ready"                         ▼
        │                                  Markdown answer + citations
        ▼                                            │
 Trigger offline eval worker                          ▼
 (auto, once, post-ingestion)              Quality validation:
        │                              citation + line + symbol + grounding
        ▼                                            │
 Generate & validate 100–150                          ▼
 Q&A pairs (separate LLM +                  Write query to semantic cache
 embedding model, embedding-                          │
 similarity validation)                               ▼
        │                                  Log turn + metrics to Supabase
        ▼
 Evaluate real retrieval pipeline
 → Recall@5, Precision@5, MRR
        │
        ▼
 Log metrics + latency to Supabase
```

---

## 3. Ingestion Pipeline (Async Background Job)

Ingestion is decoupled from the HTTP request lifecycle. The client receives a job ID immediately and polls (or subscribes via Supabase Realtime) for status: `queued → downloading → filtering → chunking → embedding → indexing → ready | failed`.

### 3.1 Acquisition
1. Input: GitHub URL, or `user_id` + `repo_id` (used to construct the URL).
2. **Repo-size pre-check** via the GitHub API before pulling any content — reject or warn on repos beyond a configured size ceiling, before spending bandwidth or time.
3. Stream-download the archive via HTTP with a connect timeout of 10s and read timeout of 30s, in 1MB chunks — bounds memory usage and tolerates large repos on constrained bandwidth.
4. Extract with Python's `zipfile`.

### 3.2 Filtering (layered, cheapest checks first)
1. **Dynamic:** honor the repo's own `.gitignore` via `pathspec`.
2. **Static:** discard known non-source noise (lockfiles, generated assets, vendored dependencies, etc.).
3. **Size:** discard files over 1MB.
4. **Binary:** discard non-text files.

### 3.3 Structural Chunking (Tree-sitter)
Rather than splitting on character/line heuristics, each supported source file is parsed into an AST using **tree-sitter**. Chunk boundaries are drawn along real function/class/method boundaries, which yields metadata that a generic text splitter cannot produce:

| Metadata field | Source |
|---|---|
| `filepath`, `language` | file system + extension/tree-sitter grammar |
| `symbol`, `symbol_type` | AST node (function/class/method name and kind) |
| `class_name`, `parent_symbol` | AST parent-chain traversal (handles nested classes/methods) |
| `start_line`, `end_line` | AST node span |
| `imports` | extracted separately from the AST, stored as their own metadata to preserve parent–child (module → symbol) relationships without polluting code-chunk boundaries |

For unsupported file types (JSON, YAML, config, build files), a custom splitter is used, since there's no meaningful "symbol" concept to parse structurally.

Each resulting chunk — code or non-code — is wrapped as a **LangChain `Document`** (`page_content` + `metadata` dict), keeping the rest of the pipeline (embedding calls, vector store interface, retriever composition) LangChain-native regardless of how the chunk boundary was decided.

**Chunk size targets (characters, ~10% overlap):**

| File type | Size range |
|---|---|
| Source code | 800–1000 |
| Config | 600–800 |
| Documents | 1000–1200 |
| Build files | 1200–1500 |

### 3.4 Embedding & Storage
- Chunks are embedded via the **Gemini embedding model**, with request-level rate limiting to stay within free-tier quotas.
- Storage is normalized into two Supabase tables:
  - `chunks` — embedding vector + raw content, indexed with **HNSW (cosine similarity)** for dense search and a full-text index for **BM25 sparse search**.
  - `chunk_metadata` — symbol/class/parent/line/import fields, joined by chunk ID.
  - **Rationale:** normalization keeps the vector index itself lean (faster HNSW builds/queries) and avoids duplicating repeated file-level metadata across chunks — not, as sometimes assumed, a way to "avoid full scans" (the HNSW index already avoids that regardless of table layout).
- Every chunk is keyed by a **content hash**, so re-ingesting the same repo (or a lightly updated version of it) skips re-embedding unchanged chunks — cheaper re-ingestion and idempotent by design.

### 3.5 Post-Ingestion Trigger
Once a repo's ingestion job reaches `ready`, it automatically triggers the offline evaluation worker (Section 6) — no manual step required.

---

## 4. Retrieval Pipeline

Triggered per user chat query, fully synchronous (fast enough not to need async handling):

1. **Embed the query** using the same embedding model used for chunks (Gemini).
2. **Semantic cache check**, scoped by `repo_id` (critical: prevents a cached answer for one repository leaking into a query about a different repository). On hit, return immediately.
3. On miss, run **hybrid retrieval** in parallel:
   - Dense: HNSW cosine similarity search, top-20.
   - Sparse: BM25 / Postgres full-text search over chunk content (and optionally exact match against the `symbol` metadata field, since a literal function name typed by the user should surface that function even with mediocre embedding similarity).
4. **Fuse** the two top-20 lists via **Reciprocal Rank Fusion (RRF)**.
5. **Truncate** the fused list to the top 15.
6. **Rerank** with a cross-encoder, keeping the final **top 5**.
7. If the top-5 set is empty, short-circuit and return: *"I couldn't find relevant information in this project."*
8. Otherwise, write the query into the semantic cache (per `repo_id`) and proceed to generation.

**Why hybrid dense+sparse instead of dense (ANN) + dense (exact):** approximate and exact search over the *same* embedding space return near-identical results at repo-scale vector counts, so fusing them adds negligible diversity for the extra full-scan cost. Fusing dense semantic similarity with sparse lexical/exact-match signal captures genuinely different information — the classic, defensible hybrid-search pattern.

---

## 5. Generation & Memory

- **Prompt composition:** user query + top-5 reranked chunks (with their metadata) + conversation memory.
- **LLM fallback chain** (free-tier availability strategy, rate-limited at each hop): **Gemini → Groq → Cerebras → OpenRouter**.
- **Memory:** most-recent-turns verbatim + a running summary of older turns, summarized by a smaller/cheaper model, kept under a fixed context-window budget.
- **Output format:** Markdown, with inline citations pointing back to `filepath:start_line-end_line` and symbol name.
- **Response quality validation**, run before the answer is returned:
  - Citation validation — cited chunks actually exist and were part of the retrieved set.
  - Line validation — cited line ranges are accurate to the source file.
  - Symbol validation — referenced symbol names match the AST-extracted metadata.
  - Context grounding — the answer's claims are supported by the retrieved chunks (not fabricated).

---

## 6. Offline Evaluation & Metrics

A fully **offline, asynchronous evaluation worker** — isolated from user-facing inference cost and latency.

**Trigger:** automatic, exactly once, immediately after a repo's ingestion job reaches `ready`.

**Process:**
1. Using a **separate LLM and embedding model** from the production stack (avoids self-grading bias, and keeps eval traffic off the rate-limited providers serving real users), generate **100–150 repository-specific Q&A pairs** in batches, each tagged with its intended ground-truth chunk.
2. **Validate** each candidate pair via an **embedding-similarity threshold** between the generated question and its source chunk — a deterministic, cost-free check rather than a second LLM judge pass.
3. Ground-truth chunk references are keyed by **content hash / symbol identity**, not raw row ID — so minor re-ingestion edits (e.g. a small commit) don't silently invalidate the whole golden set. Only a re-ingestion that actually changes a referenced chunk's content triggers regeneration of that entry.
4. Run the **real production retrieval pipeline** (HNSW + BM25 → RRF → top-15 → cross-encoder → top-5) against the golden set.
5. Compute **Recall@5, Precision@5, and MRR** per repo, and log alongside per-stage latency.

**Why this matters:** without an explicit, stored ground truth, "Recall@5 / Precision@5 / MRR" are unmeasurable claims. This design makes them concretely computable and reproducible per repository, and re-runnable after any pipeline change (e.g. swapping the reranker) as a lightweight regression check.

---

## 7. Observability & Logging

All ingestion events, retrieval-stage outputs, generation turns, quality-validation results, and evaluation metrics are logged to Supabase — global and permanent (see Section 8 for why). This log is the raw material for:
- Per-stage latency tracking (download, chunk, embed, retrieve, rerank, generate).
- The Recall@5 / Precision@5 / MRR trend per repository over time.
- Debugging where the pipeline degrades (e.g. a spike in empty-retrieval responses signals a filtering or chunking regression).

---

## 8. Scope Trade-offs (Intentional, Not Oversights)

| Decision | Trade-off accepted |
|---|---|
| No authentication | Anyone can ingest/query any repo; no per-user data isolation. Acceptable for a single-user portfolio demo. |
| Session-based memory only | Conversation state doesn't persist across sessions/devices. |
| Global, permanent logs | Simplifies observability implementation, but means query/answer history isn't private per session. Explicitly flagged rather than silently ignored — a production version would scope and retention-limit these logs. |
| Free-tier, rate-limited LLM/embedding providers | Occasional latency/availability variance under load, mitigated by the 4-provider fallback chain. |

---

## 9. Data Model Summary (Supabase)

| Table | Purpose |
|---|---|
| `repos` | Ingested repo metadata, ingestion job status |
| `chunks` | Chunk content + embedding vector (HNSW index + full-text index) |
| `chunk_metadata` | symbol, symbol_type, class_name, parent_symbol, start_line, end_line, imports |
| `semantic_cache` | Cached query→answer pairs, scoped by `repo_id` |
| `eval_golden_set` | Synthetic Q&A pairs + ground-truth chunk reference (content-hash keyed) |
| `eval_results` | Recall@5 / Precision@5 / MRR per repo, per evaluation run |
| `logs` | Ingestion, retrieval, generation, and validation events with latency |

---

## 10. Tech Stack Summary

| Layer | Technology |
|---|---|
| Repo acquisition | Streamed HTTP download + `zipfile` |
| Filtering | `pathspec` (.gitignore), static rules, size/binary checks |
| Structural parsing | Tree-sitter |
| Chunk container | LangChain `Document` |
| Embeddings | Gemini embedding model (production), separate model (offline eval) |
| Vector + sparse store | Supabase / Postgres (`pgvector` HNSW + full-text search) |
| Fusion | Reciprocal Rank Fusion |
| Reranking | Cross-encoder |
| Generation | Gemini → Groq → Cerebras → OpenRouter (fallback chain) |
| Orchestration | LangChain |
| Storage / logging / metrics | Supabase (Postgres) |

---

## 11. Why This Design Stands Out

- **Structural over textual:** tree-sitter-based chunking with real symbol/parent metadata is a materially different (and harder) approach than splitting text on delimiters — it demonstrates actual code-intelligence thinking.
- **Defensible retrieval architecture:** dense+sparse hybrid retrieval with RRF and cross-encoder reranking is a well-established, explainable pattern — not an ad hoc combination.
- **Measurable, not just demoable:** an isolated offline evaluation loop with a real (if synthetic) ground truth makes Recall@5/Precision@5/MRR actual numbers you can quote, not aspirational metric names.
- **Cost- and constraint-aware engineering:** rate-limited multi-provider fallback, idempotent re-ingestion via content hashing, and an eval loop that never touches user-facing quota all show awareness of running against free-tier limits — a realistic constraint, handled deliberately.
