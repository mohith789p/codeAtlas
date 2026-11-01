import re
from typing import Any
import httpx

from app.schemas.repository import Contributor, Repository
from app.shared.config import Settings, get_settings
from app.shared.exceptions import IngestionError
from app.shared.observability import safe_traceable

_GITHUB_URL_PATTERN = re.compile(r"^(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?/?$")


def parse_github_url(url: str) -> tuple[str, str]:
    """Extract (owner, repo) from GitHub URL or raise IngestionError."""
    match = _GITHUB_URL_PATTERN.match(url.strip())
    if not match:
        parts = url.strip().strip("/").split("/")
        if len(parts) == 2 and all(parts):
            return parts[0], parts[1].removesuffix(".git")
        raise IngestionError(f"Invalid GitHub repository URL: {url}")
    return match.group(1), match.group(2)


class GitHubClient:
    """Client for verifying GitHub repos, checking rate limits, and fetching metadata."""

    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = client

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "CodeAtlas-Engine"}
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        return headers

    @safe_traceable(name="github_fetch_metadata", run_type="tool")
    async def fetch_repository_metadata(self, url: str) -> dict[str, Any]:
        """Fetch metadata, languages, and contributors for a GitHub repository."""
        owner, repo = parse_github_url(url)
        headers = self._headers()
        async with httpx.AsyncClient(timeout=self.settings.download_read_timeout_seconds) as client:
            repo_res = await client.get(f"{self.settings.github_api_url}/repos/{owner}/{repo}", headers=headers)
            if repo_res.status_code == 404:
                raise IngestionError(f"GitHub repository '{owner}/{repo}' not found.")
            if repo_res.status_code == 403:
                raise IngestionError("GitHub API rate limit exceeded or access forbidden.")
            repo_res.raise_for_status()
            repo_data = repo_res.json()

            # Optional contributors fetch
            contribs: list[Contributor] = []
            try:
                c_res = await client.get(f"{self.settings.github_api_url}/repos/{owner}/{repo}/contributors?per_page=10", headers=headers)
                if c_res.status_code == 200:
                    contribs = [Contributor(username=c["login"], contributions=c.get("contributions", 0), avatar_url=c.get("avatar_url")) for c in c_res.json()]
            except Exception:
                pass

            lic = repo_data.get("license") or {}
            lic_name = lic.get("name") if isinstance(lic, dict) else None

            return {
                "owner": owner,
                "name": repo,
                "full_name": repo_data.get("full_name", f"{owner}/{repo}"),
                "description": repo_data.get("description"),
                "default_branch": repo_data.get("default_branch", "main"),
                "size_kb": repo_data.get("size", 0),
                "language": repo_data.get("language"),
                "stars": repo_data.get("stargazers_count", 0),
                "forks": repo_data.get("forks_count", 0),
                "contributors": contribs,
                "topics": repo_data.get("topics", []),
                "created_at": repo_data.get("created_at"),
                "updated_at": repo_data.get("updated_at"),
                "pushed_at": repo_data.get("pushed_at"),
                "visibility": repo_data.get("visibility", "public"),
                "license_name": lic_name,
            }

    async def fetch_file_content(self, owner: str, repo: str, branch: str, file_path: str) -> str:
        """Fetch raw content of a file from GitHub."""
        clean_path = file_path.lstrip("/")
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{clean_path}"
        headers = self._headers()
        async with httpx.AsyncClient(timeout=self.settings.download_read_timeout_seconds) as client:
            res = await client.get(url, headers=headers)
            if res.status_code == 404:
                raise FileNotFoundError(f"File '{file_path}' not found in {owner}/{repo}@{branch}")
            res.raise_for_status()
            return res.text
