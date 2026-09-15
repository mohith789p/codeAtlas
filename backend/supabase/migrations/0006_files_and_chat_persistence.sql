create table if not exists public.repository_files (
    repo_id uuid not null references public.repos(id) on delete cascade,
    path text not null,
    content text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (repo_id, path)
);

create index if not exists repository_files_repo_idx on public.repository_files (repo_id, path);

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

alter table public.repository_files enable row level security;
alter table public.chat_sessions enable row level security;
alter table public.chat_messages enable row level security;
