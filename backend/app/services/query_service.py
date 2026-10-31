import time
from uuid import UUID

from app.generation.step_03_response_generator import ResponseGenerator
from app.generation.step_04_citation_validator import CitationValidator
from app.generation.step_05_response_formatter import ResponseFormatter
from app.retrieval.step_01_query_preprocessor import QueryPreprocessor
from app.retrieval.step_02_semantic_cache import SemanticCache
from app.retrieval.step_03_hybrid_retriever import HybridRetriever
from app.retrieval.step_04_rrf_fusion import RRFFusion
from app.retrieval.step_05_reranker import CrossEncoderReranker
from app.schemas.query import QueryOptions
from app.schemas.response import GenerationResponse
from app.services.repository_service import RepositoryService
from app.shared.observability import safe_traceable


class QueryService:
    """Orchestrates retrieval (Steps 01-05) and grounded generation (Steps 01-05)."""

    def __init__(
        self,
        repo_service: RepositoryService | None = None,
        retriever: HybridRetriever | None = None,
        cache: SemanticCache | None = None,
    ) -> None:
        self.repo_service = repo_service or RepositoryService()
        db_repo = getattr(self.repo_service, "db_repo", None)
        self.preprocessor = QueryPreprocessor()
        self.cache = cache or SemanticCache(db_repo=db_repo)
        self.retriever = retriever or HybridRetriever(db_repo=db_repo)
        self.fusion = RRFFusion()
        self.reranker = CrossEncoderReranker()
        self.generator = ResponseGenerator()
        self.validator = CitationValidator()
        self.formatter = ResponseFormatter()

    @safe_traceable(name="query_pipeline", run_type="chain")
    async def query(self, repo_id: UUID, raw_query: str, options: QueryOptions | None = None) -> GenerationResponse:
        """Execute end-to-end question answering against repository codebase."""
        opts = options or QueryOptions()
        start = time.perf_counter()

        # Gate: Check repository is ready
        await self.repo_service.assert_ready(repo_id)

        # Retrieval Step 1: Preprocess & Embed Query
        clean_query, query_emb = await self.preprocessor.preprocess(raw_query)

        # Retrieval Step 2: Semantic Cache Lookup
        if opts.use_cache:
            cache_hit = await self.cache.lookup(repo_id, clean_query, query_emb, opts.similarity_threshold)
            if cache_hit:
                cached_data = cache_hit.response
                latency = (time.perf_counter() - start) * 1000.0
                return self.formatter.format(
                    answer=cached_data.get("answer", ""),
                    citations=[self.validator._CITATION_REGEX for _ in []],
                    provider=cached_data.get("provider", "cache"),
                    model=cached_data.get("model", "cache"),
                    cache_hit=True,
                    latency_ms=latency,
                    chunks_count=cached_data.get("retrieved_chunks_count", 0),
                )

        # Retrieval Step 3: Hybrid Concurrent Search (Dense HNSW + Sparse BM25)
        dense_res, sparse_res = await self.retriever.retrieve(repo_id, clean_query, query_emb, limit=20)

        # Retrieval Step 4: RRF Fusion
        fused = self.fusion.fuse(dense_res, sparse_res, top_k=20)

        # Retrieval Step 5: Cross-Encoder Reranking
        top_chunks = self.reranker.rerank(clean_query, fused, top_k=opts.top_k)

        # Generation Step 1-3: Prompt & LLM Client with Empty Chunk Guard
        raw_answer, provider, model, is_empty = await self.generator.generate_response(clean_query, top_chunks)

        # Generation Step 4: Line-level Citation Validation
        citations = [] if is_empty else self.validator.validate_citations(raw_answer, top_chunks)

        # Generation Step 5: Formatting & Cache Storage
        latency = (time.perf_counter() - start) * 1000.0
        response = self.formatter.format(raw_answer, citations, provider, model, False, latency, len(top_chunks))
        if not is_empty and opts.use_cache:
            await self.cache.save(repo_id, clean_query, query_emb, response.model_dump())

        return response
