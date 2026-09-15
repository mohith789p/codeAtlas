# Code Atlas

Code Atlas lets you explore a public GitHub repository and ask grounded questions about its code with file and line citations.

## Overview

Code Atlas ingests a public GitHub repository, makes its source files searchable, and provides a web dashboard for repository metadata, files, retrieval, and code-focused chat. Answers are generated from retrieved repository evidence and validated citations.

## Features

- Ingest a public GitHub repository by URL or owner/name.
- Track ingestion status and view repository metadata, contributors, and statistics.
- Browse the ingested file tree and file contents.
- Search code with dense and sparse retrieval, semantic-cache support, and cross-encoder reranking.
- Ask questions in chat and receive grounded Markdown answers with file and line citations.
- Store repositories, indexed chunks, files, logs, sessions, and messages in Supabase when configured.
- Use Gemini, Groq, Cerebras, or OpenRouter for generation, with configured providers tried in fallback order.

## How It Works

```text
GitHub Repository
       ↓
Metadata + Archive Download
       ↓
File Filtering and Parsing
       ↓
Code Chunking
       ↓
Gemini Embeddings and Content-Hash Indexing
       ↓
Dense + Sparse Retrieval
       ↓
Reciprocal Rank Fusion and Cross-Encoder Reranking
       ↓
LLM Generation
       ↓
Grounded Answer with File/Line Citations
```

Supported source files are parsed structurally with Tree-sitter. Other retained text files use fallback chunks. Retrieval uses PostgreSQL vector and full-text search with Supabase, or in-memory equivalents when Supabase is not configured.

## Architecture

```text
                         ┌──────────────────────┐
                         │     React / Vite      │
                         │     Web Dashboard     │
                         └──────────┬───────────┘
                                    │ HTTP / JSON
                                    ▼
                         ┌──────────────────────┐
                         │    FastAPI Backend    │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
       ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
       │ GitHub API   │      │  Ingestion   │      │ Chat and     │
       │ + Archives   │      │  Pipeline    │      │ Generation   │
       └──────────────┘      └──────┬───────┘      └──────┬───────┘
                                    │                     │
                                    ▼                     ▼
                           ┌────────────────┐      ┌───────────────┐
                           │ Filtering,      │      │ Retrieval      │
                           │ Parsing, and    │─────▶│ and Reranking  │
                           │ Chunking        │      └───────┬───────┘
                           └───────┬────────┘              │
                                   ▼                       ▼
                           ┌────────────────┐      ┌───────────────┐
                           │ Gemini          │      │ Provider Chain │
                           │ Embeddings and  │      │ + Citation     │
                           │ Indexing        │      │ Validation     │
                           └───────┬────────┘      └───────────────┘
                                   │
                                   ▼
                         ┌────────────────────────┐
                         │ Supabase/PostgreSQL    │
                         │ + pgvector (optional)  │
                         └────────────────────────┘
```

Without Supabase, the backend uses its in-memory store for local development.

## Tech Stack

- **Backend:** Python 3.12+, FastAPI, Uvicorn, Pydantic Settings, HTTPX
- **Frontend:** React, TypeScript, Vite, React Router
- **AI / Retrieval:** LangChain, Tree-sitter, Gemini embeddings, Sentence Transformers, PostgreSQL full-text search, reciprocal rank fusion, Hugging Face cross-encoder reranking
- **Storage:** In-memory store, or Supabase/PostgreSQL with pgvector

## Project Structure

```text
backend/
  app/                    FastAPI application and backend services
  supabase/migrations/    Ordered PostgreSQL/pgvector migrations
  tests/                  Unit and opt-in live tests
  .env.example            Backend environment template
frontend/
  src/                    React pages, components, and API clients
  .env.example            Frontend environment template
```

## Getting Started

### 1. Configure environment files

From the repository root:

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env.local
```

Set `CODE_ATLAS_GEMINI_API_KEY` and at least one generation-provider key in `backend/.env`. Supabase settings are optional for local in-memory development. For durable persistence, configure both Supabase variables and apply `backend/supabase/migrations/0001_initial_schema.sql` through `0009_repository_metadata_and_processing.sql` in order.

### 2. Install and start the backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
uvicorn app.main:app --reload
```

The backend runs at `http://localhost:8000`.

### 3. Install and start the frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173` and proxies `/api` to the local backend. `VITE_API_BASE_URL` can point to another backend when the services are deployed separately.

## Environment Variables

Backend settings use the `CODE_ATLAS_` prefix and are documented in [backend/.env.example](backend/.env.example). They cover GitHub access and limits, Supabase persistence, Gemini embeddings, retrieval and evaluation models, generation providers, and conversation-memory limits.

The frontend uses `VITE_API_BASE_URL`, documented in [frontend/.env.example](frontend/.env.example). The local default is `/api`.

The example files contain no credentials. Keep real `.env` files and provider keys out of Git.

## API

Main backend routes:

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Health check |
| `POST` | `/api/repositories` | Register and ingest a repository |
| `GET` | `/api/repositories` | List repositories |
| `GET` | `/api/repositories/{id}` | Read repository status and metadata |
| `GET` | `/api/repositories/{id}/tree` | Read the ingested file tree |
| `GET` | `/api/repositories/{id}/files/{path}` | Read an ingested file |
| `POST` | `/api/repositories/{id}/retrieve` | Retrieve ranked evidence for a query |
| `GET/POST` | `/api/chat/sessions` | List or create sessions using `repositoryId` |
| `GET/POST` | `/api/chat/sessions/{session_id}/messages` | Read or send chat messages |
| `DELETE` | `/api/chat/sessions` | Delete sessions using `repositoryId` |

## Limitations

- Only public GitHub repositories are supported; GitHub authentication is not implemented.
- Ingestion runs as an in-process FastAPI background task, not a durable job queue.
- Without Supabase, application data is lost when the backend process stops.
- Chat requires indexed repository data, a working embedding provider, and at least one configured generation provider.
- Structural parsing supports Python, JavaScript, JSX, TypeScript, TSX, Go, Rust, and Java; other retained text uses fallback chunks.
- The frontend has no authentication or user-account layer.

## Development

Backend tests default to non-live tests:

```powershell
cd backend
python -m pytest -q -m "not live"
```

Frontend checks:

```powershell
cd frontend
npm run type-check
npm run build
```

Live tests are marked `live` and require the external services described by each test.
