# Code Atlas backend

The backend is a FastAPI service. It provides the repository/job API, streamed GitHub acquisition, ordered file filtering, Tree-sitter/LangChain chunking, Gemini embedding, content-hash indexing, repository file browsing, and session endpoints used by the existing frontend.

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
uvicorn app.main:app --reload
```

Apply `supabase/migrations/0001_initial_schema.sql` to a Supabase project before setting `CODE_ATLAS_SUPABASE_URL` and `CODE_ATLAS_SUPABASE_SERVICE_ROLE_KEY`. Without those values, the local in-memory persistence adapter remains available for tests and local UI work. The API does not report retrieval-backed answers before retrieval exists.

For retrieval, apply `supabase/migrations/0002_retrieval_schema.sql` after migration 0001. It creates the repository-scoped semantic cache and the `match_chunks`, `search_chunks`, and `match_semantic_cache` Postgres RPCs. The backend uses the service-role key server-side; RLS is enabled on the tables and no public policies are created because authentication is out of scope.

For offline evaluation, apply `supabase/migrations/0003_evaluation_schema.sql` after migration 0002. It creates `eval_golden_set` and `eval_results`, both keyed by repository and content-derived evaluation version. Evaluation is automatically claimed once after READY when the application passes its evaluation worker into ingestion. The controlled live smoke test uses five examples; the configured full run target defaults to 100 examples.

Apply `supabase/migrations/0004_fix_semantic_cache_similarity.sql` after migration 0003. It replaces the deployed cache RPC with explicitly named parameters (`p_repo_id`, `p_query_embedding`, and `p_similarity_threshold`) so stored-vs-incoming cosine similarity, threshold enforcement, and repository scoping are unambiguous. Do not run the full evaluation until this migration is applied and the live retrieval smoke test passes.

Run retrieval tests locally with:

```powershell
python -m pytest -q -m "not live"
```

After applying migration 0002 and installing the declared dependencies, run the live retrieval check against a ready repository:

```powershell
$env:CODE_ATLAS_RETRIEVAL_REPOSITORY_ID = "<ready-repository-uuid>"
$env:CODE_ATLAS_RETRIEVAL_QUERY = "Where is the main entry point?"
python -m pytest -q -m live tests/test_live_retrieval.py -s
```
