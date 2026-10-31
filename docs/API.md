# API Reference

## 1. API Overview

The CodeAtlas backend provides a RESTful interface alongside real-time Server-Sent Events (SSE) streaming. It manages repository acquisition, tree exploration, grounded question answering, and conversational chat sessions.

---

## 2. Base URL

* **Local Development**: `http://localhost:8000/api`
* **Health Check**: `http://localhost:8000/health`
* **Interactive Documentation (Swagger UI)**: `http://localhost:8000/docs`
* **OpenAPI Specification**: `http://localhost:8000/openapi.json`

---

## 3. Authentication

The API currently operates in a single-tenant developer configuration. Ingestion and query endpoints do not require authorization headers from client callers. Backend interactions with third-party providers (GitHub, Supabase, Google Gemini) utilize server-side environment tokens.

---

## 4. Common Conventions

### 4.1 Request Format
All request bodies must use standard JSON (`Content-Type: application/json`).

### 4.2 Response Format
Standard responses return JSON. Streaming endpoints return Server-Sent Events (`Content-Type: text/event-stream`).

### 4.3 HTTP Status Codes
* `200 OK`: Request succeeded.
* `201 Created`: Resource successfully created.
* `202 Accepted`: Asynchronous task queued for processing.
* `204 No Content`: Action completed with no response body.
* `400 Bad Request`: Invalid parameters or malformed request.
* `404 Not Found`: Repository, file, or session does not exist.
* `409 Conflict`: Repository is currently undergoing ingestion.
* `422 Unprocessable Content`: Pydantic validation failure.
* `429 Too Many Requests`: Rate limit threshold exceeded.
* `500 Internal Server Error`: Unhandled server exception.

---

## 5. Endpoints

### 5.1 Health Check

#### GET `/health`
Returns the operational health and engine version.

* **Parameters**: None.
* **Success Response (200 OK)**:
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

---

### 5.2 Repository Management

#### POST `/api/repositories`
Queues a remote GitHub repository for multi-stage ingestion.

* **Parameters**: None.
* **Request Body**:
```json
{
  "repository_url": "https://github.com/pallets/flask",
  "branch": "main"
}
```
* **Success Response (202 Accepted)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "flask",
  "url": "https://github.com/pallets/flask",
  "status": "queued",
  "branch": "main",
  "files": 0,
  "folders": 0,
  "contributors": [],
  "processing": {
    "files_total": 0,
    "chunks_created": 0,
    "embeddings_generated": 0,
    "duration_ms": 0.0
  }
}
```
* **Errors**: `400 Bad Request`, `422 Unprocessable Content`.

#### GET `/api/repositories`
Lists all repositories currently tracked in the system.

* **Parameters**: None.
* **Success Response (200 OK)**:
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "flask",
    "url": "https://github.com/pallets/flask",
    "status": "ready",
    "primary_language": "Python",
    "stars": 67000,
    "forks": 15000
  }
]
```

---

### 5.3 Repository Information

#### GET `/api/repositories/{repository_id}`
Retrieves detailed status, contributor statistics, and processing metadata.

* **Parameters**:
  * `repository_id` (*path*, UUID, required): Repository ID.
