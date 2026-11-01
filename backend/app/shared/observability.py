import functools
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
    project = (cfg.langsmith_project or "codeatlas").strip(' "\'')
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_TRACING"] = "true"
    if cfg.langsmith_api_key:
        key = cfg.langsmith_api_key.strip(' "\'')
        os.environ["LANGCHAIN_API_KEY"] = key
        os.environ["LANGSMITH_API_KEY"] = key
    os.environ["LANGCHAIN_PROJECT"] = project
    os.environ["LANGSMITH_PROJECT"] = project
    if cfg.langsmith_endpoint:
        os.environ["LANGCHAIN_ENDPOINT"] = cfg.langsmith_endpoint
        os.environ["LANGSMITH_ENDPOINT"] = cfg.langsmith_endpoint
    logger.info("LangSmith tracing enabled for project '%s'", project)
    return True


def create_runnable_config(tags: list[str] | None = None, metadata: dict[str, Any] | None = None, settings: Settings | None = None) -> dict[str, Any]:
    cfg = settings or get_settings()
    all_tags = list(tags or [])
    if cfg.langsmith_environment:
        all_tags.append(f"env:{cfg.langsmith_environment}")
    config: dict[str, Any] = {"tags": all_tags, "metadata": redact_sensitive(metadata or {}), "callbacks": []}
    if cfg.is_langsmith_enabled:
        try:
            from langchain_core.tracers import LangChainTracer
            config["callbacks"] = [LangChainTracer(project_name=(cfg.langsmith_project or "codeatlas").strip(' "\''))]
        except Exception as exc:
            logger.debug("Failed to instantiate LangChainTracer: %s", exc)
    return config


def safe_traceable(name: str, run_type: str = "chain", tags: list[str] | None = None) -> Callable:
    """Real LangSmith traceable wrapper that gracefully falls back if LangSmith is disabled."""
    def decorator(fn: Callable) -> Callable:
        cfg = get_settings()
        if not cfg.is_langsmith_enabled:
            return fn
        try:
            from langsmith import traceable
            project = (cfg.langsmith_project or "codeatlas").strip(' "\'')
            return traceable(name=name, run_type=run_type, tags=tags, project_name=project)(fn)
        except Exception as exc:
            logger.debug("LangSmith traceable disabled for %s: %s", name, exc)
            return fn
    return decorator


def flush_langsmith_traces() -> None:
    """Flush pending LangSmith traces on shutdown."""
    try:
        from langchain_core.tracers.langchain import wait_for_all_tracers
        wait_for_all_tracers()
    except Exception as exc:
        logger.debug("LangSmith tracer flush skipped or failed: %s", exc)
