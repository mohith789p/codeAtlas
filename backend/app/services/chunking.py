from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from tree_sitter_language_pack import get_parser

SUPPORTED_LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
}

STRUCTURAL_NODES: dict[str, set[str]] = {
    "python": {"function_definition", "class_definition"},
    "javascript": {"function_declaration", "class_declaration", "method_definition"},
    "typescript": {"function_declaration", "class_declaration", "method_definition"},
    "tsx": {"function_declaration", "class_declaration", "method_definition"},
    "go": {"function_declaration", "method_declaration", "type_declaration"},
    "rust": {"function_item", "struct_item", "impl_item"},
    "java": {"class_declaration", "method_declaration", "constructor_declaration"},
}
IMPORT_NODES = {
    "import_statement",
    "import_from_statement",
    "import_declaration",
    "import_spec",
    "use_declaration",
}


def _node_name(node: Any, source: bytes) -> str | None:
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return None
    return source[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")


def _walk(node: Any):
    yield node
    for child in node.children:
        yield from _walk(child)


def _imports(root: Any, source: bytes) -> list[str]:
    return [source[node.start_byte:node.end_byte].decode("utf-8", errors="replace") for node in _walk(root) if node.type in IMPORT_NODES]


def parse_source(filepath: str, content: str) -> list[Document]:
    suffix = Path(filepath).suffix.lower()
    language = SUPPORTED_LANGUAGES.get(suffix)
    if language is None:
        return []
    source = content.encode("utf-8")
    tree = get_parser(language).parse(source)
    imports = _imports(tree.root_node, source)
    documents: list[Document] = []
    for node in _walk(tree.root_node):
        if node.type not in STRUCTURAL_NODES[language]:
            continue
        symbol = _node_name(node, source) or "<anonymous>"
        parent = node.parent
        class_name = None
        parent_symbol = None
        while parent is not None:
            ancestor_name = _node_name(parent, source)
            if parent.type.endswith("class_definition") or parent.type in {"class_declaration", "struct_item", "type_declaration"}:
                class_name = ancestor_name or class_name
            elif ancestor_name and parent_symbol is None:
                parent_symbol = ancestor_name
            parent = parent.parent
        metadata = {
            "filepath": filepath,
            "language": language,
            "symbol": symbol,
            "symbol_type": node.type,
            "class_name": class_name,
            "parent_symbol": parent_symbol,
            "start_line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "imports": imports,
        }
        documents.append(Document(page_content=source[node.start_byte:node.end_byte].decode("utf-8", errors="replace"), metadata=metadata))
    return documents


def split_unparsed(filepath: str, content: str, chunk_size: int = 1_200, overlap: int = 120) -> list[Document]:
    documents: list[Document] = []
    start = 0
    while start < len(content):
        end = min(len(content), start + chunk_size)
        line_start = content.count("\n", 0, start) + 1
        line_end = content.count("\n", 0, end) + 1
        documents.append(Document(page_content=content[start:end], metadata={"filepath": filepath, "start_line": line_start, "end_line": line_end, "symbol": None, "symbol_type": None, "imports": []}))
        if end == len(content):
            break
        start = max(start + 1, end - overlap)
    return documents


def chunk_file(filepath: str, content: str) -> list[Document]:
    documents = parse_source(filepath, content)
    return documents or split_unparsed(filepath, content)
