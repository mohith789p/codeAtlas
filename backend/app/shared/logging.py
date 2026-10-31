import logging
import re
from typing import Any

_SECRET_QUERY_PATTERN = re.compile(
    r"([?&](?:api[_-]?key|key|token|access[_-]?token|authorization|secret)=)[^&\s\"']+",
    re.IGNORECASE,
)
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"((?:api[_-]?key|access[_-]?token|authorization|secret)\s*[:=]\s*)[^\s,;\"']+",
    re.IGNORECASE,
)
_BEARER_PATTERN = re.compile(r"(\bBearer\s+)[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_SENSITIVE_KEY_PATTERN = re.compile(
    r"(?:api[_-]?key|secret|token|access[_-]?token|authorization|password|auth)",
    re.IGNORECASE,
)


def redact_sensitive_text(value: str) -> str:
    """Mask credentials and API tokens from log text."""
    value = _BEARER_PATTERN.sub(r"\1[REDACTED]", value)
    value = _SECRET_QUERY_PATTERN.sub(r"\1[REDACTED]", value)
    value = _SECRET_ASSIGNMENT_PATTERN.sub(r"\1[REDACTED]", value)
    return value


def redact_sensitive(value: Any) -> Any:
    """Recursively mask sensitive values in dicts, lists, and strings."""
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if isinstance(value, dict):
        result = {}
        for k, v in value.items():
            if isinstance(k, str) and _SENSITIVE_KEY_PATTERN.search(k):
                result[k] = "[REDACTED]"
            else:
                result[k] = redact_sensitive(v)
        return result
    if isinstance(value, list):
        return [redact_sensitive(v) for v in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive(v) for v in value)
    return value


class RedactingFormatter(logging.Formatter):
    """Logging formatter that redacts secrets from emitted log records."""

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        return redact_sensitive_text(original)


def get_logger(name: str) -> logging.Logger:
    """Return a logger instance with secret redaction support."""
    logger = logging.getLogger(name)
    if not logger.handlers and not logging.getLogger().handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(RedactingFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
