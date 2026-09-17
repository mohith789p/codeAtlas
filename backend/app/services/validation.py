import re
from dataclasses import dataclass, field

from .retrieval import RetrievalResult

CITATION_PATTERN = re.compile(r"(?P<filepath>[A-Za-z0-9_./-]+):(?P<start>\d+)-(?P<end>\d+)(?:\s+`?\(?(?P<symbol>[A-Za-z_][A-Za-z0-9_.]*)\)?`?)?")


@dataclass(frozen=True)
class ValidatedCitation:
    filepath: str
    start_line: int
    end_line: int
    symbol: str | None = None
    chunk_id: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    reason: str | None = None
    citations: list[ValidatedCitation] = field(default_factory=list)


class CitationValidator:
    def validate(self, markdown: str, retrieved: list[RetrievalResult]) -> ValidationResult:
        citations: list[ValidatedCitation] = []
        seen_sources: set[tuple[str, int, int]] = set()
        if not retrieved:
            return ValidationResult(False, "No retrieved evidence is available.")
        matches = list(CITATION_PATTERN.finditer(markdown))
        if not matches:
            return ValidationResult(False, "The response contains no source citation.")
        for match in matches:
            filepath = match.group("filepath")
            start = int(match.group("start"))
            end = int(match.group("end"))
            symbol = match.group("symbol")
            candidates = [item for item in retrieved if item.filepath == filepath]
            if not candidates:
                return ValidationResult(False, f"Citation filepath was not retrieved: {filepath}.")
            matching = [item for item in candidates if item.start_line is not None and item.end_line is not None and start >= item.start_line and end <= item.end_line]
            if not matching:
                return ValidationResult(False, f"Citation line range was not retrieved: {filepath}:{start}-{end}.")
            if symbol and not any(_symbol_matches(symbol, item) for item in matching):
                return ValidationResult(False, f"Citation symbol was not retrieved: {symbol}.")
            selected = matching[0]
            source_identity = (filepath, start, end)
            if source_identity not in seen_sources:
                citations.append(ValidatedCitation(filepath, start, end, symbol, str(selected.chunk_id)))
                seen_sources.add(source_identity)
        return ValidationResult(True, citations=citations)


def _symbol_matches(symbol: str, result: RetrievalResult) -> bool:
    return symbol in {result.symbol, result.class_name, result.parent_symbol, f"{result.class_name}.{result.symbol}"}


class GroundingValidator:
    def validate(self, markdown: str, citation_result: ValidationResult, retrieved: list[RetrievalResult]) -> ValidationResult:
        if not citation_result.valid:
            return citation_result
        if not markdown.strip() or len(markdown.strip()) < 20:
            return ValidationResult(False, "The generated response contains insufficient grounded content.")
        evidence_terms = {term.lower() for item in retrieved for term in _terms(item.content) if len(term) >= 3}
        response_terms = set(_terms(CITATION_PATTERN.sub("", markdown)))
        if not evidence_terms.intersection(response_terms):
            return ValidationResult(False, "The response contains no recognizable retrieved evidence.")
        return citation_result


def _terms(text: str) -> list[str]:
    return re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text)
