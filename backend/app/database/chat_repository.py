from typing import Any
from uuid import UUID

from app.database.connection import DatabaseConnection, get_db_connection


class ChatDatabaseRepository:
    """PostgREST data access layer for persistent chat sessions and messages."""

    def __init__(self, connection: DatabaseConnection | None = None) -> None:
        self.conn = connection or get_db_connection()

    async def create_session(self, session_id: UUID, repo_id: UUID, created_at: str) -> None:
        payload = [{
            "id": str(session_id),
            "repository_id": str(repo_id),
            "created_at": created_at,
            "updated_at": created_at,
        }]
        headers = {"Prefer": "resolution=merge-duplicates"}
        await self.conn.execute("POST", "chat_sessions?on_conflict=id", json=payload, headers=headers)

    async def list_sessions(self, repo_id: UUID) -> list[dict[str, Any]]:
        return await self.conn.execute("GET", f"chat_sessions?repository_id=eq.{repo_id}&order=created_at.asc") or []

    async def get_messages(self, session_id: UUID) -> list[dict[str, Any]]:
        return await self.conn.execute("GET", f"chat_messages?session_id=eq.{session_id}&order=created_at.asc") or []

    async def insert_message(self, message_payload: dict[str, Any]) -> None:
        headers = {"Prefer": "resolution=merge-duplicates"}
        await self.conn.execute("POST", "chat_messages?on_conflict=id", json=[message_payload], headers=headers)

    async def delete_sessions(self, repo_id: UUID) -> None:
        await self.conn.execute("DELETE", f"chat_sessions?repository_id=eq.{repo_id}")
