from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import pytest

from app.database.repositories import DatabaseRepository
from app.embeddings.embedding_service import EmbeddingService
from app.ingestion.step_01_github_client import parse_github_url
from app.ingestion.step_03_file_filter import FileFilter
from app.ingestion.step_04_parser import get_language_for_file
from app.ingestion.step_05_chunker import ASTChunker
from app.ingestion.step_06_deduplicator import ChunkDeduplicator
from app.ingestion.step_07_indexer import ChunkIndexer
from app.schemas.retrieval import ChunkRecord
from app.shared.exceptions import IngestionError


def test_parse_github_url():
    assert parse_github_url("https://github.com/torvalds/linux") == ("torvalds", "linux")
    assert parse_github_url("https://github.com/torvalds/linux.git") == ("torvalds", "linux")
    assert parse_github_url("torvalds/linux") == ("torvalds", "linux")
    with pytest.raises(IngestionError):
        parse_github_url("https://gitlab.com/owner/repo")


def test_file_filter(tmp_path: Path):
    (tmp_path / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('ok')", encoding="utf-8")
    (tmp_path / "ignored.py").write_text("print('ignored')", encoding="utf-8")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
    (tmp_path / "image.bin").write_bytes(b"\x00\x01")
    (tmp_path / "large.txt").write_text("x" * 50, encoding="utf-8")

    filter_service = FileFilter(max_size_bytes=20)
    files = filter_service.filter_directory(tmp_path)
    assert files == {"main.py": "print('ok')"}


def test_parser_and_chunker():
    assert get_language_for_file("app/main.py") == "python"
    assert get_language_for_file("index.ts") == "typescript"
    assert get_language_for_file("README.md") is None

    chunker = ASTChunker()
    python_code = "class Calculator:\n    def add(self, a, b):\n        return a + b\n"
    chunks = chunker.chunk_file("calc.py", python_code)
    assert len(chunks) >= 1
    assert chunks[0].filepath == "calc.py"


@pytest.mark.asyncio
async def test_deduplicator_and_indexer():
    mock_db = MagicMock(spec=DatabaseRepository)
    mock_db.get_chunks_by_hashes = AsyncMock(return_value=[])
    mock_db.upsert_chunks = AsyncMock()

    mock_embedder = MagicMock(spec=EmbeddingService)
    mock_embedder.embed_documents = AsyncMock(return_value=[[0.1] * 768])

    repo_id = uuid4()
    chunk = ChunkRecord(content_hash="h1", content="code", filepath="f.py", start_line=1, end_line=1)

    dedup = ChunkDeduplicator(db_repo=mock_db)
    new_chunks, existing_chunks = await dedup.deduplicate(repo_id, [chunk, chunk])
    assert len(new_chunks) == 1
    assert len(existing_chunks) == 0

    indexer = ChunkIndexer(embedder=mock_embedder, db_repo=mock_db)
    indexed = await indexer.index_chunks(repo_id, new_chunks, existing_chunks)
    assert indexed == 1
    mock_db.upsert_chunks.assert_called_once()
