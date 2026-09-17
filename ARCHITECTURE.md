# CodeAtlas — System Architecture & Technical Pipelines

This document provides a comprehensive technical breakdown of the **CodeAtlas** architecture, detailing data flow, algorithmic design, sequence diagrams, and pipeline specifications across ingestion, hybrid retrieval, streaming generation, citation validation, and frontend caching.

---

## 1. High-Level System Architecture

CodeAtlas is decoupled into a modern **React 18 + Vite** frontend and an asynchronous **FastAPI** backend with a pluggable storage layer (PostgreSQL + `pgvector` via Supabase, or a zero-dependency thread-safe in-memory store).

```mermaid
flowchart TB
    subgraph Client["Frontend Layer (Client Browser)"]
        UI["React 18 Dashboard<br/>(Obsidian / Slate / Violet)"]
        Cache["In-Memory Client Cache<br/>(DashboardCache)"]
        UI <--> Cache
    end

    subgraph API_Gateway["Backend API & Application Gateway"]
        FastAPI["FastAPI App (app/main.py)"]
        CORS["CORS & Error Handlers"]
        BG["In-Process BackgroundTasks"]
        FastAPI --- CORS
        FastAPI --> BG
    end

    subgraph Core_Services["Core Service Layer"]
        IngestSvc["Ingestion Coordinator<br/>(ingestion.py)"]
        FilterSvc["Defensive Filter<br/>(filtering.py)"]
        ChunkSvc["AST Tree-sitter Chunker<br/>(chunking.py)"]
        EmbedSvc["Gemini Embeddings<br/>(embeddings.py)"]
        RetSvc["Hybrid Retriever (RRF)<br/>(retrieval.py)"]
        RerankSvc["Cross-Encoder Reranker<br/>(ms-marco-MiniLM-L-6-v2)"]
        GenSvc["Generation & SSE Stream<br/>(generation.py)"]
        MemSvc["Conversation Memory<br/>(memory.py)"]
        ValSvc["Citation Validator<br/>(validation.py)"]
    end

    subgraph External_Services["External Services & APIs"]
        GitHub["GitHub REST API & Tarballs"]
        Gemini["Google Gemini API<br/>(Embedding + Flash)"]
        Groq["Groq API (LLaMA 3.3 70B)"]
        Cerebras["Cerebras API (LLaMA 3.3 70B)"]
        OpenRouter["OpenRouter (GPT-4o-mini)"]
    end

    subgraph Persistence_Layer["Storage & State Layer"]
        choice{"CODE_ATLAS_SUPABASE_URL<br/>configured?"}
        DB[("Supabase (PostgreSQL 15+)<br/>pgvector + Full-Text")]
        MemStore[("InMemoryStore<br/>(Thread-safe Dicts & Cosine)")]
    end

    UI <-- "HTTP REST & SSE Stream" --> FastAPI
    BG --> IngestSvc
    IngestSvc --> GitHub
    IngestSvc --> FilterSvc --> ChunkSvc --> EmbedSvc --> choice
    FastAPI --> RetSvc --> RerankSvc --> GenSvc
    GenSvc --> MemSvc
    GenSvc --> ValSvc
    GenSvc --> Gemini & Groq & Cerebras & OpenRouter
    EmbedSvc --> Gemini
    choice -- "Yes" --> DB
    choice -- "No" --> MemStore
```

---

## 2. Ingestion Pipeline

The ingestion pipeline runs asynchronously in the background so that repository registration (`POST /api/repositories`) returns immediately with status `pending`.

### 2.1 Ingestion Flowchart

