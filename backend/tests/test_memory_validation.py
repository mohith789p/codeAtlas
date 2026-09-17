from uuid import uuid4

import pytest

from app.models import ChatMessage
from app.services.memory import ConversationMemory, ProviderChainLanguageModel
from app.services.retrieval import RetrievalResult
from app.services.validation import CitationValidator, GroundingValidator


class FakeStore:
    def __init__(self, messages_by_session=None):
        self.messages_by_session = messages_by_session or {}

    async def get_messages(self, session_id):
        return self.messages_by_session.get(session_id, [])


class FakeSummaryChain:
    def __init__(self):
        self.prompts = []

    async def generate(self, prompt):
        self.prompts.append(prompt)
        return "Earlier discussion covered run and its caller.", "fake", "summary-model"


def evidence():
    return [RetrievalResult(
        chunk_id="1", repo_id="repo", content="def run(): return 42", filepath="src/run.py",
        language="python", symbol="run", symbol_type="function_definition", start_line=1, end_line=1,
    )]


def test_valid_citation_is_accepted():
    result = CitationValidator().validate("The function returns 42. `src/run.py:1-1 run`", evidence())
    assert result.valid is True
    assert result.citations[0].chunk_id == "1"


def test_invalid_filepath_line_and_symbol_are_rejected():
    validator = CitationValidator()
    assert not validator.validate("`missing.py:1-1`", evidence()).valid
    assert not validator.validate("`src/run.py:2-3 run`", evidence()).valid
    assert not validator.validate("`src/run.py:1-1 missing`", evidence()).valid


def test_repeated_citation_occurrences_return_one_source():
    result = CitationValidator().validate(
        "First claim `src/run.py:1-1 run`. Second claim `src/run.py:1-1 run`.",
        evidence(),
    )

    assert result.valid is True
    assert len(result.citations) == 1


def test_grounding_requires_retrieved_terms_and_valid_citation():
    validator = GroundingValidator()
    citations = CitationValidator().validate("run returns 42. `src/run.py:1-1 run`", evidence())
    assert validator.validate("run returns 42. `src/run.py:1-1 run`", citations, evidence()).valid
    unsupported = validator.validate("unrelated claim. `src/run.py:1-1 run`", citations, evidence())
    assert unsupported.valid is False


@pytest.mark.asyncio
async def test_conversation_memory_loads_existing_messages_and_uses_summary_buffer():
    session_id = uuid4()
    messages = [ChatMessage(role="user", content=f"turn {index} about run") for index in range(8)]
    store = FakeStore({session_id: messages})
    summary_chain = FakeSummaryChain()
    memory = ConversationMemory(
        store,
        ProviderChainLanguageModel(provider_chain=summary_chain),
        max_token_limit=20,
        message_to_token_ids=lambda text: list(range(max(1, len(text.split())))),
    )

    history = await memory.load_history(session_id)

    assert "Earlier discussion covered run and its caller." in history
    assert "turn 7 about run" in history
    assert summary_chain.prompts


@pytest.mark.asyncio
async def test_conversation_memory_isolated_by_session():
    session_a = uuid4()
    session_b = uuid4()
    store = FakeStore({session_a: [ChatMessage(role="user", content="session A only")]})
    memory = ConversationMemory(
        store,
        ProviderChainLanguageModel(provider_chain=FakeSummaryChain()),
        message_to_token_ids=lambda text: list(range(max(1, len(text.split())))),
    )

    history_a = await memory.load_history(session_a)
    history_b = await memory.load_history(session_b)

    assert "session A only" in history_a
    assert "session A only" not in history_b


def test_citation_with_parentheses_around_symbol_is_accepted():
    validator = CitationValidator()
    # Matches with parentheses
    result_parens = validator.validate("Returns 42 `src/run.py:1-1 (run)`", evidence())
    assert result_parens.valid is True
    assert result_parens.citations[0].symbol == "run"

    # Matches without parentheses
    result_plain = validator.validate("Returns 42 `src/run.py:1-1 run`", evidence())
    assert result_plain.valid is True
    assert result_plain.citations[0].symbol == "run"


@pytest.mark.asyncio
async def test_conversation_memory_excludes_current_turn_query():
    session_id = uuid4()
    messages = [
        ChatMessage(role="user", content="first question"),
        ChatMessage(role="assistant", content="first answer"),
        ChatMessage(role="user", content="active turn question"),
    ]
    store = FakeStore({session_id: messages})
    memory = ConversationMemory(
        store,
        ProviderChainLanguageModel(provider_chain=FakeSummaryChain()),
        max_token_limit=1000,
        message_to_token_ids=lambda text: list(range(max(1, len(text.split())))),
    )

    history = await memory.load_history(session_id, current_query="active turn question")

    assert "first question" in history
    assert "first answer" in history
    assert "active turn question" not in history
