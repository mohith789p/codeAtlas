# CodeAtlas - Developer Knowledge Platform

CodeAtlas is a developer knowledge platform designed for software repository analysis, semantic code search, AI-powered Retrieval-Augmented Generation (RAG) Q&A, and automated technical documentation generation using **FastAPI**, **PostgreSQL with pgvector**, **Gemini AI**, and **React + TypeScript**.

---

## 🏛️ System Architecture

CodeAtlas strictly adheres to **Clean Architecture** principles, maintaining clear separation between presentation, application workflows, domain models, and infrastructure layers.

```
Upload ZIP Repository
        ↓
Parser Service (File Extraction & Line Chunking)
        ↓
Embedding Service (Gemini text-embedding-004)
        ↓
PostgreSQL + pgvector Vector Storage (3072-dim embeddings)
        ↓
User Semantic Search / RAG Chat Query
        ↓
Vector Similarity Search (<=> Cosine Distance)
        ↓
Retrieved Code Snippets Context Prompt
        ↓
Gemini AI Engine (gemini-1.5-flash / gemini-2.5-flash)
        ↓
Grounded Architectural Explanation with Source Citations
```

---

## 🚀 Key Features

1. **User Authentication**: Secure JWT-based registration and token-based protected API routes.
2. **Repository Upload & Chunking**: Background tasks extract `.zip` repositories, filter binary files/dependencies, and parse source code into overlapping line chunks.
3. **Vector Embeddings**: Uses Gemini Embedding API (`gemini-embedding-001`) to convert code chunks into 3072-dimensional dense vectors.
4. **Vector Similarity Search**: Native PostgreSQL `pgvector` similarity calculation with Python fallback for SQLite environments.
5. **RAG Q&A Engine**: Question-answering assistant that injects **ONLY** retrieved relevant code snippets into Gemini prompts, preserving prompt privacy and preventing code hallucination.
6. **Documentation Generator**: One-click generation of comprehensive GitHub `README.md` files and Senior Architecture Specifications.
7. **Interactive Code Explorer**: Tree-structured repository navigation with line-numbered source code inspection.

---

## 🛠️ Technology Stack

- **Frontend**: React 18, Vite, TypeScript, TailwindCSS (Dark Glassmorphic UI), Axios, React Router.
- **Backend**: FastAPI, SQLAlchemy ORM, Pydantic v2, Python-Jose (JWT), BackgroundTasks.
- **Database**: PostgreSQL 16 with `pgvector` extension (with SQLite fallback).
- **Artificial Intelligence**: Gemini API (`gemini-1.5-flash` / `gemini-2.5-flash`) & Gemini Embedding API (`gemini-embedding-001`).

---

## 🚦 Quick Start with Docker Compose

### Prerequisites
- Docker Engine & Docker Compose
- Gemini API Key ([Get a key from Google AI Studio](https://aistudio.google.com/))

### 1. Configure Environment Variables
Copy `.env.example` to `.env` and insert your Gemini API Key:
```bash
cp .env.example .env
```
Edit `.env`:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

### 2. Launch Services
Run all services (Database with pgvector, FastAPI Backend, React Frontend):
```bash
docker-compose up --build -d
```

- **Frontend UI**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Swagger Documentation**: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

---

## 📁 Repository Structure

```
codeatlas/
├── ARCHITECTURE.md
├── docker-compose.yml
├── .env.example
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── core/          # Config, DB, Security, Gemini API client
│       ├── models/        # SQLAlchemy ORM Data Entities
│       ├── schemas/       # Pydantic Schemas
│       ├── services/      # Parser, Embedding, Retrieval, RAG services
│       └── api/           # FastAPI REST Router Endpoints
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    └── src/
        ├── components/    # Navbar, Sidebar, FileTree, CodeViewer, UploadModal
        ├── pages/         # Auth, Dashboard, Explorer, Chat, Docs
        ├── context/       # Auth & Repository State Contexts
        └── api/           # Axios HTTP Client
```
