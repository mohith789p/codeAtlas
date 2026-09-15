import logging
from pathlib import Path
from uuid import UUID

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .persistence import PersistenceError
from .models import (
    ChatMessage,
    ChatSession,
    FileContentResponse,
    FileNode,
    FileTreeResponse,
    IngestRequest,
    Repository,
    canonical_repository_identity,
)
from .services.ingestion import run_ingestion
from .services.embeddings import GeminiEmbeddingService
from .services.evaluation import build_evaluation_service
from .services.generation import GenerationProviderError, GenerationService, build_memory_provider_chain, build_provider_chain
from .services.memory import ConversationMemory, ProviderChainLanguageModel
from .services.reranking import CrossEncoderReranker
from .services.retrieval import CacheError, RetrievalError, RetrievalService
from .store import store

settings = get_settings()
logger = logging.getLogger(__name__)
app = FastAPI(title="Code Atlas API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_methods=["*"], allow_headers=["*"])
evaluation_worker = build_evaluation_service(settings, store)


@app.on_event("startup")
async def hydrate_repository_registry() -> None:
    try:
        await store.hydrate_repositories()
    except PersistenceError:
        # Keep the existing in-memory development fallback if Supabase is temporarily unavailable.
        # A later restart retries hydration; no repository state is fabricated here.
        logger.warning("Repository registry hydration failed; continuing with an empty in-memory registry.")
        return


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/repositories", response_model=Repository, status_code=202)
async def create_repository(request: IngestRequest, background_tasks: BackgroundTasks) -> Repository:
    repository_url = canonical_repository_identity(request.repository_url)
    repository = Repository(
        name=request.name or repository_url.rstrip("/").split("/")[-1],
        owner=request.username,
        branch=request.branch,
        url=repository_url,
        repository_key=repository_url,
    )
    repository, should_ingest = await store.get_or_create_repository(repository)
    if should_ingest:
        background_tasks.add_task(run_ingestion, repository, request.branch, store, settings, evaluation=evaluation_worker)
    return repository


@app.get("/api/repositories", response_model=list[Repository])
async def list_repositories() -> list[Repository]:
    return await store.list_repositories()


@app.get("/api/repositories/{repository_id}", response_model=Repository)
async def get_repository(repository_id: UUID) -> Repository:
    repository = await store.get_repository(repository_id)
    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repository


@app.get("/api/repositories/{repository_id}/tree", response_model=FileTreeResponse)
async def get_tree(repository_id: UUID) -> FileTreeResponse:
    if await store.get_repository(repository_id) is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    files = await store.get_files(repository_id)
    nodes: dict[str, FileNode] = {}
    for file_path, content in files.items():
        parts = Path(file_path).parts
        for index, part in enumerate(parts):
            path = "/".join(parts[: index + 1])
            if path not in nodes:
                is_file = index == len(parts) - 1
                nodes[path] = FileNode(name=part, path=path, type="file" if is_file else "directory", size=len(content.encode()) if is_file else None)
    children: dict[str, list[FileNode]] = {}
    for path, node in nodes.items():
        parent = "/".join(path.split("/")[:-1])
        children.setdefault(parent, []).append(node)
    for parent, child_nodes in children.items():
        if parent in nodes:
            nodes[parent].children = sorted(child_nodes, key=lambda child: (child.type == "file", child.name.lower()))
    return FileTreeResponse(tree=sorted(children.get("", []), key=lambda child: (child.type == "file", child.name.lower())))


@app.get("/api/repositories/{repository_id}/files/{file_path:path}", response_model=FileContentResponse)
async def get_file(repository_id: UUID, file_path: str) -> FileContentResponse:
    if await store.get_repository(repository_id) is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    content = (await store.get_files(repository_id)).get(file_path)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found")
    suffix = Path(file_path).suffix.lower().removeprefix(".") or "text"
    return FileContentResponse(content=content, language=suffix, size=len(content.encode()))


@app.post("/api/repositories/{repository_id}/retrieve")
async def retrieve_repository(repository_id: UUID, payload: dict[str, str]) -> dict[str, object]:
    if await store.get_repository(repository_id) is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    query = payload.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=422, detail="Query is required")
    service = RetrievalService(
        store,
        GeminiEmbeddingService(settings),
        CrossEncoderReranker(settings.reranker_model),
    )
    try:
        result = await service.retrieve(repository_id, query)
    except (CacheError, RetrievalError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    await store.log_event(repository_id, "retrieval", "info", "Repository retrieval completed", {"cache_hit": result["cache_hit"], "final_count": len(result["results"])}, result["latency_ms"].get("total"))
    return result


@app.get("/api/chat/sessions", response_model=list[ChatSession])
async def list_sessions(repositoryId: UUID = Query(...)) -> list[ChatSession]:
    if await store.get_repository(repositoryId) is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return await store.get_sessions(repositoryId)


@app.post("/api/chat/sessions", response_model=ChatSession)
async def create_session(repositoryId: UUID) -> ChatSession:
    if await store.get_repository(repositoryId) is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return await store.save_session(ChatSession(repository_id=repositoryId))


@app.get("/api/chat/sessions/{session_id}/messages", response_model=list[ChatMessage])
async def get_messages(session_id: UUID) -> list[ChatMessage]:
    return await store.get_messages(session_id)


@app.post("/api/chat/sessions/{session_id}/messages", response_model=ChatMessage)
async def send_message(session_id: UUID, payload: dict[str, str]) -> ChatMessage:
    session = await store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    content = payload.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=422, detail="Message content is required")
    if await store.get_repository(session.repository_id) is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    await store.add_message(ChatMessage(role="user", content=content), session_id)

    async def log_generation_event(stage: str, level: str, metadata: dict[str, object]) -> None:
        await store.log_event(session.repository_id, stage, level, "Generation pipeline event", metadata)

    service = GenerationService(
        retrieval=RetrievalService(store, GeminiEmbeddingService(settings), CrossEncoderReranker(settings.reranker_model)),
        memory=ConversationMemory(
            store,
            ProviderChainLanguageModel(provider_chain=build_memory_provider_chain(settings)),
            settings.memory_context_budget,
            message_to_token_ids=lambda text: list(range(max(1, len(text.split())))),
        ),
        providers=build_provider_chain(settings, on_event=log_generation_event),
        on_event=log_generation_event,
    )
    try:
        generated = await service.answer(session.repository_id, session_id, content)
    except GenerationProviderError as exc:
        await store.log_event(session.repository_id, "generation_failed", "error", "Generation failed", {"error": str(exc)})
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    response = ChatMessage(
        role="assistant",
        content=generated.content,
        citations=[
            {
                "file": citation.filepath,
                "line_start": citation.start_line,
                "line_end": citation.end_line,
                "symbol": citation.symbol,
                "chunk_id": citation.chunk_id,
            }
            for citation in generated.citations
        ],
    )
    return await store.add_message(response, session_id)


@app.delete("/api/chat/sessions")
async def delete_sessions(repositoryId: UUID = Query(...)) -> dict[str, bool]:
    if await store.get_repository(repositoryId) is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    await store.delete_sessions(repositoryId)
    return {"deleted": True}