```mermaid
flowchart TD
    A["User triggers Link Repository<br/>(URL or username/repo)"] --> B["Create Repository Record<br/>Status: pending"]
    B --> C["Dispatch FastAPI BackgroundTask"]
    C --> D["Fetch Metadata from GitHub API<br/>(/repos/{owner}/{repo})"]
    D --> E{"Repository Size <= 500MB?<br/>(CODE_ATLAS_MAX_REPOSITORY_SIZE_KB)"}
    E -- "No" --> F["Mark status: failed<br/>Log: Exceeds max repository size"]
    E -- "Yes" --> G["Stream Download Archive<br/>(tar.gz / zip in 1MB chunks)"]
    G --> H["Extract Archive to Temp Dir<br/>Status: cloning"]
    H --> I["Layered Defensive Filtering"]

    subgraph Filtering["Filtering Sequence (Cheapest First)"]
        I --> I1["1. Parse .gitignore with pathspec"]
        I1 --> I2["2. Exclude static dirs (.git, node_modules, dist, etc.)"]
        I2 --> I3["3. Exclude static files (lockfiles, etc.)"]
        I3 --> I4["4. Discard files > 1MB"]
        I4 --> I5["5. Reject binary files (null-byte check)"]
        I5 --> I6["6. Multi-encoding decode (utf-8, cp1252, etc.)"]
    end

    I6 --> J["Save Clean Retained Files<br/>(files table / store)"]
    J --> K["Structural AST Parsing & Chunking<br/>Status: indexing"]

    subgraph Parsing["Tree-sitter AST & Fallback Chunking"]
        K --> K1{"File Extension in<br/>[.py, .js, .jsx, .ts, .tsx, .go, .rs, .java]?"}
        K1 -- "Yes" --> K2["Tree-sitter Language Pack Parse<br/>- Function definitions<br/>- Classes & Structs<br/>- Methods & Declarations<br/>- Imports extracted into metadata"]
        K1 -- "No" --> K3["Sliding-Window Fallback Chunker<br/>- 500-token chunks with 50-token overlap<br/>- Clean line boundaries"]
    end

    K2 --> L["Compute SHA-256 Content Hash per Chunk"]
    K3 --> L
    L --> M["Batch Gemini Embeddings (768d)<br/>- Batch size: 16<br/>- Rate limit: 60 RPM<br/>- Exponential backoff (1s - 60s)"]
    M --> N["Deduplicate & Persist Chunks<br/>(chunks table / store)"]
    N --> O["Mark status: ready<br/>Update processing step counts & ready flags"]
```

### 2.2 Layered Defensive Filtering Details

| Stage | Mechanism | Rationale |
| --- | --- | --- |
| **1. Dynamic Gitignore** | `pathspec.PathSpec` on repository `.gitignore` | Prevents ingestion of developer-ignored artifacts and logs |
| **2. Static Directory Pruning** | Checks path components against `{".git", "node_modules", "vendor", "dist", "build", "coverage", "__pycache__"}` | Eliminates third-party libraries and build outputs before parsing |
| **3. Static File Filtering** | Excludes `{".gitignore", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "composer.lock"}` | Removes noise and massive configuration files |
| **4. File Size Boundary** | Skips files where `st_size > 1_048_576` bytes | Prevents memory exhaustion from large generated bundles or data dumps |
| **5. Binary Detection** | Scans for null bytes (`b"\x00"` in raw bytes) | Accurately rejects compiled binaries, images, objects, and compressed blobs |
| **6. Multi-Encoding Decoding** | Sequential attempts: `utf-8` → `utf-8-sig` → `cp1252` → `latin-1` → fallback replace | Guarantees lossless text ingestion without crashing on Windows or legacy encodings |

---

## 3. Hybrid Retrieval & Reranking Pipeline

To achieve high recall and precision, CodeAtlas combines dense vector search with sparse keyword search and cross-encoder reranking.

```mermaid
sequenceDiagram
    autonumber
    actor User as User Chat
    participant ChatAPI as FastAPI (/api/repositories/{id}/retrieve)
    participant EmbedSvc as Gemini Embeddings
    participant DenseRet as Dense Vector Retriever
    participant SparseRet as Sparse Lexical Retriever
    participant RRF as Reciprocal Rank Fusion
    participant Reranker as Cross-Encoder Reranker

    User->>ChatAPI: POST query: "How is authentication handled?"
    ChatAPI->>EmbedSvc: Embed query (gemini-embedding-001, 768d)
    EmbedSvc-->>ChatAPI: query_vector

    par Dense Retrieval
        ChatAPI->>DenseRet: Vector Search (cosine similarity / pgvector <=> operator)
        DenseRet-->>ChatAPI: Top 20 dense candidates
    and Sparse Retrieval
        ChatAPI->>SparseRet: Full-Text Search (tsvector / BM25 token match)
        SparseRet-->>ChatAPI: Top 20 sparse candidates
    end

    ChatAPI->>RRF: Fuse candidates via RRF formula: RRF(d) = sum(1 / (k + rank))
    RRF-->>ChatAPI: Combined ranked list (Top 15 candidates)

    ChatAPI->>Reranker: Score candidates with cross-encoder/ms-marco-MiniLM-L-6-v2
    Reranker-->>ChatAPI: Re-scored & sorted evidence chunks
    ChatAPI-->>User: Top 5 high-precision evidence chunks with line numbers
```

