from collections.abc import Callable
from typing import Any
from uuid import UUID

from langchain.memory import ConversationSummaryBufferMemory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.language_models.llms import LLM
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import Field

from ..models import ChatMessage


class ProviderChainLanguageModel(LLM):
    """Adapt the existing async provider chain to LangChain's LLM interface."""

    provider_chain: Any = Field(exclude=True)

    @property
    def _llm_type(self) -> str:
        return "codeatlas-provider-chain"

    def _call(self, prompt: str, stop: list[str] | None = None, **kwargs: Any) -> str:
        raise RuntimeError("Conversation memory must use the asynchronous LangChain path.")

    async def _acall(self, prompt: str, stop: list[str] | None = None, **kwargs: Any) -> str:
        content, _, _ = await self.provider_chain.generate(prompt)
        return content


class ConversationMemory:
    """Thin adapter from persisted CodeAtlas messages to LangChain memory."""

    def __init__(
        self,
        message_store: Any,
        summarization_llm: LLM,
        max_token_limit: int = 2_000,
        message_to_token_ids: Callable[[str], list[int]] | None = None,
    ) -> None:
        self.message_store = message_store
        self.summarization_llm = summarization_llm
        self.max_token_limit = max_token_limit
        self.message_to_token_ids = message_to_token_ids

    async def load_history(self, session_id: UUID, current_query: str | None = None) -> str:
        stored_messages = await self.message_store.get_messages(session_id)
        if current_query is not None and stored_messages:
            last_msg = stored_messages[-1]
            if getattr(last_msg, "role", None) == "user" and getattr(last_msg, "content", None) == current_query:
                stored_messages = stored_messages[:-1]
        chat_history = InMemoryChatMessageHistory(messages=[
            _to_langchain_message(message) for message in stored_messages
        ])
        memory = ConversationSummaryBufferMemory(
            llm=self.summarization_llm,
            chat_memory=chat_history,
            max_token_limit=self.max_token_limit,
            memory_key="history",
            return_messages=False,
        )
        if self.message_to_token_ids is not None:
            memory.llm.custom_get_token_ids = self.message_to_token_ids
        await memory.aprune()
        variables = await memory.aload_memory_variables({})
        return str(variables["history"])


def _to_langchain_message(message: ChatMessage) -> HumanMessage | AIMessage:
    if message.role == "assistant":
        return AIMessage(content=message.content)
    return HumanMessage(content=message.content)
