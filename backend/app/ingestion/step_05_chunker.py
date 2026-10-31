import hashlib
from typing import Any
from uuid import uuid4

from app.ingestion.step_04_parser import TreeSitterParserManager
from app.schemas.retrieval import ChunkRecord


class ASTChunker:
    """Traverses Tree-sitter AST to extract semantic symbol chunks (functions, classes)."""

    def chunk_file(self, filepath: str, content: str) -> list[ChunkRecord]:
        """Extract symbol chunks from file content or fall back to full file chunk."""
        if not content.strip():
            return []
        tree, lang = TreeSitterParserManager.parse(filepath, content)
        if tree is not None:
            chunks = self._extract_ast_symbols(tree, filepath, content, lang)
            if chunks:
                return chunks

        # Fallback for plain text, config files, or unparsed code
        lines = content.splitlines()
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return [
            ChunkRecord(
                chunk_id=uuid4(),
                content_hash=content_hash,
                content=content,
                filepath=filepath,
                language=lang,
                symbol=None,
                symbol_type="file",
                start_line=1,
                end_line=len(lines),
            )
        ]

    def _extract_ast_symbols(self, tree: Any, filepath: str, content: str, language: str | None) -> list[ChunkRecord]:
        lines = content.splitlines(keepends=True)
        raw_bytes = content.encode("utf-8")
        records: list[ChunkRecord] = []

        def traverse(node: Any, cur_class: str | None = None, cur_parent: str | None = None) -> None:
            name, next_class, next_parent = None, cur_class, cur_parent
            if "class" in node.type:
                for child in node.children:
                    if child.type in {"identifier", "type_identifier", "name"}:
                        name = raw_bytes[child.start_byte : child.end_byte].decode("utf-8", "replace")
                        next_class = name
                        break
            elif "function" in node.type or "method" in node.type:
                for child in node.children:
                    if child.type in {"identifier", "name"}:
                        name = raw_bytes[child.start_byte : child.end_byte].decode("utf-8", "replace")
                        break

            if name:
                s_line, e_line = node.start_point[0] + 1, node.end_point[0] + 1
                chunk_text = "".join(lines[s_line - 1 : e_line])
                if chunk_text.strip():
                    chash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
                    records.append(
                        ChunkRecord(
                            chunk_id=uuid4(),
                            content_hash=chash,
                            content=chunk_text,
                            filepath=filepath,
                            language=language,
                            symbol=name,
                            symbol_type=node.type,
                            class_name=cur_class,
                            parent_symbol=cur_parent,
                            start_line=s_line,
                            end_line=e_line,
                        )
                    )
                    next_parent = name

            for child in node.children:
                traverse(child, next_class, next_parent)

        traverse(tree.root_node)
        return records
