# CodeAtlas

CodeAtlas is an AI-powered codebase exploration and intelligence engine designed for public GitHub repositories. It indexes codebases through structural AST parsing, executes hybrid dense-sparse retrieval with cross-encoder reranking, and streams grounded answers with verified file and line citations.

[**Architecture & Pipeline**](ARCHITECTURE.md) &nbsp;&bull;&nbsp; [**API Reference**](API.md) &nbsp;&bull;&nbsp; [**Configuration Reference**](CONFIGURATION.md)

---

## Key Capabilities

- **Repository Ingestion**: Link public GitHub repositories via URL (`https://github.com/owner/repo`) or shorthand (`owner/repo`), optionally pinning a target branch. Ingestion streams repository tarballs directly via GitHub REST APIs without local `git clone` overhead.
- **Defensive File Filtering**: Respects `.gitignore` rules via `pathspec`, discards binary files via null-byte inspection, filters build/vendor directories (`node_modules`, `dist`, `build`, `vendor`, `.git`, `__pycache__`), rejects lockfiles, and enforces file size boundaries (1 MB default).
- **Structural AST Parsing**: Uses `tree-sitter-language-pack` to parse function definitions, classes, methods, and import hierarchies for 8 primary languages:
  - Python (`.py`)
  - JavaScript / JSX (`.js`, `.jsx`)
  - TypeScript / TSX (`.ts`, `.tsx`)
  - Go (`.go`)
  - Rust (`.rs`)
  - Java (`.java`)
  *Other supported text files (Markdown, JSON, YAML, etc.) fall back to line-bounded sliding window chunking.*
- **Hybrid Dense + Sparse Retrieval**: Combines semantic embeddings (Google Gemini 768-dimensional vectors) with lexical search (PostgreSQL full-text search or in-memory BM25 equivalents) using **Reciprocal Rank Fusion (RRF)**.
- **Cross-Encoder Reranking**: Re-scores top retrieved candidates using `cross-encoder/ms-marco-MiniLM-L-6-v2` to prioritize high-relevance evidence chunks before context insertion.
- **Multi-Provider Fallback Chain**: Queries LLMs in priority order across configured providers:
  1. Google Gemini (`gemini-2.5-flash` / `gemini-2.5-flash-lite`)
  2. Groq (`llama-3.3-70b-versatile`)
  3. Cerebras (`llama-3.3-70b`)
  4. OpenRouter (`openai/gpt-4o-mini`)
- **Real-Time Token Streaming**: Streams generated tokens to the client using Server-Sent Events (SSE) via `POST /api/chat/sessions/{session_id}/messages/stream`.
- **Strict Citation Validation**: Validates all generated file paths and line ranges against retrieved chunks. Halts or filters ungrounded citations before response finalization.
- **Dual Persistence Architecture**: Operates with zero external dependencies in **Pure In-Memory Mode** for local development, or persists durable data in **Supabase / PostgreSQL** with `pgvector` across 9 structured migrations.
- **Developer-Focused Dark UI**: Built with React 18 and Vite in an Obsidian/Slate neutral dark palette with restrained Violet brand accents:
  - **Overview Dashboard**: Live ingestion step tracking, repository scale metrics, language distribution, and contributor breakdown.
  - **Code Viewer**: File tree navigation, syntax highlighting via `highlight.js`, and fixed-width gutter line numbers with aligned code streams.
  - **Streaming Chat**: Real-time token streaming with Markdown and syntax highlighting, citation tags, and conversation memory.
  - **Client-Side Cache Layer**: In-memory caching (`DashboardCache`) guarantees instant, zero-latency transitions between Overview, Files, and Chat tabs without refetching.
  - **Link & Unlink Workflows**: Dedicated Unlink controls in the Overview header and pinned to the bottom of the navigation sidebar.

---

## Architecture & Data Flow

> For full architectural flowcharts, sequence diagrams, and mathematical pipeline specifications (RRF, cross-encoders, and citation validation), see [**ARCHITECTURE.md**](ARCHITECTURE.md).

