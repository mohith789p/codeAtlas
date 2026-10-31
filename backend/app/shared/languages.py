EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    "py": "python",
    "ts": "typescript",
    "tsx": "typescript",
    "js": "javascript",
    "jsx": "javascript",
    "json": "json",
    "md": "markdown",
    "css": "css",
    "scss": "scss",
    "html": "html",
    "yaml": "yaml",
    "yml": "yaml",
    "toml": "toml",
    "sh": "bash",
    "bash": "bash",
    "go": "go",
    "rs": "rust",
    "java": "java",
    "c": "c",
    "cpp": "cpp",
    "h": "c",
    "hpp": "cpp",
    "sql": "sql",
}


def detect_language(filepath: str) -> str:
    """Detect syntax language from file extension, defaulting to plaintext."""
    ext = filepath.rsplit(".", 1)[-1].lower() if "." in filepath else ""
    return EXTENSION_LANGUAGE_MAP.get(ext, "plaintext")
