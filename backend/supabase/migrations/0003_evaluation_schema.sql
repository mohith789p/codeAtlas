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

alter table public.eval_golden_set enable row level security;
alter table public.eval_results enable row level security;