```
                           ┌───────────────────────────────┐
                           │    React 18 + Vite Frontend   │
                           │   (Obsidian / Slate / Violet) │
                           └───────────────┬───────────────┘
                                           │ HTTP / SSE
                                           ▼
                           ┌───────────────────────────────┐
                           │        FastAPI Backend        │
                           └───────┬───────────────┬───────┘
                                   │               │
            ┌──────────────────────┘               └──────────────────────┐
            ▼                                                             ▼
┌───────────────────────┐                                     ┌───────────────────────┐
│   Ingestion Pipeline  │                                     │  Chat & Generation    │
├───────────────────────┤                                     ├───────────────────────┤
│ 1. GitHub API Stream  │                                     │ 1. Session Memory     │
│ 2. .gitignore & Binary│                                     │ 2. Dense Vector Search│
│ 3. Tree-sitter AST    │                                     │ 3. Sparse Lexical     │
│ 4. Gemini Embeddings  │                                     │ 4. Reciprocal Rank    │
│ 5. Content-Hash Index │                                     │ 5. Cross-Encoder Rank │
└───────────┬───────────┘                                     │ 6. Provider Chain     │
            │                                                 │ 7. Citation Check     │
            ▼                                                 │ 8. SSE Token Stream   │
┌───────────────────────────────────────────┐                 └───────────┬───────────┘
│            Storage Layer                  │                             │
│  - Supabase (PostgreSQL + pgvector)       │◀────────────────────────────┘
│    OR In-Memory Thread-Safe Store         │
└───────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technologies |
| --- | --- |
| **Backend** | Python 3.12+, FastAPI, Uvicorn, Pydantic Settings, HTTPX, Pathspec |
| **Parsing & Chunking** | `tree-sitter-language-pack`, LangChain Core |
| **Embeddings & Search** | Google Gemini (`gemini-embedding-001`, 768d), Sentence-Transformers, Cross-Encoders (`ms-marco-MiniLM-L-6-v2`), PostgreSQL Full-Text Search / pgvector |
| **LLM Inference** | Google Gemini, Groq, Cerebras, OpenRouter (OpenAI-compatible) |
| **Database & Persistence** | Supabase (PostgreSQL 15+ with `vector` extension) or thread-safe `InMemoryStore` |
| **Frontend** | React 18, TypeScript, Vite, React Router v6, Lucide React, Highlight.js, React Markdown, Remark GFM |

---

## Project Structure

```text
codeatlas/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI application & HTTP/SSE route handlers
│   │   ├── config.py                   # Pydantic BaseSettings environment configuration
│   │   ├── store.py                    # Thread-safe in-memory store for zero-DB dev
│   │   ├── persistence.py              # Supabase / PostgreSQL persistence adapter
│   │   ├── schemas.py                  # Pydantic request/response models
│   │   └── services/
│   │       ├── chunking.py             # Tree-sitter AST parsers & fallback chunker
│   │       ├── embeddings.py           # Gemini embedding client with exponential retry
│   │       ├── filtering.py            # .gitignore rules, binary checks, file bounds
│   │       ├── generation.py           # LLM provider chain & SSE streaming generator
│   │       ├── github.py               # GitHub REST API client & archive downloader
│   │       ├── ingestion.py            # End-to-end background ingestion coordinator
│   │       ├── memory.py               # ConversationSummaryBufferMemory management
│   │       ├── retrieval.py            # Dense + sparse hybrid retrieval with RRF
│   │       └── validation.py           # Citation boundaries & grounding validator
│   ├── supabase/
│   │   └── migrations/                 # Ordered PostgreSQL/pgvector migrations (0001 - 0009)
│   ├── tests/                          # Automated test suite (Pytest + Asyncio)
│   ├── pyproject.toml                  # Backend project metadata & dependencies
│   └── .env.example                    # Backend environment template
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.ts               # Base HTTP client with error handling
│   │   │   ├── repositories.ts         # Repository API methods & schemas
│   │   │   ├── chat.ts                 # Chat sessions & SSE message stream consumer
│   │   │   └── cache.ts                # In-memory dashboard cache for instant tab routing
│   │   ├── components/
│   │   │   ├── common/                 # Reusable Button, Input, Spinner, States
│   │   │   └── layout/                 # DashboardShell, Sidebar, Header
│   │   ├── pages/
│   │   │   ├── HomePage.tsx            # Repository linking entry point
│   │   │   └── dashboard/
│   │   │       ├── OverviewPage.tsx    # Metrics, languages, contributors & status
│   │   │       ├── FilesPage.tsx       # Interactive file tree & line-aligned code viewer
│   │   │       └── ChatPage.tsx        # SSE streaming chat with citation badges
│   │   ├── tokens.css                  # Obsidian/Slate design tokens & color palette
│   │   └── App.tsx                     # React Router application entry
│   ├── package.json                    # Frontend dependencies & build scripts
│   ├── vite.config.ts                  # Vite server & backend API proxy configuration
│   └── .env.example                    # Frontend environment template
└── README.md
```

---

## Getting Started

### Prerequisites

- **Python**: Version 3.12 or higher
- **Node.js**: Version 18 or higher (with npm)
- **API Keys**: At least one LLM key (e.g. `CODE_ATLAS_GEMINI_API_KEY` for embeddings and generation).

---

### Step 1: Environment Configuration

From the project root:

```bash
# Windows (PowerShell)
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env.local

# macOS / Linux
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

