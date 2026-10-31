from fastapi import APIRouter
from app.api.routes.chat import router as chat_router
from app.api.routes.files import router as files_router
from app.api.routes.queries import router as queries_router
from app.api.routes.repositories import router as repositories_router

api_router = APIRouter(prefix="/api")
api_router.include_router(repositories_router)
api_router.include_router(files_router)
api_router.include_router(queries_router)
api_router.include_router(chat_router)
