alter table public.repos
    add column if not exists metadata_ready boolean not null default false;

alter table public.repos
    add column if not exists files_ready boolean not null default false;

update public.repos
set metadata_ready = true,
    files_ready = true
where status = 'ready';
