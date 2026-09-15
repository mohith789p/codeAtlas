drop function if exists public.match_semantic_cache(uuid, vector, double precision);

create function public.match_semantic_cache(
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