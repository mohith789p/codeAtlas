from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def canonical_repository_identity(url: str) -> str:
    parsed = urlsplit(url.strip())
    host = (parsed.hostname or "").lower()
    parts = [part for part in parsed.path.split("/") if part]
    if host in {"github.com", "www.github.com"} and len(parts) >= 2:
        owner = parts[0].lower()
        name = parts[1].removesuffix(".git").lower()
        return f"https://github.com/{owner}/{name}"
    return url.strip().rstrip("/")


class IngestionStatus(StrEnum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    FILTERING = "filtering"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class RepositoryStats(BaseModel):
    files: int = 0
    folders: int = 0
    contributors: int = 0
    size_kb: int | None = None
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    open_pull_requests: int | None = None


class Contributor(BaseModel):
    username: str
    avatar_url: str | None = None
    commits: int | None = None


class RepositoryMetadata(BaseModel):
    visibility: str | None = None
    github_created_at: datetime | None = None
    github_updated_at: datetime | None = None
    pushed_at: datetime | None = None
    languages: dict[str, float] = Field(default_factory=dict)
    topics: list[str] = Field(default_factory=list)
    license_name: str | None = None


class ProcessingStats(BaseModel):
    chunks_created: int | None = None
    embeddings_generated: int | None = None
    duration_ms: float | None = None
    last_indexed_at: datetime | None = None


class Repository(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    full_name: str | None = None
    description: str | None = None
    owner: str | None = None
    branch: str | None = None
    language: str | None = None
    url: str
    repository_key: str | None = Field(default=None, exclude=True)
    stats: RepositoryStats = Field(default_factory=RepositoryStats)
    contributors: list[Contributor] = Field(default_factory=list)
    repository_metadata: RepositoryMetadata = Field(default_factory=RepositoryMetadata)
    processing: ProcessingStats = Field(default_factory=ProcessingStats)
    metadata_ready: bool = False
    files_ready: bool = False
    status: IngestionStatus = IngestionStatus.QUEUED
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class IngestRequest(BaseModel):
    mode: str = "url"
    url: HttpUrl | None = None
    username: str | None = None
    name: str | None = None
    branch: str | None = None

    @model_validator(mode="after")
    def validate_source(self) -> "IngestRequest":
        if self.mode == "url" and self.url is None:
            raise ValueError("url is required when mode is 'url'")
        if self.mode == "manual" and (not self.username or not self.name):
            raise ValueError("username and name are required when mode is 'manual'")
        if self.mode not in {"url", "manual"}:
            raise ValueError("mode must be 'url' or 'manual'")
        return self

    @property
    def repository_url(self) -> str:
        if self.mode == "manual":
            return f"https://github.com/{self.username}/{self.name}"
        return str(self.url).removesuffix("/")


class FileNode(BaseModel):
    name: str
    path: str
    type: str
    children: list["FileNode"] | None = None
    size: int | None = None


class FileTreeResponse(BaseModel):
    tree: list[FileNode]


class FileContentResponse(BaseModel):
    content: str
    language: str
    size: int
    encoding: str = "utf-8"


class ChatSession(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    repository_id: UUID
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ChatMessage(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    role: str
    content: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
