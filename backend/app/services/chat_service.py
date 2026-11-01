import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator
from uuid import UUID, uuid4

from app.schemas.chat import ChatMessage, ChatSession
from app.services.chat_session_manager import ChatSessionManager
from app.services.query_service import QueryService

logger = logging.getLogger(__name__)

EMPTY_REPO_RESPONSE = (
    "This question does not appear to be related to the repository codebase, "
    "or no relevant code could be retrieved."
)


class ChatService:
    """Manages conversational query retrieval, token streaming, and citation validation."""

    def __init__(
        self,
        query_service: QueryService | None = None,
        session_manager: ChatSessionManager | None = None,
    ) -> None:
        self.query_service = query_service or QueryService()
        self.sessions = session_manager or ChatSessionManager()

    async def create_session(self, repo_id: str) -> ChatSession:
        return await self.sessions.create_session(repo_id)

    async def list_sessions(self, repo_id: str) -> list[ChatSession]:
        return await self.sessions.list_sessions(repo_id)

    async def get_messages(self, session_id: str) -> list[ChatMessage]:
        return await self.sessions.get_messages(session_id)

    async def delete_sessions(self, repo_id: str) -> None:
        await self.sessions.delete_sessions(repo_id)

    async def stream_answer(
        self,
        repo_id: str,
        query: str,
        session_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream retrieved repository code answers token-by-token via SSE."""
        now = datetime.now(timezone.utc).isoformat()
        if session_id:
            await self.sessions.append_message(
                session_id,
                ChatMessage(id=f"msg-{uuid4().hex[:8]}", role="user", content=query, created_at=now),
                repo_id=repo_id,
            )

        try:
            repo_uuid = UUID(str(repo_id))
        except (ValueError, TypeError, AttributeError):
            repo_uuid = uuid4()

        try:
            await self.query_service.repo_service.assert_ready(repo_uuid)
            clean_query, query_emb = await self.query_service.preprocessor.preprocess(query)
            dense_res, sparse_res = await self.query_service.retriever.retrieve(repo_uuid, clean_query, query_emb, limit=20)
            fused = self.query_service.fusion.fuse(dense_res, sparse_res, top_k=20)
            top_chunks = self.query_service.reranker.rerank(clean_query, fused, top_k=5)

            if not top_chunks:
                yield f"data: {json.dumps({'type': 'token', 'content': EMPTY_REPO_RESPONSE})}\n\n"
                empty_msg = ChatMessage(id=f"msg-{uuid4().hex[:8]}", role="assistant", content=EMPTY_REPO_RESPONSE, citations=[], created_at=datetime.now(timezone.utc).isoformat())
                if session_id:
                    await self.sessions.append_message(session_id, empty_msg, repo_id=repo_id)
                yield f"data: {json.dumps({'type': 'done', 'message': empty_msg.model_dump()})}\n\n"
                return

            sys_prompt, user_prompt = self.query_service.generator.prompt_builder.build_prompt(clean_query, top_chunks)
            accumulated_text = ""
            async for token in self.query_service.generator.llm_client.stream_generate(sys_prompt, user_prompt):
                accumulated_text += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            citations = self.query_service.validator.validate_citations(accumulated_text, top_chunks)
            assistant_msg = ChatMessage(id=f"msg-{uuid4().hex[:8]}", role="assistant", content=accumulated_text, citations=citations, created_at=datetime.now(timezone.utc).isoformat())
            if session_id:
                await self.sessions.append_message(session_id, assistant_msg, repo_id=repo_id)
            yield f"data: {json.dumps({'type': 'done', 'message': assistant_msg.model_dump()})}\n\n"

        except Exception as exc:
            logger.exception("Error in stream_answer: %s", exc)
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"
            err_msg = ChatMessage(id=f"msg-{uuid4().hex[:8]}", role="assistant", content=f"Error: {exc}", citations=[], created_at=datetime.now(timezone.utc).isoformat())
            if session_id:
                await self.sessions.append_message(session_id, err_msg, repo_id=repo_id)
            yield f"data: {json.dumps({'type': 'done', 'message': err_msg.model_dump()})}\n\n"
