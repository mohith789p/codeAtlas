import io
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path
import httpx

from app.shared.config import Settings, get_settings
from app.shared.exceptions import IngestionError


class ArchiveExtractor:
    """Downloads repository archive from GitHub and unpacks to a temporary directory."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def download_and_extract(self, owner: str, name: str, branch: str, target_dir: Path | None = None) -> Path:
        """Stream tarball (or zipball fallback) and extract to target directory."""
        dest_dir = target_dir or Path(tempfile.mkdtemp(prefix="codeatlas-extract-"))
        headers = {"User-Agent": "CodeAtlas-Engine"}
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"

        tar_url = f"{self.settings.github_api_url}/repos/{owner}/{name}/tarball/{branch}"
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=self.settings.download_read_timeout_seconds) as client:
                res = await client.get(tar_url, headers=headers)
                if res.status_code == 404:
                    raise IngestionError(f"Branch '{branch}' or repository '{owner}/{name}' not found for archive download.")
                res.raise_for_status()
                content = res.content

            self._extract_bytes(content, dest_dir)
        except IngestionError:
            raise
        except Exception as exc:
            shutil.rmtree(dest_dir, ignore_errors=True)
            raise IngestionError(f"Failed to download or extract archive for {owner}/{name}@{branch}: {exc}") from exc

        # Find the root folder created inside the archive
        subdirs = [p for p in dest_dir.iterdir() if p.is_dir()]
        return subdirs[0] if len(subdirs) == 1 else dest_dir

    def _extract_bytes(self, content: bytes, dest: Path) -> None:
        try:
            with tarfile.open(fileobj=io.BytesIO(content), mode="r:*") as tar:
                # Use data filter if supported (Python 3.12+)
                if hasattr(tarfile, "data_filter"):
                    tar.extractall(path=dest, filter="data")
                else:
                    tar.extractall(path=dest)
        except Exception:
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                z.extractall(path=dest)
