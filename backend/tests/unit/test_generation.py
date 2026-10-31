from unittest.mock import AsyncMock, MagicMock
import pytest

from app.generation.step_01_prompt_builder import PromptBuilder
from app.generation.step_02_llm_client import LLMClientChain
from app.generation.step_03_response_generator import EMPTY_REPO_RESPONSE, ResponseGenerator
from app.generation.step_04_citation_validator import CitationValidator
from app.generation.step_05_response_formatter import ResponseFormatter
from app.schemas.retrieval import ChunkRecord, RetrievalResult


def test_prompt_builder_and_formatter():
    builder = PromptBuilder()
    chunk = ChunkRecord(content_hash="h", content="print('hello')", filepath="main.py", start_line=1, end_line=1)
    results = [RetrievalResult(chunk=chunk, score=0.9)]
    sys_prompt, user_content = builder.build_prompt("How to run?", results)

    assert "main.py" in user_content
    assert "print('hello')" in user_content

    formatter = ResponseFormatter()
    resp = formatter.format(answer="test", citations=[], provider="gemini", model="gemini-2.5-flash")
    assert resp.answer == "test"
    assert resp.provider == "gemini"


@pytest.mark.asyncio
async def test_empty_chunk_guard():
    gen = ResponseGenerator()
    answer, provider, model, is_empty = await gen.generate_response("random query", [])
    assert is_empty is True
    assert answer == EMPTY_REPO_RESPONSE
    assert provider == "guard"


def test_citation_validator():
    chunk = ChunkRecord(content_hash="h", content="def run():\n    return True\n", filepath="src/runner.py", start_line=10, end_line=12, symbol="run")
    results = [RetrievalResult(chunk=chunk, score=1.0)]

    text = "The runner starts at [src/runner.py:10-12] using function run."
    validator = CitationValidator()
    citations = validator.validate_citations(text, results)

    assert len(citations) == 1
    assert citations[0].filepath == "src/runner.py"
    assert citations[0].start_line == 10
    assert citations[0].end_line == 12
    assert citations[0].symbol == "run"


@pytest.mark.asyncio
async def test_llm_client_fallback():
    chain = LLMClientChain()
    chain._call_gemini = AsyncMock(side_effect=Exception("Gemini quota 429"))
    chain._call_groq = AsyncMock(return_value=("Answer from Groq", "llama-3.3-70b-versatile"))

    text, provider, model = await chain.generate("system", "user")
    assert text == "Answer from Groq"
    assert provider == "groq"
    assert model == "llama-3.3-70b-versatile"
