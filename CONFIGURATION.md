# CodeAtlas — Configuration Reference

This guide details all environment variables, runtime parameters, and setup profiles for **CodeAtlas**.

---

## Configuration Overview

- **Backend Settings**: Managed by Pydantic Settings in [`backend/app/config.py`](backend/app/config.py). All environment variables use the `CODE_ATLAS_` prefix and are loaded from `backend/.env`.
- **Frontend Settings**: Managed by Vite in `frontend/.env.local`. Variables use the `VITE_` prefix.

---

## Environment Setup Profiles

### Profile 1: Minimal Local Development (Zero Database)

For rapid local testing with zero database setup. Requires only Python, Node.js, and a Google Gemini API key:

```env
# backend/.env
CODE_ATLAS_GEMINI_API_KEY=AIzaSy...your-gemini-key
CODE_ATLAS_CORS_ORIGINS=http://localhost:5173
```

- **Persistence**: Uses the thread-safe `InMemoryStore`.
- **Retrieval**: Uses in-memory cosine similarity and token matching.
- **Generation**: Powered by Google Gemini (`gemini-2.5-flash`).

---

### Profile 2: Persistent Storage with Supabase & pgvector

For persistent storage of repositories, files, chunks, embeddings, and chat histories across server restarts:

```env
# backend/.env
CODE_ATLAS_GEMINI_API_KEY=AIzaSy...your-gemini-key

# Supabase Credentials
CODE_ATLAS_SUPABASE_URL=https://your-project.supabase.co
CODE_ATLAS_SUPABASE_SERVICE_ROLE_KEY=eyJh...your-service-role-key

# Client Origins
CODE_ATLAS_CORS_ORIGINS=http://localhost:5173
```

#### Applying Database Migrations
Before starting the backend, apply all 9 migrations sequentially in your Supabase SQL editor from [`backend/supabase/migrations/`](backend/supabase/migrations/):
1. `0001_initial_schema.sql` — Base tables, pgvector extension, chunks, and logs.
2. `0002_retrieval_schema.sql` — Retrieval index configurations and functions.
3. `0003_evaluation_schema.sql` — Evaluation tables for offline metrics.
4. `0004_fix_semantic_cache_similarity.sql` — Semantic cache distance tuning.
5. `0005_repository_idempotency.sql` — Repository idempotency constraints.
6. `0006_files_and_chat_persistence.sql` — Files, chat sessions, and message persistence.
7. `0007_contributor_details.sql` — Repository contributor metadata schema.
8. `0008_ingestion_readiness.sql` — Ingestion readiness boolean flags.
9. `0009_repository_metadata_and_processing.sql` — Granular step processing tracking.

---

### Profile 3: Multi-Provider LLM Fallback

To prevent service degradation during upstream rate limits or outages, configure secondary LLM providers:

```env
# backend/.env
CODE_ATLAS_GEMINI_API_KEY=AIzaSy...

# Secondary Fallback Providers (Optional)
CODE_ATLAS_GROQ_API_KEY=gsk_...
CODE_ATLAS_CEREBRAS_API_KEY=csk-...
CODE_ATLAS_OPENROUTER_API_KEY=sk-or-v1-...
```

The system queries providers in priority order:
1. **Gemini** (`gemini-2.5-flash`)
2. **Groq** (`llama-3.3-70b-versatile`)
3. **Cerebras** (`llama-3.3-70b`)
4. **OpenRouter** (`openai/gpt-4o-mini`)

---

## Backend Configuration Reference (`CODE_ATLAS_*`)

