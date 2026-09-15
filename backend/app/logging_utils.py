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


def redact_sensitive_text(value: str) -> str:
    value = _BEARER_PATTERN.sub(r"\1[REDACTED]", value)
    value = _SECRET_QUERY_PATTERN.sub(r"\1[REDACTED]", value)
    value = _SECRET_ASSIGNMENT_PATTERN.sub(r"\1[REDACTED]", value)
    return value


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if isinstance(value, dict):
        return {key: redact_sensitive(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive(item) for item in value)
    return value
