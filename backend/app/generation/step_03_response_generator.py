import logging
from app.generation.step_01_prompt_builder import PromptBuilder
from app.generation.step_02_llm_client import LLMClientChain
from app.schemas.retrieval import RetrievalResult

logger = logging.getLogger(__name__)

EMPTY_REPO_RESPONSE = "This question does not appear to be related to the repository codebase, or no relevant code could be retrieved."


class ResponseGenerator:
    """Manages prompt creation and LLM invocation with an empty-chunk fast exit guard."""

    def __init__(
        self,
        prompt_builder: PromptBuilder | None = None,
        llm_client: LLMClientChain | None = None,
    ) -> None:
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.llm_client = llm_client or LLMClientChain()

    async def generate_response(
        self, query: str, chunks: list[RetrievalResult]
    ) -> tuple[str, str, str, bool]:
        """Generate response or fast-exit if no chunks are relevant."""
        # Empty chunk guard: Avoid wasteful and hallucinated LLM calls
        if not chunks:
            logger.info("Empty chunk guard triggered for query: '%s'", query)
            return EMPTY_REPO_RESPONSE, "guard", "fast-exit", True

        system_instruction, user_content = self.prompt_builder.build_prompt(query, chunks)
        raw_text, provider, model = await self.llm_client.generate(system_instruction, user_content)
        return raw_text, provider, model, False
