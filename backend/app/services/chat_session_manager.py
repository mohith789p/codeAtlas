import hashlib
import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.database.chat_repository import ChatDatabaseRepository
from app.schemas.chat import ChatMessage, ChatSession

logger = logging.getLogger(__name__)


def safe_uuid(val: str) -> UUID:
    try:
        return UUID(val)
    except Exception:
        return UUID(hashlib.md5(val.encode("utf-8")).hexdigest())


class ChatSessionManager:
    """Manages chat session lifecycles and message histories with database persistence."""

    def __init__(self, chat_db: ChatDatabaseRepository | None = None) -> None:
        self.db = chat_db or ChatDatabaseRepository()
        self._sessions: dict[str, ChatSession] = {}
        self._repo_sessions: dict[str, list[str]] = {}
        self._messages: dict[str, list[ChatMessage]] = {}

    async def get_or_create_session(self, repo_id: str) -> ChatSession:
        sessions = await self.list_sessions(repo_id)
        return sessions[-1] if sessions else await self.create_session(repo_id)

    async def create_session(self, repo_id: str) -> ChatSession:
        session_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        session = ChatSession(id=session_id, repository_id=repo_id, created_at=now, updated_at=now)
        self._sessions[session_id] = session
        self._repo_sessions.setdefault(repo_id, []).append(session_id)
        self._messages[session_id] = []
        try:
            await self.db.create_session(safe_uuid(session_id), safe_uuid(repo_id), now)
        except Exception as exc:
            logger.warning("Database chat session write failed, falling back to memory: %s", exc)
        return session

    async def list_sessions(self, repo_id: str) -> list[ChatSession]:
        try:
            rows = await self.db.list_sessions(safe_uuid(repo_id))
            if rows:
                db_sessions = [
                    ChatSession(id=str(r["id"]), repository_id=str(r["repository_id"]), created_at=str(r["created_at"]), updated_at=str(r.get("updated_at") or r["created_at"]))
                    for r in rows
                ]
                for s in db_sessions:
                    self._sessions[s.id] = s
                    if s.id not in self._repo_sessions.get(repo_id, []):
                        self._repo_sessions.setdefault(repo_id, []).append(s.id)
                return db_sessions
        except Exception as exc:
            logger.warning("Database chat session read failed, falling back to memory: %s", exc)
        return [self._sessions[sid] for sid in self._repo_sessions.get(repo_id, []) if sid in self._sessions]

    async def get_messages(self, session_id: str) -> list[ChatMessage]:
        try:
            rows = await self.db.get_messages(safe_uuid(session_id))
            if rows:
                db_msgs = [
                    ChatMessage(id=str(r["id"]), role=r["role"], content=r["content"], citations=r.get("citations") or [], created_at=str(r["created_at"]))
                    for r in rows
                ]
                self._messages[session_id] = db_msgs
                return db_msgs
        except Exception as exc:
            logger.warning("Database chat messages read failed, falling back to memory: %s", exc)
        return self._messages.get(session_id, [])

    async def delete_sessions(self, repo_id: str) -> None:
        try:
            await self.db.delete_sessions(safe_uuid(repo_id))
        except Exception as exc:
            logger.warning("Database chat delete failed, falling back to memory: %s", exc)
        for sid in self._repo_sessions.pop(repo_id, []):
            self._sessions.pop(sid, None)
            self._messages.pop(sid, None)

    async def append_message(self, session_id: str, message: ChatMessage) -> None:
        self._messages.setdefault(session_id, []).append(message)
        if session_id in self._sessions:
            self._sessions[session_id].updated_at = datetime.now(timezone.utc).isoformat()
        try:
            payload = {
                "id": str(safe_uuid(message.id)),
                "session_id": str(safe_uuid(session_id)),
                "role": message.role,
                "content": message.content,
                "citations": [c.model_dump() if hasattr(c, "model_dump") else c for c in message.citations],
                "created_at": message.created_at,
            }
            await self.db.insert_message(payload)
        except Exception as exc:
            logger.warning("Database chat message insert failed, falling back to memory: %s", exc)
