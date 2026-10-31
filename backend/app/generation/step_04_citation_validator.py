import re
from app.schemas.response import ValidatedCitation
from app.schemas.retrieval import RetrievalResult

# Regex matching [filepath:start-end] or [filepath:line] or [filepath#L10-L20]
_CITATION_REGEX = re.compile(
    r"\[([a-zA-Z0-9_\-./\\]+)(?:[:#]L?(\d+)(?:[-–]L?(\d+))?)?\]"
)


class CitationValidator:
    """Parses citations from generated text and validates them against retrieved chunks."""

    def validate_citations(
        self, text: str, chunks: list[RetrievalResult]
    ) -> list[ValidatedCitation]:
        """Extract and verify all citations against retrieved evidence."""
        matches = _CITATION_REGEX.findall(text)
        if not matches:
            return []

        # Index retrieved evidence by normalized filepath
        evidence_by_file: dict[str, list[RetrievalResult]] = {}
        for r in chunks:
            norm_path = r.chunk.filepath.replace("\\", "/").lower()
            evidence_by_file.setdefault(norm_path, []).append(r)

        validated: list[ValidatedCitation] = []
        seen_keys: set[str] = set()

        for path_str, start_str, end_str in matches:
            norm_req_path = path_str.replace("\\", "/").lower()
            if norm_req_path not in evidence_by_file:
                continue

            start_line = int(start_str) if start_str else 1
            end_line = int(end_str) if end_str else start_line

            # Find matching chunk and symbol
            matching_chunk = None
            for item in evidence_by_file[norm_req_path]:
                c = item.chunk
                c_start = c.start_line or 1
                c_end = c.end_line or (c_start + len(c.content.splitlines()))
                if not (end_line < c_start or start_line > c_end):
                    matching_chunk = c
                    break

            citation_key = f"{norm_req_path}:{start_line}-{end_line}"
            if citation_key not in seen_keys:
                seen_keys.add(citation_key)
                validated.append(
                    ValidatedCitation(
                        filepath=path_str,
                        start_line=start_line,
                        end_line=end_line,
                        symbol=matching_chunk.symbol if matching_chunk else None,
                        confidence=1.0 if matching_chunk else 0.7,
                    )
                )

        return validated