* **Success Response (200 OK)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "flask",
  "url": "https://github.com/pallets/flask",
  "status": "ready",
  "owner": "pallets",
  "default_branch": "main",
  "primary_language": "Python",
  "files": 84,
  "folders": 12,
  "contributors": [
    {
      "username": "mitsuhiko",
      "commits": 1420,
      "contributions": 1420,
      "avatar_url": "https://avatars.githubusercontent.com/u/1?v=4"
    }
  ],
  "processing": {
    "files_total": 84,
    "chunks_created": 312,
    "embeddings_generated": 312,
    "duration_ms": 14250.5,
    "last_indexed_at": "2026-11-01T00:00:00Z"
  }
}
```
* **Errors**: `404 Not Found`.

---

### 5.4 File Operations

#### GET `/api/repositories/{repository_id}/tree`
Returns the complete nested directory and file tree for an indexed repository.

* **Parameters**:
  * `repository_id` (*path*, UUID, required): Repository ID.
* **Success Response (200 OK)**:
```json
{
  "tree": [
    {
      "name": "src",
      "path": "src",
      "type": "directory",
      "children": [
        {
          "name": "flask",
          "path": "src/flask",
          "type": "directory",
          "children": [
            {
              "name": "app.py",
              "path": "src/flask/app.py",
              "type": "file"
            }
          ]
        }
      ]
    },
    {
      "name": "README.md",
      "path": "README.md",
      "type": "file"
    }
  ]
}
```
* **Errors**: `404 Not Found`, `500 Internal Server Error`.

#### GET `/api/repositories/{repository_id}/files/{file_path}`
Fetches the raw text content and syntax language for a specific file.

* **Parameters**:
  * `repository_id` (*path*, UUID, required): Repository ID.
  * `file_path` (*path*, string, required): Relative path within the repository.
* **Success Response (200 OK)**:
```json
{
  "content": "class Flask:\n    def __init__(self, import_name):\n        self.import_name = import_name\n",
  "language": "python",
  "size": 78,
  "encoding": "utf-8"
}
```
* **Errors**: `404 Not Found`.

---

### 5.5 Chat and Query Operations

#### POST `/api/queries`
Executes an end-to-end question answering pipeline and returns a full response with validated citations.

* **Request Body**:
```json
{
  "repository_id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "Where is the Flask application class defined?",
  "options": {
    "top_k": 5,
    "use_cache": true,
    "similarity_threshold": 0.92
  }
}
```
* **Success Response (200 OK)**:
```json
{
  "answer": "The Flask application class is defined in `src/flask/app.py:100-150`.",
  "citations": [
    {
      "filepath": "src/flask/app.py",
      "start_line": 100,
      "end_line": 150,
      "symbol": "Flask",
      "confidence": 1.0,
      "snippet": "class Flask(Scaffold):"
    }
  ],
  "provider": "gemini",
  "model": "gemini-2.0-flash",
  "cache_hit": false,
  "latency_ms": 842.1,
  "retrieved_chunks_count": 5
}
```
* **Errors**: `404 Not Found`, `409 Conflict` (repository still indexing).

#### GET `/api/chat/sessions`
Lists conversation sessions for a repository.

* **Parameters**:
  * `repository_id` (*query*, string, optional): Scoped repository ID.
* **Success Response (200 OK)**:
```json
[
  {
    "id": "c1f71a9e-87a4-44b2-a4a3-5a02e6093d8b",
    "repository_id": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2026-11-01T01:00:00Z",
    "updated_at": "2026-11-01T01:05:00Z"
  }
]
```

#### POST `/api/chat/sessions`
Initializes a new persistent conversation session.

* **Request Body** *(Optional)*:
```json
{
  "repository_id": "550e8400-e29b-41d4-a716-446655440000"
}
```
* **Success Response (201 Created)**:
```json
{
  "id": "c1f71a9e-87a4-44b2-a4a3-5a02e6093d8b",
  "repository_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-11-01T01:00:00Z",
  "updated_at": "2026-11-01T01:00:00Z"
}
```

#### GET `/api/chat/sessions/{session_id}/messages`
Retrieves the historical conversation thread for a session.

* **Parameters**:
  * `session_id` (*path*, string, required): Session ID.
* **Success Response (200 OK)**:
```json
[
  {
    "id": "msg-01",
    "role": "user",
    "content": "Where is the Flask class?",
    "created_at": "2026-11-01T01:01:00Z"
  },
  {
    "id": "msg-02",
    "role": "assistant",
    "content": "The Flask class is located in src/flask/app.py [src/flask/app.py:100-150].",
    "citations": [
      {
        "filepath": "src/flask/app.py",
        "start_line": 100,
        "end_line": 150
      }
    ],
    "created_at": "2026-11-01T01:01:02Z"
  }
]
```

#### POST `/api/chat/stream`
Streams generated answers token-by-token via Server-Sent Events (SSE).

* **Request Body**:
```json
{
  "repository_id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "Explain the request context handling.",
  "session_id": "c1f71a9e-87a4-44b2-a4a3-5a02e6093d8b"
}
```
* **Success Response (200 OK, `text/event-stream`)**:
```
data: {"type": "token", "content": "The "}

data: {"type": "token", "content": "request "}

data: {"type": "token", "content": "context "}

data: {"type": "done", "message": {"id": "msg-03", "role": "assistant", "content": "The request context...", "citations": [{"filepath": "src/flask/ctx.py", "start_line": 50, "end_line": 80}]}}
```

#### DELETE `/api/chat/sessions`
Deletes all conversation sessions and associated messages for a repository.

* **Parameters**:
  * `repository_id` (*query*, string, required): Target repository.
* **Success Response (204 No Content)**.

---

## 6. Request and Response Examples

### Submitting a Question and Receiving Structured Citations
```bash
curl -X POST "http://localhost:8000/api/queries" \
     -H "Content-Type: application/json" \
     -d '{
       "repository_id": "550e8400-e29b-41d4-a716-446655440000",
       "query": "How is routing handled?",
       "options": {"top_k": 3}
     }'
```

---

## 7. Error Responses

Error payloads return standard JSON containing detail explanations:
```json
{
  "detail": "Repository '550e8400-e29b-41d4-a716-446655440000' is still indexing (status: chunking). Please wait."
}
```

---

## 8. Rate Limiting and Retry Behavior

* **Sliding Window Rate Limiter**: The backend implements an in-memory sliding window rate limiter (`SlidingWindowRateLimiter`) capping high-cost concurrent ingestion jobs.
* **Provider Retry**: The LLM client automatically retries transient HTTP 5xx errors and immediately falls over to secondary providers (Groq &rarr; Cerebras &rarr; OpenRouter) on HTTP 429 rate limit errors.

---

## 9. API Documentation Tools

* **Swagger UI**: Interactive playground accessible at `http://localhost:8000/docs`.
* **ReDoc**: Static API specification accessible at `http://localhost:8000/redoc`.
