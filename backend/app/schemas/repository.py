from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, model_validator


class IngestionStatus(str, Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    FILTERING = "filtering"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class Contributor(BaseModel):
    username: str
    contributions: int = 0
    commits: int = 0
    avatar_url: str | None = None

    @model_validator(mode="before")
    @classmethod
    def sync_commits(cls, data: Any) -> Any:
        if isinstance(data, dict):
            c = data.get("commits") if data.get("commits") is not None else data.get("contributions", 0)
            data["commits"] = c
            data["contributions"] = c
        return data


class ProcessingStats(BaseModel):
    files_total: int = 0
    chunks_created: int = 0
    embeddings_generated: int = 0
    duration_ms: float = 0.0
    last_indexed_at: str | None = None


class IngestRequest(BaseModel):
    repository_url: str
    branch: str | None = None


class Repository(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    url: str
    status: IngestionStatus = IngestionStatus.QUEUED
    owner: str | None = None
    full_name: str | None = None
    description: str | None = None
    branch: str | None = None
    default_branch: str | None = None
    language: str | None = None
    primary_language: str | None = None
    error: str | None = None
    files: int = 0
    folders: int = 0
    contributors: list[Contributor] = Field(default_factory=list)
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    size_kb: int | None = None
    visibility: str | None = None
    topics: list[str] = Field(default_factory=list)
    languages: dict[str, int] = Field(default_factory=dict)
    metadata_ready: bool = False
    files_ready: bool = False
    processing: ProcessingStats = Field(default_factory=ProcessingStats)
    repository_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
