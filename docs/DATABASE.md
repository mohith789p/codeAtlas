# Database Documentation

## 1. Database Overview

CodeAtlas utilizes PostgreSQL paired with the `pgvector` extension, managed through Supabase and accessed via PostgREST and custom SQL Remote Procedure Calls (RPCs). The database is designed for fast semantic vector search, relational chunk metadata tracking, conversation persistence, and semantic query caching.

A local, non-blocking in-memory database adapter acts as a transparent development and testing fallback when external Supabase credentials are not supplied.

---

## 2. Database Technology

* **Engine**: PostgreSQL 15+
* **Vector Extension**: `pgvector` (`vector` type supporting cosine, L2, and inner product operations)
* **Access Protocol**: PostgREST HTTP REST API & Postgres SQL RPC functions
* **Client Driver**: Asynchronous HTTP client (`httpx.AsyncClient`) communicating with Supabase PostgREST endpoints
* **Security**: Row-Level Security (RLS) enabled on all public schema tables with service-role token access

---

## 3. Schema Overview

The database models codebases hierarchically from repository entities down to code chunks, metadata, and persistent chat sessions.

```
+---------------------+
|        repos        |
+---------------------+
           | 1
           |
           +-----------------------------+-----------------------------+
           | N                           | N                           | N
+---------------------+       +---------------------+       +---------------------+
|   repository_files  |       |       chunks        |       |    chat_sessions    |
+---------------------+       +---------------------+       +---------------------+
                                         | 1                           | 1
                                         |                             |
                                         | 1                           | N
                              +---------------------+       +---------------------+
                              |   chunk_metadata    |       |    chat_messages    |
                              +---------------------+       +---------------------+
```

---

## 4. Tables and Entities

### 4.1 Repositories (`public.repos`)
Stores high-level metadata, processing statistics, and ingestion states for processed GitHub repositories.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `uuid` | `PRIMARY KEY` | Unique repository identifier |
| `name` | `text` | `NOT NULL` | Repository short name (e.g. `flask`) |
| `full_name` | `text` | — | Owner and name (e.g. `pallets/flask`) |
| `description` | `text` | — | Repository summary from GitHub |
| `owner` | `text` | — | GitHub user or organization name |
| `branch` | `text` | — | Indexed Git branch |
| `language` | `text` | — | Primary repository language |
| `url` | `text` | `NOT NULL` | Full remote GitHub URL |
| `status` | `text` | `NOT NULL` | State: `queued`, `downloading`, `filtering`, `chunking`, `embedding`, `indexing`, `ready`, `failed` |
| `error` | `text` | — | Error trace if ingestion failed |
| `files` | `integer` | `DEFAULT 0` | Count of filtered source files |
| `folders` | `integer` | `DEFAULT 0` | Count of directories |
| `contributors`| `integer` | `DEFAULT 0` | Count of active contributors |
| `size_kb` | `integer` | — | Repository archive size in kilobytes |
| `created_at` | `timestamptz` | `DEFAULT now()` | Ingestion timestamp |
| `updated_at` | `timestamptz` | `DEFAULT now()` | Last update timestamp |

### 4.2 Files (`public.repository_files`)
Stores path mapping and optional cached content for files within an indexed repository.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `repo_id` | `uuid` | `REFERENCES repos(id) ON DELETE CASCADE` | Parent repository |
| `path` | `text` | `NOT NULL` | Relative file path (e.g. `src/app/main.py`) |
| `content` | `text` | `NOT NULL` | Raw file contents |
| `created_at` | `timestamptz` | `DEFAULT now()` | File creation timestamp |
| `updated_at` | `timestamptz` | `DEFAULT now()` | File modification timestamp |

*Primary Key:* `(repo_id, path)`

### 4.3 Code Chunks (`public.chunks` and `public.chunk_metadata`)
Code chunk data is normalized into two complementary tables to optimize vector scanning speed and isolate metadata.

#### `public.chunks`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `uuid` | `PRIMARY KEY, DEFAULT gen_random_uuid()` | Unique chunk ID |
| `repo_id` | `uuid` | `REFERENCES repos(id) ON DELETE CASCADE` | Associated repository |
| `content_hash`| `char(64)` | `NOT NULL` | SHA-256 hash of chunk content |
| `content` | `text` | `NOT NULL` | Source code text of the chunk |
| `embedding` | `vector(768)`| `NOT NULL` | 768-dimensional dense vector |
| `search_vector`| `tsvector` | `GENERATED ALWAYS AS (to_tsvector('english', content)) STORED` | Lexical search token vector |
| `created_at` | `timestamptz` | `DEFAULT now()` | Creation timestamp |
| `updated_at` | `timestamptz` | `DEFAULT now()` | Modification timestamp |

