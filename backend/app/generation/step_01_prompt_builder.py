import json
from app.schemas.retrieval import RetrievalResult

SYSTEM_PROMPT = """You are an expert repository intelligence engine.
Answer the user's question using ONLY the provided code snippets.
For every claim or code explanation, you MUST provide explicit citations in the format:
[filepath:start_line-end_line] or [filepath:line].
If the evidence does not contain enough information to answer the question, state:
"The provided repository context does not contain sufficient information to answer this question."
Do not speculate or reference external code not present in the snippets."""


class PromptBuilder:
    """Builds grounded prompts with structured evidence snippets and citation rules."""

    def build_prompt(self, query: str, chunks: list[RetrievalResult]) -> tuple[str, str]:
        """Return (system_instruction, user_content) with evidence formatted for grounding."""
        evidence_blocks: list[str] = []
        for idx, res in enumerate(chunks, start=1):
            c = res.chunk
            header = f"--- Snippet #{idx} | File: {c.filepath} | Lines: {c.start_line}-{c.end_line}"
            if c.symbol:
                header += f" | Symbol: {c.symbol} ({c.symbol_type or 'code'})"
            evidence_blocks.append(f"{header} ---\n{c.content}\n")

        evidence_text = "\n".join(evidence_blocks)
        user_content = f"User Question: {query}\n\nRetrieved Repository Evidence:\n{evidence_text}\n\nAnswer:"
        return SYSTEM_PROMPT, user_content
