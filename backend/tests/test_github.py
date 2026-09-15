import httpx
import pytest

from app.config import Settings
from app.services.github import inspect_repository


@pytest.mark.asyncio
async def test_inspect_repository_fetches_contributors_from_github():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/contributors"):
            return httpx.Response(200, json=[{
                "login": "octocat",
                "avatar_url": "https://avatars.example/octocat.png",
                "contributions": 17,
            }])
        if request.url.path.endswith("/languages"):
            return httpx.Response(200, json={"Python": 75, "TypeScript": 25})
        if request.url.path.endswith("/search/issues"):
            return httpx.Response(200, json={"total_count": 3})
        return httpx.Response(200, json={
            "size": 12,
            "default_branch": "main",
            "description": "Demo",
            "language": "Python",
            "visibility": "public",
            "topics": ["codeatlas"],
            "stargazers_count": 12,
            "forks_count": 4,
            "open_issues_count": 2,
        })

    transport = httpx.MockTransport(handler)
    settings = Settings(github_api_url="https://api.github.test")
    # inspect_repository creates its own client, so patch the client factory at the HTTP boundary.
    client_type = httpx.AsyncClient
    httpx.AsyncClient = lambda **kwargs: client_type(transport=transport)
    try:
        repository = await inspect_repository("https://github.com/example/demo", settings)
    finally:
        httpx.AsyncClient = client_type

    assert repository.contributors[0].username == "octocat"
    assert repository.contributors[0].commits == 17
    assert repository.languages == {"Python": 75.0, "TypeScript": 25.0}
    assert repository.topics == ["codeatlas"]
    assert repository.stars == 12
    assert repository.open_pull_requests == 3


@pytest.mark.asyncio
async def test_inspect_repository_keeps_metadata_when_contributors_fail():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/contributors"):
            return httpx.Response(403, json={"message": "rate limited"})
        return httpx.Response(200, json={"size": 12, "default_branch": "main"})

    transport = httpx.MockTransport(handler)
    settings = Settings(github_api_url="https://api.github.test")
    client_type = httpx.AsyncClient
    httpx.AsyncClient = lambda **kwargs: client_type(transport=transport)
    try:
        repository = await inspect_repository("https://github.com/example/demo", settings)
    finally:
        httpx.AsyncClient = client_type

    assert repository.name == "demo"
    assert repository.contributors == []