*Uniqueness Constraint:* `UNIQUE (repo_id, content_hash)`

#### `public.chunk_metadata`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `chunk_id` | `uuid` | `PRIMARY KEY, REFERENCES chunks(id) ON DELETE CASCADE` | 1-to-1 chunk link |
| `filepath` | `text` | `NOT NULL` | Source file path |
| `language` | `text` | — | Programming language |
| `symbol` | `text` | — | Extracted AST function/class name |
| `symbol_type` | `text` | — | `function`, `class`, `method`, `block` |
| `class_name` | `text` | — | Enclosing class if method |
| `parent_symbol`| `text` | — | Parent enclosing symbol |
| `start_line` | `integer` | — | Source code starting line (1-indexed) |
| `end_line` | `integer` | — | Source code ending line (inclusive) |
| `imports` | `jsonb` | `DEFAULT '[]'::jsonb` | Extracted module dependencies |

### 4.4 Conversations (`public.chat_sessions`)
Persists chat threads scoped to specific repositories.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `uuid` | `PRIMARY KEY` | Session ID |
| `repository_id`| `uuid`| `REFERENCES repos(id) ON DELETE CASCADE` | Scoped repository |
| `created_at` | `timestamptz` | `DEFAULT now()` | Session start time |
| `updated_at` | `timestamptz` | `DEFAULT now()` | Last activity timestamp |

### 4.5 Messages (`public.chat_messages`)
Stores individual user queries and assistant responses with verified citations.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `uuid` | `PRIMARY KEY` | Message ID |
| `session_id` | `uuid` | `REFERENCES chat_sessions(id) ON DELETE CASCADE` | Parent conversation |
| `role` | `text` | `NOT NULL` | `user` or `assistant` |
| `content` | `text` | `NOT NULL` | Message markdown content |
| `citations` | `jsonb` | `DEFAULT '[]'::jsonb` | Validated citation array |
| `created_at` | `timestamptz` | `DEFAULT now()` | Creation timestamp |

---

## 5. Entity Relationships

* **Repositories to Chunks**: `1-to-N` (`repos.id` &rarr; `chunks.repo_id`). Cascading delete removes all chunks if a repository is deleted.
* **Chunks to Metadata**: `1-to-1` (`chunks.id` &rarr; `chunk_metadata.chunk_id`). Cascades on chunk removal.
* **Repositories to Files**: `1-to-N` (`repos.id` &rarr; `repository_files.repo_id`). Cascades on delete.
* **Repositories to Sessions**: `1-to-N` (`repos.id` &rarr; `chat_sessions.repository_id`). Cascades on delete.
* **Sessions to Messages**: `1-to-N` (`chat_sessions.id` &rarr; `chat_messages.session_id`). Cascades on delete.

---

## 6. Vector Embedding Storage

### 6.1 Embedding Model
Vector embeddings are generated using Google Gemini's **`text-embedding-004`** model.

### 6.2 Embedding Dimensions
Embeddings are formatted as 768-dimensional single-precision floating-point arrays (`vector(768)`).

### 6.3 Vector Data Representation
PostgreSQL stores vectors in memory-aligned blocks managed by `pgvector`. Cosine distance is the standard metric used for similarity:
$$\text{similarity} = 1 - (\mathbf{u} \cdot \mathbf{v})$$

---

## 7. Database Indexing

### 7.1 HNSW Vector Index
Dense embeddings are indexed using Hierarchical Navigable Small World (HNSW) graphs:
```sql
create index chunks_embedding_hnsw_idx
    on public.chunks using hnsw (embedding vector_cosine_ops);
```
* **Operator Class**: `vector_cosine_ops` (optimizes normalized cosine similarity).
* **Properties**: Delivers logarithmic search time $\mathcal{O}(\log N)$ without requiring full sequential vector table scans.

### 7.2 GIN Full-Text Search Index
Lexical keywords on chunk code are indexed via Generalized Inverted Indexes (GIN):
```sql
create index chunks_search_vector_idx
    on public.chunks using gin (search_vector);
```
* **Target**: Stored column `search_vector tsvector` generated via `to_tsvector('english', content)`.
* **Properties**: Enables sub-millisecond sparse full-text phrase and keyword lookups.

