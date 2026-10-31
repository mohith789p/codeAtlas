from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass
class RepoRow:
    id: UUID
    name: str
    url: str
    status: str
    owner: str | None = None
    full_name: str | None = None
    description: str | None = None
    branch: str | None = None
    language: str | None = None
    error: str | None = None
    files: int = 0
    folders: int = 0
    contributors: int = 0
    size_kb: int | None = None
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    metadata_ready: bool = False
    files_ready: bool = False
    contributor_details: list[dict[str, Any]] = field(default_factory=list)
    repository_metadata: dict[str, Any] = field(default_factory=dict)
    processing_stats: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class ChunkRow:
    id: UUID
    repo_id: UUID
    content_hash: str
    content: str
    embedding: list[float]
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class ChunkMetadataRow:
    chunk_id: UUID
    filepath: str
    language: str | None = None
    symbol: str | None = None
    symbol_type: str | None = None
    class_name: str | None = None
    parent_symbol: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    imports: list[str] = field(default_factory=list)


@dataclass
class SemanticCacheRow:
    id: UUID
    repo_id: UUID
    query_hash: str
    query_text: str
    query_embedding: list[float]
    response: dict[str, Any]
    created_at: datetime | None = None
    updated_at: datetime | None = None


def parse_embedding(raw: Any) -> list[float]:
    """Parse raw database vector embedding (string, list, or array)."""
    try:
        if isinstance(raw, list):
            return [float(x) for x in raw]
        if isinstance(raw, str):
            cleaned = raw.strip("[]() ")
            return [float(x.strip()) for x in cleaned.split(",") if x.strip()]
    except (ValueError, TypeError):
        return []
    return []
