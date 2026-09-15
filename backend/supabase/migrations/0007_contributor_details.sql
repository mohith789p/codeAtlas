alter table public.repos
    add column if not exists contributor_details jsonb not null default '[]'::jsonb;