---

## 8. Search and Retrieval

### 8.1 Semantic Search (`match_chunks` RPC)
```sql
create or replace function public.match_chunks(
    query_embedding vector(768),
    match_repo_id uuid,
    match_count integer default 20
)
returns table (
    id uuid,
    repo_id uuid,
    content text,
    similarity double precision,
    filepath text,
    language text,
    symbol text,
    symbol_type text,
    class_name text,
    parent_symbol text,
    start_line integer,
    end_line integer,
    imports jsonb
)
language sql stable as $$
    select
        c.id,
        c.repo_id,
        c.content,
        1 - (c.embedding <=> query_embedding) as similarity,
        m.filepath,
        m.language,
        m.symbol,
        m.symbol_type,
        m.class_name,
        m.parent_symbol,
        m.start_line,
        m.end_line,
        m.imports
    from public.chunks c
    left join public.chunk_metadata m on c.id = m.chunk_id
    where c.repo_id = match_repo_id
    order by c.embedding <=> query_embedding
    limit match_count;
$$;
```

### 8.2 Keyword Search (`search_chunks` RPC)
```sql
create or replace function public.search_chunks(
    match_repo_id uuid,
    search_query text,
    match_count integer default 20
)
returns table (
    id uuid,
    repo_id uuid,
    content text,
    rank double precision,
    filepath text,
    language text,
    symbol text,
    symbol_type text,
    class_name text,
    parent_symbol text,
    start_line integer,
    end_line integer,
    imports jsonb
)
language sql stable as $$
    select
        c.id,
        c.repo_id,
        c.content,
        ts_rank_cd(c.search_vector, websearch_to_tsquery('english', search_query)) as rank,
        m.filepath,
        m.language,
        m.symbol,
        m.symbol_type,
        m.class_name,
        m.parent_symbol,
        m.start_line,
        m.end_line,
        m.imports
    from public.chunks c
    left join public.chunk_metadata m on c.id = m.chunk_id
    where c.repo_id = match_repo_id
      and c.search_vector @@ websearch_to_tsquery('english', search_query)
    order by rank desc
    limit match_count;
$$;
```

### 8.3 Hybrid Search
The backend executes `match_chunks` and in-memory `BM25Okapi` in parallel, normalizes the distinct score spaces with Reciprocal Rank Fusion ($RRF$), and applies Cross-Encoder reranking over the joined candidates.

---

## 9. Data Integrity and Constraints

* **Idempotent Chunking**: `unique (repo_id, content_hash)` prevents redundant storage of identical code segments.
* **Cascading Purges**: `ON DELETE CASCADE` guarantees that removing a repository cleans all files, chunks, metadata, sessions, and messages.
* **Check Constraints**: `repos.status` is restricted to known state machine strings (`queued`, `downloading`, `filtering`, `chunking`, `embedding`, `indexing`, `ready`, `failed`).

---

## 10. Database Configuration and Setup

### Supabase Environment Variables
```ini
CODE_ATLAS_SUPABASE_URL=https://<your-project-ref>.supabase.co
CODE_ATLAS_SUPABASE_SERVICE_ROLE_KEY=eyJh...
```

When these keys are omitted, the application operates with its local in-memory persistence layer, enabling zero-dependency local runs.

---

## 11. Migrations and Maintenance

SQL migrations are located in `backend/supabase/migrations/` and applied sequentially:

1. `0001_initial_schema.sql`: Core `repos`, `chunks`, `chunk_metadata`, `logs` tables and `pgvector` extension setup.
2. `0002_retrieval_schema.sql`: `semantic_cache` table and `match_chunks`, `search_chunks` RPC definitions.
3. `0003_evaluation_schema.sql`: Evaluation harness tables (`eval_golden_set`, `eval_results`).
4. `0004_fix_semantic_cache_similarity.sql`: Unambiguous named parameter resolution for `match_semantic_cache`.
5. `0005_repository_idempotency.sql`: Repository conflict and unique constraints.
6. `0006_files_and_chat_persistence.sql`: `repository_files`, `chat_sessions`, and `chat_messages` tables.
7. `0007_contributor_details.sql`: Structured contributor JSONB payload handling.
8. `0008_ingestion_readiness.sql`: Stage readiness tracking flags.
9. `0009_repository_metadata_and_processing.sql`: Top-level metadata and processing telemetry attributes.

Apply migrations via the Supabase CLI:
```bash
supabase db push
```
Or paste individual migration files into the Supabase SQL Editor.
