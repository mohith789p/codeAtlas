import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.database.connection import get_db_connection
from app.shared.config import get_settings
from app.shared.logging import get_logger
from app.shared.observability import flush_langsmith_traces, setup_langsmith_environment

settings = get_settings()
logger = get_logger("codeatlas.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan setup and graceful shutdown."""
    setup_langsmith_environment(settings)
    logger.info("CodeAtlas Engine started.")
    yield
    # Graceful teardown
    conn = get_db_connection()
    await conn.aclose()
    flush_langsmith_traces()
    logger.info("CodeAtlas Engine shutdown complete.")


app = FastAPI(
    title="CodeAtlas API",
    version="1.0.0",
    description="Intelligent code retrieval and citation-grounded generation engine.",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Mask internal errors and log redacted diagnostics."""
    logger.exception("Unhandled server exception processing %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred. Please try again later."},
    )


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint for liveness and readiness probes."""
    return {"status": "ok", "version": "1.0.0"}


# Register aggregated API router
app.include_router(api_router)
