# CodeAtlas Architecture Guide 🏛️

This document outlines the architectural blueprint, data flows, core components, and engineering decisions behind **CodeAtlas**.

---

## 1. System Context & High-Level Architecture

CodeAtlas operates as a decoupled client-server system designed for repository intelligence, code semantic search, and citation-grounded conversational reasoning.

```mermaid
graph TD
    User([Developer / User])
    
    subgraph Client ["Client Tier (React 18 + Vite)"]
        SPA["Single Page Application"]
        HookChat["useChatSession (SSE Engine)"]
        UIComp["Components (Overview, Files, Chat)"]
        Cache["Client-Side Dashboard Cache"]
    end

    subgraph Service ["Application Tier (FastAPI Service)"]
        Router["API Gateway / Controllers"]
        
        subgraph PipelineIngestion ["Ingestion Engine"]
            GH["GitHub Archive Service"]
            Filter["File Filter & Language Classifier"]
            Chunker["AST / LangChain Chunker"]
            EmbedService["Gemini Embedding Service"]
            IndexService["Content-Hash Indexing Service"]
        end

        subgraph PipelineRAG ["Hybrid RAG & Generation"]
            CacheService["Semantic Cache Engine"]
            DenseSearch["Dense Search (Gemini 768d)"]
            SparseSearch["Sparse Full-Text Match"]
            RRF["Reciprocal Rank Fusion (k=60)"]
            Rerank["Cross-Encoder Reranker"]
            Providers["LLM Provider Chain (Gemini/Groq/Cerebras/OpenRouter)"]
            Memory["ConversationSummaryBufferMemory"]
            Validator["Citation & Grounding Validator"]
        end
    end

    subgraph Persistence ["Persistence Tier"]
        Store["InMemoryStore (Default / Local Fallback)"]
        Supabase[("Supabase PostgreSQL + pgvector")]
    end

    User <--> SPA
    SPA --> HookChat
    SPA --> UIComp
    SPA <--> Cache
    HookChat -->|REST & SSE| Router
    UIComp -->|REST| Router

    Router --> PipelineIngestion
    Router --> PipelineRAG
    PipelineIngestion --> Store
    PipelineRAG --> Store
    Store -.->|Configured| Supabase
```

---

## 2. Ingestion & Indexing Pipeline

The ingestion pipeline transforms raw repository source code into indexed, searchable chunks. It is designed to be **incremental**, **idempotent**, and **resilient** to network interruptions.

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as FastAPI Gateway
    participant Store as InMemory / Supabase Store
    participant Ingestion as Ingestion Engine
    participant GH as GitHub API / Raw Archive
    participant Chunker as Syntax Chunker
    participant Embed as Gemini Embedder
    participant Indexer as Indexing Service

    Client->>API: POST /api/repositories (url / manual)
    API->>Store: get_or_create_repository()
    API-->>Client: 202 Accepted (Repository object)
    
    Note over API,Ingestion: Async Background Task Launched

    Ingestion->>Store: Set status: DOWNLOADING
    Ingestion->>GH: Inspect repo metadata & download zip archive
    GH-->>Ingestion: Extracted directory tree
    
    Ingestion->>Store: Set status: FILTERING
    Ingestion->>Ingestion: collect_text_files (skip binaries, .git, minified files)
    Ingestion->>Store: save_files()
    
    Ingestion->>Store: Set status: CHUNKING
    Ingestion->>Chunker: chunk_file(path, content)
    Chunker-->>Ingestion: list[Document] with AST metadata
    Ingestion->>Store: save_documents()
    
    Ingestion->>Store: Set status: INDEXING
    Ingestion->>Indexer: index_documents(repo_id, documents)
    Indexer->>Store: get_chunks_by_hash(hashes)
    Indexer->>Embed: embed_documents(unindexed_chunks) in batches
    Embed-->>Indexer: 768-dimensional float vectors
    Indexer->>Store: upsert_chunks() & upsert_chunk_metadata()
    Indexer->>Store: delete_stale_chunks()
    
    Ingestion->>Store: Set status: READY
    Ingestion->>Store: log_event(status=READY, duration_ms)
```

### Ingestion Lifecycle Stages
```
QUEUED ──► DOWNLOADING ──► FILTERING ──► CHUNKING ──► INDEXING ──► READY
  │                                                                 ▲
  └───────────────────────────────► FAILED ─────────────────────────┘ (Retry on duplicate submission)