Edit `backend/.env` to configure your API keys:
- Set `CODE_ATLAS_GEMINI_API_KEY` (required for embeddings; also enables default generation).
- *(Optional)* Add `CODE_ATLAS_GROQ_API_KEY`, `CODE_ATLAS_CEREBRAS_API_KEY`, or `CODE_ATLAS_OPENROUTER_API_KEY` for fallback generation.
- *(Optional)* Set `CODE_ATLAS_SUPABASE_URL` and `CODE_ATLAS_SUPABASE_SERVICE_ROLE_KEY` if using persistent database storage.

---

### Step 2: Set Up and Run the Backend

```bash
cd backend

# Create and activate a virtual environment
# Windows:
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# macOS / Linux:
# python3 -m venv .venv
# source .venv/bin/activate

# Install dependencies in editable mode with test extras
pip install -e ".[test]"

# Run FastAPI with live reload
uvicorn app.main:app --reload --port 8000
```

The backend starts at `http://localhost:8000`. Verify with `curl http://localhost:8000/health`.

---

### Step 3: Set Up and Run the Frontend

In a separate terminal:

```bash
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

The dashboard opens at `http://localhost:5173`. Requests made to `/api/*` are automatically proxied to `http://localhost:8000`.

---

### (Optional) Database Setup with Supabase

If durable PostgreSQL persistence is needed:
1. Create a project on [Supabase](https://supabase.com).
2. Enable the `vector` extension in the PostgreSQL database.
3. Apply the migrations in sequential order from `backend/supabase/migrations/`:
   - `0001_initial_schema.sql`
   - `0002_retrieval_schema.sql`
   - `0003_evaluation_schema.sql`
   - `0004_fix_semantic_cache_similarity.sql`
   - `0005_repository_idempotency.sql`
   - `0006_files_and_chat_persistence.sql`
   - `0007_contributor_details.sql`
   - `0008_ingestion_readiness.sql`
   - `0009_repository_metadata_and_processing.sql`
4. Set `CODE_ATLAS_SUPABASE_URL` and `CODE_ATLAS_SUPABASE_SERVICE_ROLE_KEY` in `backend/.env`.

---

## Configuration & Environment Variables

CodeAtlas uses environment variables with the `CODE_ATLAS_` prefix for the backend and `VITE_` for the frontend.

For setup profiles (Minimal Local In-Memory, Supabase Persistence, Multi-Provider LLM Fallback) and the complete variable reference table, see [**CONFIGURATION.md**](CONFIGURATION.md).

---

## API & Streaming Reference

CodeAtlas exposes RESTful endpoints for repository lifecycle management and Server-Sent Events (SSE) for real-time token streaming chat.

For complete endpoint specifications, request/response schemas, SSE event protocols, and error codes, see [**API.md**](API.md).

| Area | Key Endpoints | Documentation |
| --- | --- | --- |
| **System** | `GET /health` | [System Health](API.md#get-health) |
| **Repositories** | `POST /api/repositories`, `GET /api/repositories/{id}`, `GET /tree`, `GET /files/{path}` | [Repository Endpoints](API.md#repository-endpoints) |
| **Retrieval** | `POST /api/repositories/{id}/retrieve` | [Retrieval & Rerank](API.md#post-apirepositoriesidretrieve) |
| **Chat & Streaming** | `GET/POST/DELETE /api/chat/sessions`, `POST /messages/stream` | [Chat & Streaming](API.md#chat--streaming-endpoints) |

---

## Verification & Testing

### Backend Tests

Backend tests use `pytest` with `asyncio`. By default, tests exclude external live API calls:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q -m "not live"
```
*Current status: **82 passed**, 0 failures.*

To run opt-in live tests against real providers:
```powershell
.\.venv\Scripts\python.exe -m pytest -q -m "live"
```

### Frontend Checks

```powershell
cd frontend
# Run TypeScript compilation check
npm run type-check

# Run production Vite bundle build
npm run build
```
*Current status: **0 TypeScript errors**, production bundle builds cleanly.*

---

## Technical Boundaries & Honest Limitations

To maintain strict truthfulness without unsupported claims:

1. **Public Repositories Only**: GitHub personal access tokens or OAuth authentications are not implemented; private repositories are not supported.
2. **In-Process Background Ingestion**: Ingestion tasks run as FastAPI in-process background tasks (`BackgroundTasks`), not via a distributed queue (such as Celery, Temporal, or Redis). Server restarts during ingestion require re-linking the repository.
3. **In-Memory Volatility**: When running without Supabase, all indexed chunks, file trees, and chat sessions are stored in `InMemoryStore` and will be discarded when the backend process exits.
4. **Targeted AST Grammar Support**: Tree-sitter structural extraction is implemented for the 8 supported languages listed above. All other file types (e.g. C, C++, Elixir, Shell, HTML, CSS) use sliding-window line/token chunking.
5. **Single-User Architecture**: The frontend does not implement user accounts, authentication guards, or multi-tenant permission boundaries.
