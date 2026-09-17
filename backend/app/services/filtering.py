from pathlib import Path, PurePosixPath

import pathspec

STATIC_FILE_NAMES = {
    ".gitignore",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "composer.lock",
}
STATIC_DIRECTORY_NAMES = {".git", "node_modules", "vendor", "dist", "build", "coverage", "__pycache__"}


def is_binary(data: bytes) -> bool:
    return b"\x00" in data


def _gitignore_spec(root: Path) -> pathspec.PathSpec:
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return pathspec.PathSpec.from_lines("gitwildmatch", [])
    return pathspec.PathSpec.from_lines("gitwildmatch", gitignore.read_text(encoding="utf-8", errors="ignore").splitlines())


def decode_text_bytes(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def collect_text_files(root: Path, max_file_size_bytes: int) -> dict[str, str]:
    """Apply the documented filter order before decoding retained files."""
    spec = _gitignore_spec(root)
    files: dict[str, str] = {}
    for candidate in root.rglob("*"):
        if not candidate.is_file():
            continue
        relative = candidate.relative_to(root).as_posix()
        parts = PurePosixPath(relative).parts
        if spec.match_file(relative):
            continue
        if any(part in STATIC_DIRECTORY_NAMES for part in parts) or candidate.name in STATIC_FILE_NAMES:
            continue
        if candidate.stat().st_size > max_file_size_bytes:
            continue
        data = candidate.read_bytes()
        if is_binary(data):
            continue
        files[relative] = decode_text_bytes(data)
    return files