```

1. **`QUEUED`**: Repository registered in database; waiting for worker execution.
2. **`DOWNLOADING`**: Fetching repository metadata (stars, forks, languages, topics) and streaming ZIP archive from GitHub.
3. **`FILTERING`**: Filtering out binary assets, images, vendor dependencies, and lockfiles, while persisting valid text files.
4. **`CHUNKING`**: Language-specific AST/Tree-Sitter semantic chunking to preserve symbol contexts (class/function definitions, line numbers).
5. **`INDEXING`**: Computing SHA-256 content hashes, deduplicating against existing vectors, generating Gemini embeddings, and persisting to Postgres `pgvector`.
6. **`READY`**: Repository fully indexed and available for hybrid search and chat queries.
7. **`FAILED`**: Ingestion encountered an unrecoverable error; error message captured and logged.

---

## 3. Hybrid Retrieval & Reranking Architecture (RAG)

CodeAtlas uses a state-of-the-art hybrid search pipeline combining **Dense Semantic Search**, **Sparse Lexical Search**, **Reciprocal Rank Fusion (RRF)**, and **Cross-Encoder Reranking**.

```mermaid
flowchart TD
    Query["User Query: 'Where is authentication middleware configured?'"] --> CacheCheck{"Check Semantic Cache<br/>(Cosine Sim >= 0.92)"}
    
    CacheCheck -->|Cache Hit| ReturnCached["Return Cached Generation Response"]
    
    CacheCheck -->|Cache Miss| QueryEmbedding["Generate Query Embedding (Gemini 768d)"]
    
    subgraph ParallelRetrieval ["Parallel Retrieval Stages"]
        QueryEmbedding --> Dense["Dense Vector Search<br/>Top 20 candidates (pgvector <=> cosine)"]
        Query --> Sparse["Sparse Lexical Search<br/>Top 20 candidates (tsvector / BM25 term frequency)"]
    end
    
    Dense --> RRF["Reciprocal Rank Fusion (RRF)<br/>Score = Σ 1 / (60 + rank)<br/>Select Top 15 candidates"]
    Sparse --> RRF
    
    RRF --> Reranker["Cross-Encoder Semantic Reranker<br/>Model: cross-encoder/ms-marco-MiniLM-L-6-v2<br/>Select Top 5 candidates"]
    
    Reranker --> FormattedEvidence["Structured JSON Evidence Formatter<br/>(filepath, start_line, end_line, symbol, code)"]
```

### Reciprocal Rank Fusion (RRF) Formula
Candidates from dense and sparse retrieval stages are merged using the constant $k = 60$:

$$\text{RRF\_Score}(d) = \sum_{m \in \{\text{dense}, \text{sparse}\}} \frac{1}{60 + \text{rank}_m(d)}$$

---

## 4. Generation Pipeline & Streaming Protocol

```mermaid
sequenceDiagram
    autonumber
    actor Client as Frontend Client
    participant Stream as FastAPI SSE Stream (/messages/stream)
    participant Gen as GenerationService
    participant RAG as RetrievalService
    participant Mem as LangChain Memory
    participant LLM as Provider Chain (Gemini / Groq / Cerebras / OpenRouter)
    participant Val as Grounding & Citation Validator

    Client->>Stream: POST /api/chat/sessions/{id}/messages/stream {content: "..."}
    Stream->>Gen: answer_stream(repo_id, session_id, query)
    Gen->>RAG: retrieve(repo_id, query)
    RAG-->>Gen: Top 5 Reranked Evidence Chunks
    Gen->>Mem: load_history(session_id, current_query)
    Mem-->>Gen: Summarized Conversation Buffer
    Gen->>Gen: build_prompt(query, evidence, memory)
    
    Gen->>LLM: generate_stream(prompt)
    loop Token Streaming
        LLM-->>Gen: token chunk
        Gen-->>Stream: yield {type: "token", content: token}
        Stream-->>Client: data: {"type": "token", "content": token}
    end
    
    Gen->>Val: validate(full_content, citations, evidence)
    Val-->>Gen: ValidationResult (valid=True/False, citations=[...])
    
    Gen-->>Stream: yield {type: "done", message: {...}, citations: [...]}
    Stream-->>Client: data: {"type": "done", "message": {...}}
```

### Multi-Provider Fallback Strategy
If a provider encounters an HTTP error, quota exhaustion, or rate limit, `ProviderChain` automatically fails over in sequence:

```
1. Google Gemini 2.5 Flash (Primary)
   └──► 2. Groq LLaMA 3.3 70B (Fast Fallback)
        └──► 3. Cerebras LLaMA 3.3 70B (High-Throughput Fallback)
             └──► 4. OpenRouter GPT-4o-mini (Universal Fallback)
```

---

## 5. Persistence Architecture

CodeAtlas uses a dual-engine storage architecture:

```mermaid
classDiagram
    class InMemoryStore {
        +dict repositories
        +dict repository_files
        +dict repository_documents
        +dict chunks
        +dict semantic_cache
        +dict sessions
        +dict messages
        +dense_search()
        +sparse_search()
        +get_semantic_cache()
    }

    class SupabasePersistence {
        +httpx.AsyncClient client
        +upsert_repository()
        +list_repositories()
        +upsert_chunks()
        +dense_search()
        +sparse_search()
        +save_semantic_cache()
        +get_semantic_cache()
    }

    InMemoryStore --> SupabasePersistence : Delegates durable calls when configured
```

### Database Entities & Schema Mapping
- **`repos`**: Repository metadata, statistics, ingestion stage, branch, and configuration.
- **`repository_files`**: Source file contents indexed by `(repo_id, path)`.
- **`chunks`**: Content chunks with `vector(768)` embeddings and content hashes.
- **`chunk_metadata`**: Symbol names, types, line ranges (`start_line`, `end_line`), and import statements.
- **`chat_sessions`**: Conversation session records linked to repositories.
- **`chat_messages`**: User and assistant messages, including verified citation metadata.
- **`semantic_cache`**: Query embeddings and generation responses with similarity thresholding.
- **`logs`**: Structured audit events with sensitive token redaction and execution latencies.

---

## 6. Security, Redaction, & Error Boundaries

- **Sensitive Data Redaction**: The [`logging_utils`](file:///d:/workspace/codeatlas/backend/app/logging_utils.py) subsystem automatically strips API keys, Authorization headers, Bearer tokens, and secrets from all logs and database event payloads.
- **Global Error Boundary**: FastAPI global exception handlers catch unexpected runtime failures and return sanitized RFC 7807 compliant error payloads without exposing internal stack traces.
- **Citation Guardrails**: Hallucinated file paths or invented line numbers are stripped by `CitationValidator` before citations are presented in the UI.
