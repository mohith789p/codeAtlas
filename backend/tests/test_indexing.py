from uuid import uuid4

import pytest
from langchain_core.documents import Document

from app.services.indexing import IndexingService


class FakePersistence:
    def __init__(self) -> None:
        self.chunks = {}
        self.upsert_calls = 0
        self.deleted = None

    async def get_chunks_by_hash(self, repository_id, hashes):
        return {key: value for key, value in self.chunks.items() if key in hashes}

    async def upsert_chunks(self, repository_id, records):
        self.upsert_calls += 1
        self.chunks.update({record.content_hash: record for record in records})

    async def delete_stale_chunks(self, repository_id, current_hashes):
        self.deleted = current_hashes
        self.chunks = {key: value for key, value in self.chunks.items() if key in current_hashes}


class FakeEmbedder:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    async def embed_documents(self, texts):
        self.calls.append(list(texts))
        if self.fail:
            raise RuntimeError("provider unavailable")
        return [[float(len(text))] for text in texts]


@pytest.mark.asyncio
async def test_unchanged_documents_reuse_embeddings_and_changed_documents_reembed():
    persistence = FakePersistence()
    service = IndexingService(persistence)
    embedder = FakeEmbedder()
    repository_id = uuid4()
    first = [Document(page_content="alpha", metadata={"filepath": "a.py", "symbol": "alpha"})]
    await service.index_documents(repository_id, first, embedder)
    unchanged = await service.index_documents(repository_id, first, embedder)
    changed = [Document(page_content="beta", metadata={"filepath": "a.py", "symbol": "beta"})]
    result = await service.index_documents(repository_id, changed, embedder)

    assert unchanged == {"total": 1, "embedded": 0, "reused": 1}
    assert result == {"total": 1, "embedded": 1, "reused": 0}
    assert len(embedder.calls) == 2
    assert embedder.calls[-1] == ["beta"]


@pytest.mark.asyncio
async def test_metadata_is_persisted_with_structural_document():
    persistence = FakePersistence()
    service = IndexingService(persistence)
    document = Document(page_content="def run(): pass", metadata={"filepath": "src/run.py", "language": "python", "symbol": "run", "start_line": 1, "end_line": 1, "imports": []})

    await service.index_documents(uuid4(), [document], FakeEmbedder())

    stored = next(iter(persistence.chunks.values()))
    assert stored.metadata["symbol"] == "run"
    assert stored.metadata["filepath"] == "src/run.py"


@pytest.mark.asyncio
async def test_embedding_failure_does_not_write_chunks():
    persistence = FakePersistence()
    service = IndexingService(persistence)

    with pytest.raises(RuntimeError):
        await service.index_documents(uuid4(), [Document(page_content="alpha")], FakeEmbedder(fail=True))

    assert persistence.chunks == {}
    assert persistence.upsert_calls == 0
