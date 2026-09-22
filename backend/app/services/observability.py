import logging
import os
from collections.abc import Callable
from functools import wraps
from typing import Any

from langchain_core.runnables import RunnableConfig, chain
try:
    from langchain_core.tracers.langchain import wait_for_all_tracers
except ImportError:
    try:
        from langchain_core.tracers.context import wait_for_all_tracers
    except ImportError:
        def wait_for_all_tracers() -> None:
            pass

from ..config import Settings, get_settings
from ..logging_utils import redact_sensitive

logger = logging.getLogger(__name__)


def setup_langsmith_environment(settings: Settings | None = None) -> bool:
    """Initialize LangSmith tracing environment variables if enabled.
    
    This only configures the global connection endpoints and project defaults;
    request-level metadata and tags are isolated per-request via RunnableConfig.
    """
    active_settings = settings or get_settings()
    if not active_settings.is_langsmith_enabled:
        return False

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_TRACING"] = "true"
    if active_settings.langsmith_api_key:
        os.environ["LANGCHAIN_API_KEY"] = active_settings.langsmith_api_key
        os.environ["LANGSMITH_API_KEY"] = active_settings.langsmith_api_key
    if active_settings.langsmith_project:
        os.environ["LANGCHAIN_PROJECT"] = active_settings.langsmith_project
        os.environ["LANGSMITH_PROJECT"] = active_settings.langsmith_project
    if active_settings.langsmith_endpoint:
        os.environ["LANGCHAIN_ENDPOINT"] = active_settings.langsmith_endpoint
        os.environ["LANGSMITH_ENDPOINT"] = active_settings.langsmith_endpoint

    logger.info("LangSmith tracing initialized for project '%s'", active_settings.langsmith_project)
    return True


def create_runnable_config(
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    project_name: str | None = None,
    settings: Settings | None = None,
) -> RunnableConfig:
    """Create an isolated, request-scoped RunnableConfig.
    
    This ensures request-level metadata (such as repo_id, session_id) does not leak
    across concurrent FastAPI requests and avoids global os.environ mutations.
    """
    active_settings = settings or get_settings()
    safe_metadata = redact_sensitive(metadata or {})
    all_tags = list(tags or [])
    if active_settings.langsmith_environment:
        all_tags.append(f"env:{active_settings.langsmith_environment}")

    config: RunnableConfig = {
        "tags": all_tags,
        "metadata": safe_metadata,
        "callbacks": [],
    }

    if active_settings.is_langsmith_enabled:
        try:
            from langchain_core.tracers import LangChainTracer

            project = project_name or active_settings.langsmith_project
            tracer = LangChainTracer(project_name=project)
            config["callbacks"] = [tracer]
        except Exception as exc:
            logger.debug("Failed to instantiate LangChainTracer: %s", exc)

    return config


def flush_langsmith_traces() -> None:
    """Flush all pending queued spans before shutdown to prevent dropped traces."""
    try:
        wait_for_all_tracers()
        logger.info("LangSmith traces flushed successfully.")
    except Exception as exc:
        logger.warning("Error while waiting for LangSmith tracers on shutdown: %s", exc)


def safe_traceable(
    name: str | None = None,
    run_type: str = "chain",
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Safe traceable decorator for standalone background tasks (e.g. ingestion, evaluation).
    
    For functions inside LangChain chains, use @chain instead to preserve RunnableConfig
    and avoid trace tree disconnection.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        settings = get_settings()
        if not settings.is_langsmith_enabled:
            return func

        try:
            from langsmith import traceable

            return traceable(
                name=name or func.__name__,
                run_type=run_type,
                tags=tags,
                metadata=redact_sensitive(metadata or {}),
            )(func)
        except Exception as exc:
            logger.debug("LangSmith traceable decoration skipped for %s: %s", func.__name__, exc)
            return func

    return decorator


__all__ = [
    "setup_langsmith_environment",
    "create_runnable_config",
    "flush_langsmith_traces",
    "safe_traceable",
    "chain",
]
