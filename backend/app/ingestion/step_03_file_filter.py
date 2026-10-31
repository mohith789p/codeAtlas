from pathlib import Path, PurePosixPath
import pathspec

IGNORE_DIRS = {".git", "node_modules", "vendor", "dist", "build", "coverage", "__pycache__", ".venv", ".tox", ".idea", ".vscode"}
IGNORE_FILES = {".gitignore", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Cargo.lock", "go.sum", "composer.lock"}


def is_binary_file(sample: bytes) -> bool:
    """Return True if null bytes exist in sample, signaling binary data."""
    return b"\x00" in sample


def build_gitignore_spec(root: Path) -> pathspec.PathSpec:
    """Parse .gitignore from extracted repo root if present."""
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return pathspec.PathSpec.from_lines("gitwildmatch", [])
    try:
        lines = gitignore.read_text(encoding="utf-8", errors="ignore").splitlines()
        return pathspec.PathSpec.from_lines("gitwildmatch", lines)
    except Exception:
        return pathspec.PathSpec.from_lines("gitwildmatch", [])


def decode_bytes(data: bytes) -> str:
    """Attempt decoding file content across common encodings."""
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


class FileFilter:
    """Filters repository files by gitignore patterns, binary check, static paths, and size."""

    def __init__(self, max_size_bytes: int = 1_048_576) -> None:
        self.max_size_bytes = max_size_bytes

    def filter_directory(self, root: Path) -> dict[str, str]:
        """Traverse directory, filter files, and return relative_path -> content."""
        spec = build_gitignore_spec(root)
        results: dict[str, str] = {}
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            parts = PurePosixPath(rel).parts
            if spec.match_file(rel):
                continue
            if any(p in IGNORE_DIRS for p in parts) or path.name in IGNORE_FILES:
                continue
            try:
                if path.stat().st_size > self.max_size_bytes:
                    continue
                raw = path.read_bytes()
                if is_binary_file(raw[:1024]):
                    continue
                results[rel] = decode_bytes(raw)
            except (OSError, PermissionError):
                continue
        return results
