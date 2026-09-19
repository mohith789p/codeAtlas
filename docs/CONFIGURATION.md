# CodeAtlas Configuration & Deployment Reference ⚙️

This document details all configuration options, environment variables, provider integrations, and deployment profiles for **CodeAtlas**.

---

## 🔑 Environment Variable Conventions

- All backend environment variables use the prefix **`CODE_ATLAS_`**.
- Variables can be provided via system environment variables, shell exports, or a `.env` file located in the root of the backend directory.
- Pydantic Settings parses types, defaults, and comma-separated lists automatically.

---

## 📋 Comprehensive Environment Variable Matrix

| Variable Name | Type | Default Value | Description |
| :--- | :---: | :---: | :--- |
| **`CODE_ATLAS_GEMINI_API_KEY`** | `string` | `None` | **Required**. Google Gemini API key for embeddings and generation. |
| `CODE_ATLAS_GEMINI_API_URL` | `string` | `https://generativelanguage.googleapis.com/v1beta` | Base URL for Google Generative Language API. |
| `CODE_ATLAS_GEMINI_EMBEDDING_MODEL` | `string` | `gemini-embedding-001` | Model used for 768-dimensional document and query embeddings. |
| `CODE_ATLAS_GEMINI_GENERATION_MODEL` | `string` | `gemini-2.5-flash` | Primary LLM model for code analysis and chat generation. |
| `CODE_ATLAS_GEMINI_SUMMARY_MODEL` | `string` | `gemini-2.5-flash-lite` | Compact model used by LangChain conversation memory summarization. |
| `CODE_ATLAS_EMBEDDING_DIMENSIONS` | `integer` | `768` | Vector dimensionality for embeddings and Postgres `pgvector` columns. |
| `CODE_ATLAS_EMBEDDING_BATCH_SIZE` | `integer` | `16` | Batch size for parallel vector embedding requests. |
| `CODE_ATLAS_GEMINI_EMBEDDING_RPM_LIMIT` | `integer` | `60` | Client-side rate limit (Requests Per Minute) for embedding calls. |
| `CODE_ATLAS_GEMINI_EMBEDDING_MAX_RETRIES` | `integer` | `5` | Maximum retry attempts for transient embedding network/quota errors. |
| `CODE_ATLAS_RERANKER_MODEL` | `string` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | HuggingFace CrossEncoder model for candidate semantic reranking. |
| **`CODE_ATLAS_SUPABASE_URL`** | `string` | `None` | *(Optional)* Supabase REST API URL (e.g. `https://xyz.supabase.co`). |
| **`CODE_ATLAS_SUPABASE_SERVICE_ROLE_KEY`**| `string` | `None` | *(Optional)* Supabase service role secret key. Enables durable storage. |
| `CODE_ATLAS_CORS_ORIGINS` | `string` | `http://localhost:5173` | Allowed CORS origins (comma-separated list for multiple hosts). |
| `CODE_ATLAS_GITHUB_API_URL` | `string` | `https://api.github.com` | GitHub REST API endpoint. |
| `CODE_ATLAS_MAX_REPOSITORY_SIZE_KB` | `integer` | `512000` (512 MB) | Maximum permitted repository download size. |
| `CODE_ATLAS_MAX_FILE_SIZE_BYTES` | `integer` | `1048576` (1 MB) | Maximum permitted size for individual indexed source files. |
| `CODE_ATLAS_DOWNLOAD_CONNECT_TIMEOUT_SECONDS` | `float` | `10.0` | Connection timeout for downloading remote repository archives. |
| `CODE_ATLAS_DOWNLOAD_READ_TIMEOUT_SECONDS` | `float` | `30.0` | Stream read timeout for downloading repository archives. |
| `CODE_ATLAS_MEMORY_CONTEXT_BUDGET` | `integer` | `2000` | Token budget limit for conversation summary buffer memory. |
| `CODE_ATLAS_EVALUATION_TARGET_COUNT` | `integer` | `100` | Target dataset size for automated golden evaluation generation. |
| `CODE_ATLAS_GROQ_API_KEY` | `string` | `None` | *(Optional)* API key for Groq fallback provider. |
| `CODE_ATLAS_GROQ_GENERATION_MODEL` | `string` | `llama-3.3-70b-versatile` | Model name for Groq LLM fallback. |
| `CODE_ATLAS_CEREBRAS_API_KEY` | `string` | `None` | *(Optional)* API key for Cerebras fallback provider. |
| `CODE_ATLAS_CEREBRAS_GENERATION_MODEL` | `string` | `llama-3.3-70b` | Model name for Cerebras LLM fallback. |
| `CODE_ATLAS_OPENROUTER_API_KEY` | `string` | `None` | *(Optional)* API key for OpenRouter universal fallback. |
| `CODE_ATLAS_OPENROUTER_GENERATION_MODEL` | `string` | `openai/gpt-4o-mini` | Model name for OpenRouter LLM fallback. |

---

## 🛠️ Configuration Profiles

### 1. Minimal Local Development (Zero Database Setup)
In this mode, CodeAtlas stores everything in memory. Perfect for rapid development and testing.

```ini
# backend/.env
CODE_ATLAS_GEMINI_API_KEY=your_gemini_api_key_here
CODE_ATLAS_CORS_ORIGINS=http://localhost:5173
```

---

### 2. Production Durable Storage (Supabase PostgreSQL + pgvector)
In this mode, repositories, chunk vectors, and chat history persist permanently in Supabase.

```ini
# backend/.env
CODE_ATLAS_GEMINI_API_KEY=your_gemini_api_key_here
CODE_ATLAS_SUPABASE_URL=https://your-project.supabase.co
CODE_ATLAS_SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key

# Fallback LLM Providers for High Reliability:
CODE_ATLAS_GROQ_API_KEY=gsk_your_groq_api_key
CODE_ATLAS_CEREBRAS_API_KEY=csk_your_cerebras_api_key
CODE_ATLAS_OPENROUTER_API_KEY=sk-or-your_openrouter_api_key
```

---

## 🗃️ Database Migrations Setup

When using Supabase, apply the SQL migrations in order located in `supabase/migrations/`:

```
1. supabase/migrations/0001_initial_schema.sql
   └── Creates base tables: repos, repository_files, chunks, chunk_metadata, logs, chat_sessions, chat_messages

2. supabase/migrations/0002_retrieval_schema.sql
   └── Configures pgvector extension and RPC functions: match_chunks, search_chunks, match_semantic_cache

3. supabase/migrations/0003_evaluation_schema.sql
   └── Creates evaluation tables: eval_golden_set, eval_results

4. supabase/migrations/0004_fix_semantic_cache_similarity.sql
   └── Updates semantic cache RPC with named parameters and strict similarity filtering
```
