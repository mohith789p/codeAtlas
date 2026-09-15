create extension if not exists vector;

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
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

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
