import logging
from typing import Any
import httpx

from app.shared.config import Settings, get_settings
from app.shared.exceptions import ConfigurationError, PersistenceError

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Async connection manager for Supabase PostgREST and RPC endpoints."""

    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = client
        self._owns_client = client is None

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.supabase_url and self.settings.supabase_service_role_key)

    @property
    def base_url(self) -> str:
        if not self.settings.supabase_url:
            raise ConfigurationError("Supabase URL is not configured.")
        url = self.settings.supabase_url.rstrip("/")
        return url if url.endswith("/rest/v1") else f"{url}/rest/v1"

    @property
    def headers(self) -> dict[str, str]:
        key = self.settings.supabase_service_role_key or ""
        return {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
            self._owns_client = True
        return self._client

    async def execute(self, method: str, path: str, **kwargs: Any) -> Any:
        """Execute an HTTP request against the Supabase PostgREST API."""
        if not self.is_configured:
            raise PersistenceError("Database connection is not configured.")
        client = self.get_client()
        req_headers = {**self.headers, **kwargs.pop("headers", {})}
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = await client.request(method, url, headers=req_headers, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else None
        except httpx.HTTPStatusError as exc:
            msg = f"Database HTTP {exc.response.status_code} error on {method} {path}: {exc.response.text}"
            logger.error(msg)
            raise PersistenceError(msg) from exc
        except (httpx.RequestError, ValueError) as exc:
            msg = f"Database request failed on {method} {path}: {exc}"
            logger.error(msg)
            raise PersistenceError(msg) from exc

    async def aclose(self) -> None:
        """Close managed HTTP client connection pool."""
        if self._owns_client and self._client is not None and not self._client.is_closed:
            await self._client.aclose()


_default_connection: DatabaseConnection | None = None


def get_db_connection() -> DatabaseConnection:
    """Return singleton database connection instance."""
    global _default_connection
    if _default_connection is None:
        _default_connection = DatabaseConnection()
    return _default_connection
