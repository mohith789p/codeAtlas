import functools
import inspect
import logging
import os
from collections.abc import Callable
from typing import Any

from app.shared.config import Settings, get_settings
from app.shared.logging import redact_sensitive

logger = logging.getLogger(__name__)


def setup_langsmith_environment(settings: Settings | None = None) -> bool:
    """Initialize LangSmith environment variables if enabled."""
    cfg = settings or get_settings()
    if not cfg.is_langsmith_enabled:
        return False
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_TRACING"] = "true"
    if cfg.langsmith_api_key:
        os.environ["LANGCHAIN_API_KEY"] = cfg.langsmith_api_key
        os.environ["LANGSMITH_API_KEY"] = cfg.langsmith_api_key
    if cfg.langsmith_project:
        os.environ["LANGCHAIN_PROJECT"] = cfg.langsmith_project
        os.environ["LANGSMITH_PROJECT"] = cfg.langsmith_project
    if cfg.langsmith_endpoint:
        os.environ["LANGCHAIN_ENDPOINT"] = cfg.langsmith_endpoint
        os.environ["LANGSMITH_ENDPOINT"] = cfg.langsmith_endpoint
    logger.info("LangSmith tracing enabled for project '%s'", cfg.langsmith_project)
    return True


def create_runnable_config(
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Build LangSmith runnable configuration with redacted metadata."""
    cfg = settings or get_settings()
    safe_meta = redact_sensitive(metadata or {})
    all_tags = list(tags or [])
    if cfg.langsmith_environment:
        all_tags.append(f"env:{cfg.langsmith_environment}")
    config: dict[str, Any] = {"tags": all_tags, "metadata": safe_meta, "callbacks": []}
    if cfg.is_langsmith_enabled:
        try:
            from langchain_core.tracers import LangChainTracer
            config["callbacks"] = [LangChainTracer(project_name=cfg.langsmith_project)]
        except Exception as exc:
            logger.debug("Failed to instantiate LangChainTracer: %s", exc)
    return config


def safe_traceable(name: str, run_type: str = "chain", tags: list[str] | None = None) -> Callable:
    """Safe wrapper for tracing execution without failing if LangSmith is inactive."""
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await fn(*args, **kwargs)
        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return fn(*args, **kwargs)
        return async_wrapper if inspect.iscoroutinefunction(fn) else sync_wrapper
    return decorator


def flush_langsmith_traces() -> None:
    """Flush pending LangSmith traces on shutdown."""
    try:
        from langchain_core.tracers.langchain import wait_for_all_tracers
        wait_for_all_tracers()
    except Exception as exc:
        logger.debug("LangSmith tracer flush skipped or failed: %s", exc)
