alter table public.repos
    add column if not exists repository_key text;

create unique index if not exists repos_repository_key_unique_idx
    on public.repos (repository_key)
    where repository_key is not null;
