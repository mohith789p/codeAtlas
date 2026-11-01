-- ==============================================================================
-- CodeAtlas Database Schema
-- ==============================================================================

-- 1. Extensions
create extension if not exists vector;

-- 2. Repositories Table
create table if not exists public.repos (
    id uuid primary key,
    name text not null,
    full_name text,
    description text,
    owner text,
    branch text,
    language text,
    url text not null,
    status text not null check (status in ('queued', 'downloading', 'filtering', 'chunking', 'embedding', 'indexing', 'ready', 'failed')),
    error text,
    files integer not null default 0,
    folders integer not null default 0,
    contributors integer not null default 0,
    size_kb integer,
    repository_key text,
    stars integer not null default 0,
    forks integer not null default 0,
    open_pull_requests integer,
    metadata_ready boolean not null default false,
    files_ready boolean not null default false,
    contributor_details jsonb not null default '[]'::jsonb,
    repository_metadata jsonb not null default '{}'::jsonb,
    processing_stats jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index if not exists repos_repository_key_unique_idx
    on public.repos (repository_key)
    where repository_key is not null;

-- 3. Repository Files Table
create table if not exists public.repository_files (
    repo_id uuid not null references public.repos(id) on delete cascade,
    path text not null,
    content text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (repo_id, path)
);

create index if not exists repository_files_repo_idx on public.repository_files (repo_id, path);

-- 4. Code Chunks Table
create table if not exists public.chunks (
    id uuid primary key default gen_random_uuid(),
    repo_id uuid not null references public.repos(id) on delete cascade,
    content_hash char(64) not null,
    content text not null,
    embedding vector(768) not null,
    search_vector tsvector generated always as (to_tsvector('english', content)) stored,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (repo_id, content_hash)
);

create index if not exists chunks_embedding_hnsw_idx
    on public.chunks using hnsw (embedding vector_cosine_ops);

create index if not exists chunks_search_vector_idx
    on public.chunks using gin (search_vector);

create index if not exists chunks_repo_id_idx on public.chunks (repo_id);

-- 5. Chunk Metadata Table
create table if not exists public.chunk_metadata (
    chunk_id uuid primary key references public.chunks(id) on delete cascade,
    filepath text not null,
    language text,
    symbol text,
    symbol_type text,
    class_name text,
    parent_symbol text,
    start_line integer,
    end_line integer,
    imports jsonb not null default '[]'::jsonb
);

-- 6. Ingestion & System Logs Table
create table if not exists public.logs (
    id uuid primary key default gen_random_uuid(),
    repo_id uuid references public.repos(id) on delete set null,
    stage text not null,
    level text not null default 'info',
    message text not null,
    metadata jsonb not null default '{}'::jsonb,
    latency_ms double precision,
    created_at timestamptz not null default now()
);

create index if not exists logs_repo_stage_idx on public.logs (repo_id, stage, created_at desc);

-- 7. Semantic Query Cache Table
create table if not exists public.semantic_cache (
    id uuid primary key default gen_random_uuid(),
    repo_id uuid not null references public.repos(id) on delete cascade,
    query_hash char(64) not null,
    query_text text not null,
    query_embedding vector(768) not null,
    response jsonb not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (repo_id, query_hash)
);

create index if not exists semantic_cache_repo_idx on public.semantic_cache (repo_id, created_at desc);

-- 8. Chat Sessions & Messages Tables
create table if not exists public.chat_sessions (
    id uuid primary key,
    repository_id uuid not null references public.repos(id) on delete cascade,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists chat_sessions_repository_idx on public.chat_sessions (repository_id, updated_at);

create table if not exists public.chat_messages (
    id uuid primary key,
    session_id uuid not null references public.chat_sessions(id) on delete cascade,
    role text not null,
    content text not null,
    citations jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists chat_messages_session_idx on public.chat_messages (session_id, created_at);

-- 9. Evaluation Framework Tables
create table if not exists public.eval_golden_set (
    id uuid primary key default gen_random_uuid(),
    repo_id uuid not null references public.repos(id) on delete cascade,
    eval_version text not null,
    question_hash char(64) not null,
    question text not null,
    answer text not null,
    ground_truth jsonb not null,
    question_embedding vector(768),
    validation_score double precision not null,
    created_at timestamptz not null default now(),
    unique (repo_id, eval_version, question_hash)
);

create index if not exists eval_golden_repo_version_idx
    on public.eval_golden_set (repo_id, eval_version);

create table if not exists public.eval_results (
    id uuid primary key default gen_random_uuid(),
    repo_id uuid not null references public.repos(id) on delete cascade,
    eval_version text not null,
    status text not null check (status in ('running', 'completed', 'failed')),
    generated_count integer not null default 0,
    accepted_count integer not null default 0,
    rejected_count integer not null default 0,
    query_count integer not null default 0,
    successful_count integer not null default 0,
    failed_count integer not null default 0,
    recall_at_5 double precision,
    precision_at_5 double precision,
    mrr double precision,
    latency_stats jsonb not null default '{}'::jsonb,
    per_query jsonb not null default '[]'::jsonb,
    error text,
    started_at timestamptz not null default now(),
    completed_at timestamptz,
    unique (repo_id, eval_version)
);

create index if not exists eval_results_repo_idx on public.eval_results (repo_id, started_at desc);

-- 10. RPC Vector and Lexical Search Functions
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
language sql stable
as $$
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
    join public.chunk_metadata m on m.chunk_id = c.id
    where c.repo_id = match_repo_id
    order by c.embedding <=> query_embedding
    limit least(greatest(match_count, 1), 20);
$$;

create or replace function public.search_chunks(
    search_query text,
    match_repo_id uuid,
    match_count integer default 20
)
returns table (
    id uuid,
    repo_id uuid,
    content text,
    rank_score real,
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
language sql stable
as $$
    with query as (
        select websearch_to_tsquery('english', search_query) as tsquery
    )
    select
        c.id,
        c.repo_id,
        c.content,
        greatest(
            ts_rank_cd(c.search_vector, query.tsquery),
            case when coalesce(m.symbol, '') = search_query then 1.0 else 0.0 end
        ) as rank_score,
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
    join public.chunk_metadata m on m.chunk_id = c.id
    cross join query
    where c.repo_id = match_repo_id
      and (c.search_vector @@ query.tsquery or m.symbol = search_query)
    order by (m.symbol = search_query) desc, rank_score desc, c.id
    limit least(greatest(match_count, 1), 20);
$$;

create or replace function public.match_semantic_cache(
    p_repo_id uuid,
    p_query_embedding vector(768),
    p_similarity_threshold double precision default 0.92
)
returns table (
    response jsonb,
    similarity double precision
)
language sql stable
as $$
    select
        cache_entry.response,
        1 - (cache_entry.query_embedding <=> p_query_embedding) as similarity
    from public.semantic_cache as cache_entry
    where cache_entry.repo_id = p_repo_id
      and 1 - (cache_entry.query_embedding <=> p_query_embedding) >= p_similarity_threshold
    order by cache_entry.query_embedding <=> p_query_embedding
    limit 1;
$$;

-- 11. Row-Level Security
alter table public.repos enable row level security;
alter table public.repository_files enable row level security;
alter table public.chunks enable row level security;
alter table public.chunk_metadata enable row level security;
alter table public.logs enable row level security;
alter table public.semantic_cache enable row level security;
alter table public.chat_sessions enable row level security;
alter table public.chat_messages enable row level security;
alter table public.eval_golden_set enable row level security;
alter table public.eval_results enable row level security;