### 3.1 Reciprocal Rank Fusion (RRF) Formula

For each document $d$ appearing in dense ranking $R_{\text{dense}}$ and sparse ranking $R_{\text{sparse}}$:

$$RRF\_Score(d) = \sum_{m \in \{\text{dense}, \text{sparse}\}} \frac{1}{k + r_m(d)}$$

Where:
- $k = 60$ (constant smoothing parameter preventing early high ranks from dominating).
- $r_m(d)$ is the 1-based rank index of document $d$ in system $m$.
- If document $d$ does not appear in system $m$, that component contributes $0$.

### 3.2 Cross-Encoder Reranking
Top-15 candidates from RRF are passed into `cross-encoder/ms-marco-MiniLM-L-6-v2`. Unlike bi-encoders (which compute separate query and document embeddings), the cross-encoder performs joint attention over the combined token sequence:

$$\text{Input: } [\text{CLS}] \circ \text{Query} \circ [\text{SEP}] \circ \text{Code Chunk} \circ [\text{SEP}]$$

The top 5 scoring chunks are retained as evidence context for prompt construction.

---

## 4. Grounded Generation, Streaming & Citation Validation

```mermaid
sequenceDiagram
    autonumber
    actor Client as React Client (ChatPage)
    participant API as FastAPI (/api/chat/sessions/{id}/messages/stream)
    participant Memory as Conversation Memory
    participant Ret as Retrieval & Reranker
    participant Provider as LLM Fallback Chain
    participant Validator as Citation Validator
    participant Store as Storage (Supabase / In-Memory)

    Client->>API: POST /messages/stream {"content": "Explain router setup"}
    API->>Store: Save user message to database
    API->>Memory: Load conversation summary & recent history (budget: 2000 tokens)
    API->>Ret: Retrieve top evidence chunks for query
    Ret-->>API: 5 verified code chunks

    API->>Provider: Stream prompt with context (Gemini -> Groq -> Cerebras -> OpenRouter)
    loop SSE Token Delivery
        Provider-->>API: Yield chunk / token
        API-->>Client: data: {"type": "token", "content": "chunk"}
    end

    Provider-->>API: Stream completed
    API->>Validator: Validate citations in full generated text
    Note over Validator: 1. Extract [file:line-line] tags via regex<br/>2. Verify file exists in repository<br/>3. Verify line span within retrieved chunks<br/>4. Filter ungrounded references

    Validator-->>API: Validated citations list
    API->>Store: Persist assistant message with verified citations
    API-->>Client: data: {"type": "done", "content": "Full response", "citations": [...]}
```

### 4.1 Citation Validation Rules

1. **Regex Extraction**: Scans response text for markdown citation links and bracketed patterns: `[path/to/file:start-end]`.
2. **File Existence**: Verifies that `path/to/file` exists in the repository file registry.
3. **Line Range Boundary**: Checks whether `start_line` and `end_line` overlap with the line bounds of any retrieved chunk for that specific file.
4. **Ungrounded Tag Stripping**: If an LLM hallucinated a non-existent file or fabricated line numbers outside the retrieved context, the citation is removed from the metadata payload and flagged, preserving factual correctness.

---

## 5. Client Architecture & In-Memory Routing Cache

### 5.1 Dashboard Shell & Routing Topology

The dashboard is structured around an persistent layout shell:

```mermaid
flowchart TD
    Router["React Router v6"] --> Home["HomePage (/)<br/>- Link Repository Form (URL or Shorthand)<br/>- Live linking status spinner"]
    Router --> Shell["DashboardShell (/dashboard/:repoId)<br/>- Pinned brand header & mobile navigation drawer<br/>- Persistent Sidebar navigation<br/>- Pinned Sidebar Footer with Unlink Button<br/>- In-memory cache sync"]

    Shell --> Overview["OverviewPage (/overview)<br/>- Compact Header (repo name, branch, status badge, Unlink button)<br/>- Responsive Scale Grid (size, files, chunks, vectors, contributors)<br/>- Live CodeAtlas Processing stage cards<br/>- Two-column layout: Repository Metadata table & Languages/Topics/Contributors"]
    Shell --> Files["FilesPage (/files)<br/>- Recursive File Tree browser<br/>- Fixed-width gutter (52px) line numbers<br/>- Syntax-highlighted code viewer<br/>- File metadata header"]
    Shell --> Chat["ChatPage (/chat)<br/>- SSE real-time streaming message view<br/>- Ingestion readiness guard<br/>- Clickable grounded citation tags<br/>- Markdown and syntax-highlighted code blocks"]
```

