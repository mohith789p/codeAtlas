from functools import lru_cache
from fastapi import Depends

from app.database.connection import DatabaseConnection, get_db_connection
from app.database.repositories import DatabaseRepository
from app.services.chat_service import ChatService
from app.services.file_service import FileService
from app.services.ingestion_service import IngestionService
from app.services.query_service import QueryService
from app.services.repository_service import RepositoryService

_chat_service: ChatService | None = None


def get_db_repo(conn: DatabaseConnection = Depends(get_db_connection)) -> DatabaseRepository:
    return DatabaseRepository(connection=conn)


def get_repository_service(db: DatabaseRepository = Depends(get_db_repo)) -> RepositoryService:
    return RepositoryService(db_repo=db)


def get_file_service(db: DatabaseRepository = Depends(get_db_repo)) -> FileService:
    return FileService(db_repo=db)


def get_ingestion_service(db: DatabaseRepository = Depends(get_db_repo)) -> IngestionService:
    return IngestionService(db_repo=db)


def get_query_service(repo_svc: RepositoryService = Depends(get_repository_service)) -> QueryService:
    return QueryService(repo_service=repo_svc)


def get_chat_service(query_svc: QueryService = Depends(get_query_service)) -> ChatService:
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService(query_service=query_svc)
    else:
        _chat_service.query_service = query_svc
    return _chat_service
