alter table public.repos
    add column if not exists stars integer not null default 0,
    add column if not exists forks integer not null default 0,
    add column if not exists open_issues integer not null default 0,
    add column if not exists open_pull_requests integer,
    add column if not exists repository_metadata jsonb not null default '{}'::jsonb,
    add column if not exists processing_stats jsonb not null default '{}'::jsonb;
