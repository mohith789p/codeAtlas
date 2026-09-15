from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse
from zipfile import BadZipFile, ZipFile

import httpx

from ..config import Settings
from ..models import Contributor


class GitHubRepositoryError(ValueError):
    pass


@dataclass(frozen=True)
class GitHubRepository:
    owner: str
    name: str
    url: str
    default_branch: str
    size_kb: int
    description: str | None
    language: str | None
    contributors: list[Contributor] = field(default_factory=list)
    visibility: str | None = None
    github_created_at: str | None = None
    github_updated_at: str | None = None
    pushed_at: str | None = None
    languages: dict[str, float] = field(default_factory=dict)
    topics: list[str] = field(default_factory=list)
    license_name: str | None = None
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    open_pull_requests: int | None = None


def parse_repository_url(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        raise GitHubRepositoryError("Only public GitHub repository URLs are supported.")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise GitHubRepositoryError("GitHub URL must include an owner and repository name.")
    return parts[0], parts[1].removesuffix(".git")


async def inspect_repository(url: str, settings: Settings) -> GitHubRepository:
    owner, name = parse_repository_url(url)
    endpoint = f"{settings.github_api_url}/repos/{owner}/{name}"
    timeout = httpx.Timeout(settings.download_read_timeout_seconds, connect=settings.download_connect_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(endpoint, headers={"Accept": "application/vnd.github+json"})
        if response.status_code == 404:
            raise GitHubRepositoryError("GitHub repository was not found or is not public.")
        response.raise_for_status()
        repository_payload = response.json()
        size_kb = int(repository_payload.get("size", 0))
        if size_kb > settings.max_repository_size_kb:
            raise GitHubRepositoryError(
                f"Repository is {size_kb} KB, above the configured {settings.max_repository_size_kb} KB limit."
            )
        contributors: list[Contributor] = []
        try:
            contributors_response = await client.get(
                f"{endpoint}/contributors",
                params={"per_page": 100},
                headers={"Accept": "application/vnd.github+json"},
            )
            if contributors_response.is_success:
                contributors_payload = contributors_response.json()
                if isinstance(contributors_payload, list):
                    contributors = [
                        Contributor(
                            username=str(item["login"]),
                            avatar_url=item.get("avatar_url"),
                            commits=item.get("contributions"),
                        )
                        for item in contributors_payload
                        if isinstance(item, dict) and item.get("login")
                    ]
        except (httpx.HTTPError, TypeError, ValueError, KeyError):
            # Contributor data is optional; repository ingestion should still succeed.
            contributors = []

        languages: dict[str, float] = {}
        try:
            languages_response = await client.get(
                f"{endpoint}/languages",
                headers={"Accept": "application/vnd.github+json"},
            )
            if languages_response.is_success:
                language_bytes = languages_response.json()
                if isinstance(language_bytes, dict):
                    numeric_languages = {
                        str(language): float(byte_count)
                        for language, byte_count in language_bytes.items()
                        if isinstance(byte_count, (int, float)) and byte_count >= 0
                    }
                    total_bytes = sum(numeric_languages.values())
                    if total_bytes:
                        languages = {
                            language: round(byte_count / total_bytes * 100, 1)
                            for language, byte_count in numeric_languages.items()
                        }
        except (httpx.HTTPError, TypeError, ValueError):
            languages = {}

        open_pull_requests: int | None = None
        try:
            pulls_response = await client.get(
                f"{settings.github_api_url}/search/issues",
                params={"q": f"repo:{owner}/{name} is:pr is:open", "per_page": 1},
                headers={"Accept": "application/vnd.github+json"},
            )
            if pulls_response.is_success:
                search_payload = pulls_response.json()
                if isinstance(search_payload, dict) and isinstance(search_payload.get("total_count"), int):
                    open_pull_requests = search_payload["total_count"]
        except (httpx.HTTPError, TypeError, ValueError):
            open_pull_requests = None

    return GitHubRepository(
        owner=owner,
        name=name,
        url=f"https://github.com/{owner}/{name}",
        default_branch=repository_payload.get("default_branch") or "main",
        size_kb=size_kb,
        description=repository_payload.get("description"),
        language=repository_payload.get("language"),
        contributors=contributors,
        visibility=repository_payload.get("visibility"),
        github_created_at=repository_payload.get("created_at"),
        github_updated_at=repository_payload.get("updated_at"),
        pushed_at=repository_payload.get("pushed_at"),
        languages=languages,
        topics=repository_payload.get("topics") or [],
        license_name=(repository_payload.get("license") or {}).get("spdx_id") or (repository_payload.get("license") or {}).get("name"),
        stars=int(repository_payload.get("stargazers_count") or 0),
        forks=int(repository_payload.get("forks_count") or 0),
        open_issues=int(repository_payload.get("open_issues_count") or 0),
        open_pull_requests=open_pull_requests,
    )


async def download_and_extract(repository: GitHubRepository, branch: str | None, settings: Settings) -> Path:
    selected_branch = branch or repository.default_branch
    archive_url = f"https://codeload.github.com/{repository.owner}/{repository.name}/zip/refs/heads/{selected_branch}"
    archive_path = Path.cwd() / ".codeatlas-downloads" / f"{repository.owner}-{repository.name}.zip"
    extract_path = archive_path.with_suffix("")
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    timeout = httpx.Timeout(settings.download_read_timeout_seconds, connect=settings.download_connect_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        async with client.stream("GET", archive_url) as response:
            response.raise_for_status()
            with archive_path.open("wb") as archive:
                async for block in response.aiter_bytes(settings.download_chunk_size_bytes):
                    archive.write(block)
    extract_path.mkdir(parents=True, exist_ok=True)
    try:
        with ZipFile(archive_path) as archive:
            archive.extractall(extract_path)
    except BadZipFile as exc:
        raise GitHubRepositoryError("GitHub returned an invalid repository archive.") from exc
    finally:
        archive_path.unlink(missing_ok=True)
    return extract_path
