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
        s.response,
                1 - (s.query_embedding <=> p_query_embedding) as similarity
    from public.semantic_cache s
        where s.repo_id = p_repo_id
            and 1 - (s.query_embedding <=> p_query_embedding) >= p_similarity_threshold
        order by s.query_embedding <=> p_query_embedding
    limit 1;
$$;

alter table public.semantic_cache enable row level security;
alter table public.repos enable row level security;
alter table public.chunks enable row level security;
alter table public.chunk_metadata enable row level security;
alter table public.logs enable row level security;