| Variable | Type | Default Value | Description |
| --- | --- | --- | --- |
| `CODE_ATLAS_GITHUB_API_URL` | `string` | `https://api.github.com` | Base URL for the GitHub REST API. |
| `CODE_ATLAS_MAX_REPOSITORY_SIZE_KB` | `integer` | `512000` (500 MB) | Maximum permitted archive download size. Repositories exceeding this are rejected at pre-flight. |
| `CODE_ATLAS_MAX_FILE_SIZE_BYTES` | `integer` | `1048576` (1 MB) | Maximum allowed size for individual source files during ingestion. |
| `CODE_ATLAS_DOWNLOAD_CHUNK_SIZE_BYTES` | `integer` | `1048576` (1 MB) | Stream buffer chunk size during tarball/zipball download. |
| `CODE_ATLAS_DOWNLOAD_CONNECT_TIMEOUT_SECONDS` | `float` | `10.0` | Connection timeout for GitHub archive streaming. |
| `CODE_ATLAS_DOWNLOAD_READ_TIMEOUT_SECONDS` | `float` | `30.0` | Read timeout per chunk during repository download. |
| `CODE_ATLAS_CORS_ORIGINS` | `string` | `http://localhost:5173` | Comma-delimited list of permitted CORS origins. |
| `CODE_ATLAS_SUPABASE_URL` | `string \| null` | `None` | Supabase project REST URL. If omitted, in-memory store is used. |
| `CODE_ATLAS_SUPABASE_SERVICE_ROLE_KEY` | `string \| null` | `None` | Supabase service-role key with permissions for vector operations. |
| `CODE_ATLAS_GEMINI_API_KEY` | `string \| null` | `None` | API key for Google Gemini embedding and generation services. |
| `CODE_ATLAS_GEMINI_API_URL` | `string` | `https://generativelanguage.googleapis.com/v1beta` | Base URL for Google Generative Language API. |
| `CODE_ATLAS_GEMINI_EMBEDDING_MODEL` | `string` | `gemini-embedding-001` | Model name for 768-dimensional text embeddings. |
| `CODE_ATLAS_GEMINI_GENERATION_MODEL` | `string` | `gemini-2.5-flash` | Primary chat generation model. |
| `CODE_ATLAS_GEMINI_SUMMARY_MODEL` | `string` | `gemini-2.5-flash-lite` | Model for summarizing long conversation histories. |
| `CODE_ATLAS_EMBEDDING_DIMENSIONS` | `integer` | `768` | Vector embedding dimension count. |
| `CODE_ATLAS_EMBEDDING_BATCH_SIZE` | `integer` | `16` | Number of chunks dispatched per embedding request. |
| `CODE_ATLAS_GEMINI_EMBEDDING_RPM_LIMIT` | `integer` | `60` | Client-side rate limiting requests-per-minute threshold. |
| `CODE_ATLAS_GEMINI_EMBEDDING_MAX_RETRIES` | `integer` | `5` | Maximum retry attempts for transient embedding failures. |
| `CODE_ATLAS_GEMINI_EMBEDDING_RETRY_BASE_SECONDS` | `float` | `1.0` | Base delay for exponential backoff retry. |
| `CODE_ATLAS_GEMINI_EMBEDDING_RETRY_MAX_SECONDS` | `float` | `60.0` | Maximum cap for exponential backoff delay. |
| `CODE_ATLAS_EMBEDDING_TIMEOUT_SECONDS` | `float` | `30.0` | HTTP client timeout for embedding operations. |
| `CODE_ATLAS_RERANKER_MODEL` | `string` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Hugging Face cross-encoder model used for candidate reranking. |
| `CODE_ATLAS_GROQ_API_URL` | `string` | `https://api.groq.com/openai/v1` | Base URL for Groq API. |
| `CODE_ATLAS_GROQ_API_KEY` | `string \| null` | `None` | Groq API key (fallback provider). |
| `CODE_ATLAS_GROQ_GENERATION_MODEL` | `string` | `llama-3.3-70b-versatile` | Model name for Groq inference. |
| `CODE_ATLAS_CEREBRAS_API_URL` | `string` | `https://api.cerebras.ai/v1` | Base URL for Cerebras API. |
| `CODE_ATLAS_CEREBRAS_API_KEY` | `string \| null` | `None` | Cerebras API key (fallback provider). |
| `CODE_ATLAS_CEREBRAS_GENERATION_MODEL` | `string` | `llama-3.3-70b` | Model name for Cerebras inference. |
| `CODE_ATLAS_OPENROUTER_API_URL` | `string` | `https://openrouter.ai/api/v1` | Base URL for OpenRouter API. |
| `CODE_ATLAS_OPENROUTER_API_KEY` | `string \| null` | `None` | OpenRouter API key (fallback provider). |
| `CODE_ATLAS_OPENROUTER_GENERATION_MODEL` | `string` | `openai/gpt-4o-mini` | Model name for OpenRouter inference. |
| `CODE_ATLAS_MEMORY_CONTEXT_BUDGET` | `integer` | `2000` | Token limit allocated for conversation history buffer. |
| `CODE_ATLAS_EVALUATION_EMBEDDING_MODEL` | `string` | `sentence-transformers/all-MiniLM-L-6-v2` | Local model used for offline similarity evaluation. |
| `CODE_ATLAS_EVALUATION_EMBEDDING_SIMILARITY_THRESHOLD` | `float` | `0.35` | Similarity threshold for offline evaluation matches. |
| `CODE_ATLAS_EVALUATION_TARGET_COUNT` | `integer` | `100` | Target sample count for automated evaluation runs. |

---

## Frontend Configuration Reference (`VITE_*`)

Frontend settings are loaded by Vite from `frontend/.env.local`:

| Variable | Default Value | Description |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `/api` | Base path for backend API calls. When left as `/api`, Vite dev server proxies requests to `http://localhost:8000`. Set to a full URL (e.g. `https://api.codeatlas.dev`) when backend is deployed separately. |

---

## Security Best Practices

- **Never commit `.env` or `.env.local`**: Both are explicitly excluded in `.gitignore`.
- **Use Service Role keys securely**: The Supabase service-role key bypasses Row-Level Security and must remain confined to the backend process.
- **Provider API Keys**: Rotate API keys immediately if unintentionally exposed.