### 5.2 Zero-Latency Navigation Cache (`api/cache.ts`)

To eliminate blank loading spinners and redundant network calls when switching between **Overview**, **Files**, and **Chat**:

```mermaid
sequenceDiagram
    autonumber
    actor User as User Navigation
    participant View as Overview / Files / Chat View
    participant Cache as DashboardCache (api/cache.ts)
    participant API as Backend API

    User->>View: Click "Files" tab
    View->>Cache: Read cached file tree for repoId
    alt Cache Hit
        Cache-->>View: Return treeNodes instantly
        View->>View: Render file tree immediately (0ms delay)
    else Cache Miss
        View->>API: GET /api/repositories/{id}/tree
        API-->>View: Return file tree JSON
        View->>Cache: Save treeNodes for repoId
        View->>View: Render file tree
    end

    User->>View: Click file "main.py"
    View->>Cache: Read cached file content
    alt File in Cache
        Cache-->>View: Return content immediately
    else File Not Cached
        View->>API: GET /api/repositories/{id}/files/main.py
        API-->>View: Return content string
        View->>Cache: Save content in cache
    end
```

---

## 6. Database Schema (Supabase / PostgreSQL)

When `CODE_ATLAS_SUPABASE_URL` is set, data is stored across 9 sequential PostgreSQL migrations:

```mermaid
erDiagram
    repositories ||--o{ chunks : "contains"
    repositories ||--o{ files : "contains"
    repositories ||--o{ chat_sessions : "has"
    repositories ||--o{ ingestion_logs : "logs"
    chat_sessions ||--o{ chat_messages : "records"

    repositories {
        uuid id PK
        text name
        text full_name
        text url
        text branch
        text status "pending | cloning | indexing | ready | failed"
        bigint size_bytes
        int file_count
        int chunk_count
        text language
        jsonb repository_metadata
        jsonb contributors
        jsonb processing_status
        boolean metadata_ready
        boolean files_ready
        timestamp created_at
        timestamp updated_at
    }

    chunks {
        uuid id PK
        uuid repository_id FK
        text file_path
        int start_line
        int end_line
        text content
        text content_hash "SHA-256 deduplication"
        vector embedding "768-dimensional Gemini vector"
        tsvector fts "Full-text search vector"
        jsonb chunk_metadata "Imports, symbols, type"
        timestamp created_at
    }

    files {
        uuid id PK
        uuid repository_id FK
        text path
        bigint size_bytes
        text content
        timestamp created_at
    }

    chat_sessions {
        uuid id PK
        uuid repository_id FK
        text title
        timestamp created_at
    }

    chat_messages {
        uuid id PK
        uuid session_id FK
        text role "user | assistant"
        text content
        jsonb citations "Validated citations array"
        timestamp created_at
    }

    ingestion_logs {
        uuid id PK
        uuid repository_id FK
        text stage "clone | filter | chunk | embed"
        text status "started | completed | failed"
        text message
        timestamp created_at
    }
```

---

## 7. Operational Modes & Failure Handling

| Failure Scenario | Mitigation Strategy | Result |
| --- | --- | --- |
| **Primary LLM provider quota exhausted / 429** | Fallback priority chain: Gemini → Groq → Cerebras → OpenRouter | Zero user-visible downtime if at least one provider has remaining quota |
| **Gemini embedding rate limit hit during ingestion** | Exponential backoff with jitter (1s base, 60s max, 5 retries) | Ingestion recovers smoothly without aborting the job |
| **Database unreachable / unconfigured** | Automatic fallback to thread-safe `InMemoryStore` | Application boots and functions locally with zero external setup |
| **Invalid or malformed repository link** | Pre-flight validation against GitHub REST API (`/repos/{owner}/{repo}`) | Clean error notification displayed on Home form before triggering background tasks |
| **Client disconnect during chat stream** | SSE stream detects socket closure and gracefully halts generator | Prevents orphan inference requests from consuming background resources |
