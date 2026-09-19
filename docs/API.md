# CodeAtlas REST & SSE API Reference 📡

Complete specification for the **CodeAtlas API**. The API provides repository ingestion, file browsing, hybrid code retrieval, and real-time streaming AI conversation endpoints.

---

## 🌐 General Information

- **Base URL**: `http://localhost:8000` (development) or configured production host.
- **Protocol**: HTTP/1.1 & HTTP/2
- **Default Content Type**: `application/json`
- **Streaming Content Type**: `text/event-stream` (Server-Sent Events)
- **CORS**: Configurable via `CODE_ATLAS_CORS_ORIGINS` (defaults to `http://localhost:5173`).

---

## 📌 Status Code Conventions

| Status Code | Meaning | Description |
| :--- | :--- | :--- |
| `200 OK` | Success | The request succeeded and returns the requested payload. |
| `202 Accepted` | Accepted | The repository ingestion task was queued/accepted for processing. |
| `400 Bad Request` | Client Error | The request payload violates syntax or structural constraints. |
| `404 Not Found` | Not Found | The requested resource (repository, session, file) does not exist. |
| `422 Unprocessable Entity` | Validation Error | Request parameters failed validation (e.g. invalid URL or missing fields). |
| `500 Internal Server Error` | Server Error | An unhandled exception occurred within the application. |
| `502 Bad Gateway` | Upstream Failure | Upstream AI provider or embedding service failed to respond. |
| `503 Service Unavailable` | Storage Degraded | Database or Supabase persistence is temporarily unavailable. |

---

## 📚 Endpoints Specification

---

### 1. Repository Management

#### `POST /api/repositories`
Registers a repository for background ingestion, chunking, and embedding.

- **Status Code**: `202 Accepted`
- **Request Body**:
  ```json
  {
    "mode": "url",
    "url": "https://github.com/facebook/react",
    "branch": "main"
  }
  ```
  *Alternative Manual Mode*:
  ```json
  {
    "mode": "manual",
    "username": "facebook",
    "name": "react",
    "branch": "main"
  }
  ```
- **Response Model (`Repository`)**:
  ```json
  {
    "id": "7a3556ee-5c21-4f01-948f-3765e998a4da",
    "name": "react",
    "full_name": "facebook/react",
    "description": "The library for web and native user interfaces.",
    "owner": "facebook",
    "branch": "main",
    "language": "JavaScript",
    "url": "https://github.com/facebook/react",
    "stats": {
      "files": 0,
      "folders": 0,
      "contributors": 0,
      "size_kb": 125000,
      "stars": 230000,
      "forks": 46000,
      "open_issues": 850,
      "open_pull_requests": 240
    },
    "contributors": [],
    "repository_metadata": {
      "visibility": "public",
      "languages": { "JavaScript": 0.85, "TypeScript": 0.15 },
      "topics": ["declarative", "frontend", "javascript", "react", "ui"],
      "license_name": "MIT"
    },
    "processing": {
      "chunks_created": null,
      "embeddings_generated": null,
      "duration_ms": null,
      "last_indexed_at": null
    },
    "metadata_ready": false,
    "files_ready": false,
    "status": "downloading",
    "error": null,
    "created_at": "2026-09-19T18:00:00.000000Z",
    "updated_at": "2026-09-19T18:00:01.000000Z"
  }
  ```

---

#### `GET /api/repositories`
Lists all registered repositories.

- **Status Code**: `200 OK`
- **Response**: `list[Repository]`

---

#### `GET /api/repositories/{repository_id}`
Retrieves details, ingestion status, and processing metrics for a specific repository.

- **Status Code**: `200 OK`
- **Path Parameters**:
  - `repository_id` (`UUID`, required): Unique repository identifier.
- **Response**: `Repository` object.

---

### 2. File Explorer & Source Code

#### `GET /api/repositories/{repository_id}/tree`
Returns the hierarchical directory and file tree of an ingested repository.

- **Status Code**: `200 OK`
- **Path Parameters**:
  - `repository_id` (`UUID`, required)
- **Response Model (`FileTreeResponse`)**:
  ```json
  {
    "tree": [
      {
        "name": "src",
        "path": "src",
        "type": "directory",
        "size": null,
        "children": [
          {
            "name": "App.tsx",
            "path": "src/App.tsx",
            "type": "file",
            "size": 1824,
            "children": null
          }
        ]
      },
      {
        "name": "package.json",
        "path": "package.json",
        "type": "file",
        "size": 540,
        "children": null
      }
    ]
  }
  ```

