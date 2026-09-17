# CodeAtlas — API Reference

CodeAtlas provides a RESTful HTTP API and Server-Sent Events (SSE) streaming protocol built on FastAPI. This document provides complete endpoint specifications, request/response schemas, streaming event definitions, and error codes.

---

## General Conventions

- **Base URL**: `http://localhost:8000` (or configured deployment host)
- **Frontend Proxy**: When running the Vite dev server, requests to `/api/*` are proxied to `http://localhost:8000/api/*`.
- **Request Bodies**: `application/json` (unless otherwise noted).
- **Responses**: `application/json` for standard endpoints; `text/event-stream` for chat streaming.
- **Identifiers**: Repository IDs and Session IDs are UUID strings.

---

## Endpoints Overview

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | [`/health`](#get-health) | System health check |
| `POST` | [`/api/repositories`](#post-apirepositories) | Submit a repository for asynchronous ingestion |
| `GET` | [`/api/repositories`](#get-apirepositories) | List all registered repositories |
| `GET` | [`/api/repositories/{id}`](#get-apirepositoriesid) | Get repository metadata, ingestion status, and statistics |
| `GET` | [`/api/repositories/{id}/tree`](#get-apirepositoriesidtree) | Get the recursive directory and file hierarchy |
| `GET` | [`/api/repositories/{id}/files/{path}`](#get-apirepositoriesidfilespath) | Read the decoded content of a specific source file |
| `POST` | [`/api/repositories/{id}/retrieve`](#post-apirepositoriesidretrieve) | Retrieve hybrid dense/sparse evidence chunks for a query |
| `GET` | [`/api/chat/sessions`](#get-apichatsessions) | List active chat sessions for a repository |
| `POST` | [`/api/chat/sessions`](#post-apichatsessions) | Create a new chat session |
| `DELETE` | [`/api/chat/sessions`](#delete-apichatsessions) | Purge all chat sessions for a repository |
| `GET` | [`/api/chat/sessions/{session_id}/messages`](#get-apichatsessionssession_idmessages) | Get conversation message history |
| `POST` | [`/api/chat/sessions/{session_id}/messages/stream`](#post-apichatsessionssession_idmessagesstream) | Send message & receive real-time streaming tokens via SSE |
| `POST` | [`/api/chat/sessions/{session_id}/messages`](#post-apichatsessionssession_idmessages-deprecated) | *(Deprecated)* Synchronous non-streaming chat generation |

---

## Repository Endpoints

### `GET /health`
Verifies backend service availability.

**Response `200 OK`**:
```json
{
  "status": "ok"
}
```

---

### `POST /api/repositories`
Registers and initiates asynchronous background ingestion for a public GitHub repository.

**Request Body (URL Mode)**:
```json
{
  "mode": "url",
  "url": "https://github.com/pallets/flask",
  "branch": "main"
}
```

**Request Body (Manual / Shorthand Mode)**:
```json
{
  "mode": "manual",
  "username": "pallets",
  "name": "flask",
  "branch": "main"
}
```

**Response `200 OK`**:
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "flask",
  "full_name": "pallets/flask",
  "url": "https://github.com/pallets/flask",
  "branch": "main",
  "status": "pending",
  "size_bytes": 0,
  "file_count": 0,
  "chunk_count": 0,
  "language": null,
  "repository_metadata": {},
  "contributors": [],
  "processing_status": {
    "clone": "pending",
    "filter": "pending",
    "chunk": "pending",
    "embed": "pending"
  },
  "metadata_ready": false,
  "files_ready": false,
  "created_at": "2026-09-18T00:00:00Z",
  "updated_at": "2026-09-18T00:00:00Z"
}
```

---

### `GET /api/repositories`
Returns all ingested or registered repositories.

**Response `200 OK`**:
```json
[
  {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "name": "flask",
    "full_name": "pallets/flask",
    "url": "https://github.com/pallets/flask",
    "branch": "main",
    "status": "ready",
    "size_bytes": 1048576,
    "file_count": 142,
    "chunk_count": 480,
    "language": "Python",
    "metadata_ready": true,
    "files_ready": true
  }
]
```

---

### `GET /api/repositories/{id}`
Returns the comprehensive details, ingestion lifecycle status, and statistics for a single repository.

**Parameters**:
- `id` (path, string): Unique repository UUID.

**Lifecycle Status Values (`status`)**:
- `pending`: Registered, awaiting background worker allocation.
- `cloning`: Downloading and extracting archive stream.
- `indexing`: Structural AST parsing, chunking, and vector embedding.
- `ready`: Ingestion complete; search, code viewer, and chat available.
- `failed`: Ingestion encountered a fatal error (e.g. repo size limit, network timeout).

**Response `200 OK`**:
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "flask",
  "full_name": "pallets/flask",
  "url": "https://github.com/pallets/flask",
  "branch": "main",
  "description": "The Python micro framework for building web applications.",
  "status": "ready",
  "size_bytes": 3524000,
  "file_count": 84,
  "chunk_count": 312,
  "language": "Python",
  "repository_metadata": {
    "languages": {
      "Python": 98.4,
      "HTML": 1.6
    },
    "topics": ["python", "web", "microframework", "flask"],
    "stars": 65000,
    "forks": 15000
  },
  "contributors": [
    {
      "name": "mitsuhiko",
      "contributions": 1200,
      "avatar_url": "https://avatars.githubusercontent.com/u/19?v=4"
    }
  ],
  "processing_status": {
    "clone": "completed",
    "filter": "completed",
    "chunk": "completed",
    "embed": "completed"
  },
  "metadata_ready": true,
  "files_ready": true
}
```

---

### `GET /api/repositories/{id}/tree`
Returns the hierarchical file and folder directory tree.

**Parameters**:
- `id` (path, string): Unique repository UUID.

**Response `200 OK`**:
```json
[
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
            "type": "file",
            "size": 65420
          }
        ]
      }
    ]
  },
  {
    "name": "README.md",
    "path": "README.md",
    "type": "file",
    "size": 4210
  }
]
```

---

### `GET /api/repositories/{id}/files/{path:path}`
Fetches the content and metadata of a specific file.

**Parameters**:
- `id` (path, string): Unique repository UUID.
- `path` (path, string): Relative repository path (e.g. `src/flask/app.py`).

**Response `200 OK`**:
```json
{
  "path": "src/flask/app.py",
  "size_bytes": 65420,
  "content": "import typing\nfrom .globals import current_app...",
  "language": "python"
}
```

---

### `POST /api/repositories/{id}/retrieve`
Direct retrieval endpoint executing dense vector search, sparse keyword search, Reciprocal Rank Fusion, and Cross-Encoder reranking.

**Parameters**:
- `id` (path, string): Unique repository UUID.

**Request Body**:
```json
{
  "query": "How is routing configured?",
  "top_k": 5
}
```

**Response `200 OK`**:
```json
{
  "query": "How is routing configured?",
  "results": [
    {
      "file_path": "src/flask/sansio/app.py",
      "start_line": 95,
      "end_line": 130,
      "content": "def add_url_rule(self, rule: str, endpoint: str | None = None...):",
      "score": 0.892,
      "metadata": {
        "symbols": ["add_url_rule"],
        "type": "function_definition"
      }
    }
  ]
}
```

---

## Chat & Streaming Endpoints

### `GET /api/chat/sessions`
Lists all chat sessions associated with a repository.

**Query Parameters**:
- `repositoryId` (query, string, required): Unique repository UUID.

**Response `200 OK`**:
```json
[
  {
    "id": "f5e4d3c2-b1a0-9876-fedc-ba0987654321",
    "repository_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "title": "Application routing questions",
    "created_at": "2026-09-18T00:05:00Z"
  }
]
```

---

### `POST /api/chat/sessions`
Initializes a new chat session for a repository.

**Request Body**:
```json
{
  "repository_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Response `200 OK`**:
```json
{
  "id": "f5e4d3c2-b1a0-9876-fedc-ba0987654321",
  "repository_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "title": "New Chat",
  "created_at": "2026-09-18T00:05:00Z"
}
```

---

### `DELETE /api/chat/sessions`
Deletes all chat sessions associated with a repository (used during Unlink flows).

**Query Parameters**:
- `repositoryId` (query, string, required): Unique repository UUID.

**Response `200 OK`**:
```json
{
  "deleted": 3
}
```

---

### `GET /api/chat/sessions/{session_id}/messages`
Retrieves chronological message history for a chat session.

**Parameters**:
- `session_id` (path, string): Unique session UUID.

**Response `200 OK`**:
```json
[
  {
    "id": "msg-001",
    "session_id": "f5e4d3c2-b1a0-9876-fedc-ba0987654321",
    "role": "user",
    "content": "Where is the main entry point defined?",
    "citations": [],
    "created_at": "2026-09-18T00:05:10Z"
  },
  {
    "id": "msg-002",
    "session_id": "f5e4d3c2-b1a0-9876-fedc-ba0987654321",
    "role": "assistant",
    "content": "The application entry point is instantiated in `app.py` [src/flask/app.py:12-40].",
    "citations": [
      {
        "file_path": "src/flask/app.py",
        "start_line": 12,
        "end_line": 40
      }
    ],
    "created_at": "2026-09-18T00:05:14Z"
  }
]
```

---

### `POST /api/chat/sessions/{session_id}/messages/stream`
Sends a user query and initiates real-time token streaming using Server-Sent Events (SSE).

**Parameters**:
- `session_id` (path, string): Unique session UUID.

**Headers**:
- `Accept: text/event-stream`
- `Content-Type: application/json`

**Request Body**:
```json
{
  "content": "How does the route decorator register URL endpoints?"
}
```

**SSE Stream Protocol (`text/event-stream`)**:

The endpoint emits continuous SSE data lines formatted as `data: <JSON>\n\n`.

1. **Token Event** (Emitted for each generated token chunk):
   ```text
   data: {"type": "token", "content": "The"}

   data: {"type": "token", "content": " route"}

   data: {"type": "token", "content": " decorator"}
   ```

2. **Done Event** (Emitted upon stream completion with the consolidated text and validated citations):
   ```text
   data: {"type": "done", "content": "The route decorator registers endpoints via `add_url_rule` [src/flask/app.py:80-110].", "citations": [{"file_path": "src/flask/app.py", "start_line": 80, "end_line": 110}]}
   ```

3. **Error Event** (Emitted if an exception occurs during stream generation):
   ```text
   data: {"type": "error", "content": "Unable to connect to generation provider."}
   ```

---

### `POST /api/chat/sessions/{session_id}/messages` *(Deprecated)*
*Legacy synchronous endpoint. Deprecated in favor of the streaming endpoint above, but preserved for backward compatibility and test coverage.*

**Request Body**:
```json
{
  "content": "Where is the router configured?"
}
```

**Response `200 OK`**:
```json
{
  "id": "msg-003",
  "session_id": "f5e4d3c2-b1a0-9876-fedc-ba0987654321",
  "role": "assistant",
  "content": "The router is configured in `app.py`...",
  "citations": [
    {
      "file_path": "src/flask/app.py",
      "start_line": 80,
      "end_line": 110
    }
  ],
  "created_at": "2026-09-18T00:06:00Z"
}
```

---

## Error Handling

Standard HTTP error responses adhere to the following schema:

```json
{
  "detail": "Descriptive error message"
}
```

| HTTP Status | Description | Typical Cause |
| --- | --- | --- |
| `400 Bad Request` | Invalid payload or unsupported repository format | Malformed URL or non-GitHub address |
| `404 Not Found` | Requested entity not found | Repository ID or file path does not exist |
| `422 Unprocessable Entity` | Schema validation error | Missing required fields or wrong data types |
| `500 Internal Server Error` | Unexpected backend failure | Uncaught exception (logged to server logs) |
| `503 Service Unavailable` | Upstream or persistence service offline | External LLM provider downtime or Supabase connection timeout |
