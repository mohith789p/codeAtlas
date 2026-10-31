from pathlib import Path
from typing import Any

EXT_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
}

_PARSER_CACHE: dict[str, Any] = {}


def get_language_for_file(filepath: str) -> str | None:
    """Return recognized programming language name from file extension."""
    ext = Path(filepath).suffix.lower()
    return EXT_TO_LANGUAGE.get(ext)


class TreeSitterParserManager:
    """Initializes and caches Tree-sitter parsers for supported programming languages."""

    @staticmethod
    def get_parser(language: str) -> Any | None:
        """Retrieve or initialize a Tree-sitter parser instance for a language."""
        if language in _PARSER_CACHE:
            return _PARSER_CACHE[language]
        try:
            from tree_sitter_language_pack import get_parser
            parser = get_parser(language)
            _PARSER_CACHE[language] = parser
            return parser
        except Exception:
            return None

    @classmethod
    def parse(cls, filepath: str, content: str) -> tuple[Any | None, str | None]:
        """Parse source code string into a Tree-sitter AST; returns (tree, language)."""
        lang = get_language_for_file(filepath)
        if not lang:
            return None, None
        parser = cls.get_parser(lang)
        if parser is None:
            return None, lang
        try:
            tree = parser.parse(content.encode("utf-8"))
            return tree, lang
        except Exception:
            return None, lang