---

#### `GET /api/repositories/{repository_id}/files/{file_path}`
Retrieves raw file contents and metadata for source viewer rendering.

- **Status Code**: `200 OK`
- **Path Parameters**:
  - `repository_id` (`UUID`, required)
  - `file_path` (`string`, required, captures full relative path)
- **Response Model (`FileContentResponse`)**:
  ```json
  {
    "content": "import React from 'react';\n\nexport function App() { ... }",
    "language": "tsx",
    "size": 1824,
    "encoding": "utf-8"
  }
  ```

---

### 3. Hybrid Code Search & Retrieval

#### `POST /api/repositories/{repository_id}/retrieve`
Direct retrieval endpoint for testing hybrid dense/sparse search and cross-encoder reranking.

- **Status Code**: `200 OK`
- **Request Body**:
  ```json
  {
    "query": "Where is the authentication middleware implemented?"
  }
  ```
- **Response**:
  ```json
  {
    "cache_hit": false,
    "latency_ms": {
      "dense": 42.1,
      "sparse": 15.3,
      "rrf": 1.2,
      "rerank": 88.4,
      "total": 147.0
    },
    "results": [
      {
        "chunk_id": "c1f7b889-1033-4f9e-a612-4211de41209b",
        "repo_id": "7a3556ee-5c21-4f01-948f-3765e998a4da",
        "filepath": "src/middleware/auth.py",
        "language": "python",
        "symbol": "verify_token",
        "symbol_type": "function",
        "start_line": 24,
        "end_line": 48,
        "content": "async def verify_token(req: Request) -> User: ...",
        "reranker_score": 0.9412,
        "reranker_rank": 1
      }
    ]
  }
  ```

---

### 4. Conversational Chat & Streaming

#### `POST /api/chat/sessions`
Creates a new conversation session for a repository.

- **Query Parameters**:
  - `repositoryId` (`UUID`, required)
- **Response Model (`ChatSession`)**:
  ```json
  {
    "id": "e4a2d892-2b63-479c-bfa8-69255a5b1c92",
    "repository_id": "7a3556ee-5c21-4f01-948f-3765e998a4da",
    "created_at": "2026-09-19T18:10:00.000000Z",
    "updated_at": "2026-09-19T18:10:00.000000Z"
  }
  ```

---

#### `GET /api/chat/sessions`
Lists all active chat sessions for a repository.

- **Query Parameters**:
  - `repositoryId` (`UUID`, required)
- **Response**: `list[ChatSession]`

---

#### `GET /api/chat/sessions/{session_id}/messages`
Retrieves message history for a given session.

- **Path Parameters**:
  - `session_id` (`UUID`, required)
- **Response**: `list[ChatMessage]`

---

#### `POST /api/chat/sessions/{session_id}/messages/stream` 🔥
**Primary Real-Time Streaming Endpoint** utilizing Server-Sent Events (SSE).

- **Path Parameters**:
  - `session_id` (`UUID`, required)
- **Request Body**:
  ```json
  {
    "content": "How does the caching mechanism work in this project?"
  }
  ```
- **Response Headers**:
  ```http
  Content-Type: text/event-stream
  Cache-Control: no-cache
  Connection: keep-alive
  ```

- **SSE Stream Protocol**:
  1. **Token Event**: Emitted continuously as new tokens arrive from the LLM.
     ```
     data: {"type": "token", "content": "The "}
     data: {"type": "token", "content": "caching "}
     data: {"type": "token", "content": "system "}
     ```
  2. **Done Event**: Emitted upon completion with full message payload and validated citations.
     ```
     data: {"type": "done", "message": {"id": "uuid", "role": "assistant", "content": "...", "citations": [{"file": "src/cache.ts", "line_start": 12, "line_end": 45, "symbol": "MemoryCache"}], "created_at": "2026-09-19T18:12:00Z"}}
     ```
  3. **Error Event**: Emitted if generation fails upstream.
     ```
     data: {"type": "error", "error": "All generation providers failed."}
     ```

---

#### `DELETE /api/chat/sessions`
Deletes all chat sessions and messages associated with a repository.

- **Query Parameters**:
  - `repositoryId` (`UUID`, required)
- **Response**: `{"deleted": true}`

---

### 5. Health & Monitoring

#### `GET /health`
Liveness and health check endpoint.

- **Status Code**: `200 OK`
- **Response**: `{"status": "ok"}`
