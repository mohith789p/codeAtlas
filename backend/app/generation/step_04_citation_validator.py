import re
from app.schemas.response import ValidatedCitation
from app.schemas.retrieval import RetrievalResult
from app.shared.observability import safe_traceable

_BRACKET_REGEX = re.compile(r"\[([^\]\n]+)\]")
_ITEM_REGEX = re.compile(
    r"^([a-zA-Z0-9_\-./\\]+?)(?:[:#]L?(\d+)(?:[-–]L?(\d+))?)?$"
)


class CitationValidator:
    """Parses citations from generated text and validates them against retrieved chunks."""

    @safe_traceable(name="validate_citations", run_type="tool")
    def validate_citations(
        self, text: str, chunks: list[RetrievalResult]
    ) -> list[ValidatedCitation]:
        """Extract and verify single or comma-separated citations against evidence."""
        raw_items: list[tuple[str, str | None, str | None]] = []
        for block in _BRACKET_REGEX.findall(text):
            for part in re.split(r"[,;]", block):
                cleaned = part.strip("` \t")
                m = _ITEM_REGEX.match(cleaned) if cleaned else None
                if m:
                    raw_items.append(m.groups())
        if not raw_items:
            return []

        evidence_by_file: dict[str, list[RetrievalResult]] = {}
        for r in chunks:
            norm = r.chunk.filepath.replace("\\", "/").lower()
            evidence_by_file.setdefault(norm, []).append(r)

        validated: list[ValidatedCitation] = []
        seen_keys: set[str] = set()

        for path_str, start_str, end_str in raw_items:
            norm_req = path_str.replace("\\", "/").lower().strip("/")
            norm_base = norm_req.split("/")[-1]
            matching_items = next(
                (v for k, v in evidence_by_file.items()
                 if k == norm_req or k.endswith("/" + norm_req) or k.split("/")[-1] == norm_base),
                None,
            )
            if not matching_items:
                continue

            start_line = int(start_str) if start_str else 1
            end_line = int(end_str) if end_str else start_line

            matching_chunk = None
            for item in matching_items:
                c = item.chunk
                c_start = c.start_line or 1
                c_end = c.end_line or (c_start + len(c.content.splitlines()))
                if not (end_line < c_start or start_line > c_end):
                    matching_chunk = c
                    break

            canonical_path = matching_chunk.filepath if matching_chunk else matching_items[0].chunk.filepath
            if matching_chunk and not start_str:
                start_line = matching_chunk.start_line or 1
                end_line = matching_chunk.end_line or start_line

            citation_key = f"{canonical_path.lower()}:{start_line}-{end_line}"
            if citation_key not in seen_keys:
                seen_keys.add(citation_key)
                validated.append(
                    ValidatedCitation(
                        filepath=canonical_path,
                        start_line=start_line,
                        end_line=end_line,
                        symbol=matching_chunk.symbol if matching_chunk else None,
                        confidence=1.0 if matching_chunk else 0.7,
                    )
                )

        return validated
