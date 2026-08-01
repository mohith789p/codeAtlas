import os
import zipfile
import shutil
from typing import List, Dict, Any, Tuple

IGNORED_DIRS = {
    "node_modules", ".git", ".venv", "venv", "__pycache__", "build", "dist",
    ".idea", ".vscode", "target", "bin", "obj", ".next", ".nuxt"
}

IGNORED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".pdf", ".docx", ".doc", ".zip", ".tar",
    ".gz", ".exe", ".dll", ".so", ".dylib", ".pyc", ".lock", ".db", ".sqlite"
}

class RepositoryParserService:
    @staticmethod
    def extract_and_parse_zip(zip_path: str, extract_dir: str) -> List[Dict[str, Any]]:
        """Extracts ZIP and parses all text-based source code files."""
        os.makedirs(extract_dir, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
            
        parsed_files = []
        
        # Traverse directory
        for root, dirs, files in os.walk(extract_dir):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
            
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in IGNORED_EXTENSIONS or file.startswith("."):
                    continue
                
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, extract_dir).replace("\\", "/")
                
                # Strip top-level directory if single root dir in zip
                parts = rel_path.split("/")
                if len(parts) > 1 and parts[0] == os.path.basename(extract_dir):
                    rel_path = "/".join(parts[1:])
                    
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        
                    if not content.strip():
                        continue
                        
                    parsed_files.append({
                        "path": rel_path,
                        "extension": ext or "txt",
                        "content": content,
                        "size_bytes": len(content.encode("utf-8"))
                    })
                except Exception as e:
                    print(f"Error reading file {full_path}: {e}")
                    
        return parsed_files

    @staticmethod
    def chunk_file_content(content: str, max_chunk_lines: int = 60, overlap: int = 10) -> List[Dict[str, Any]]:
        """Splits file content into overlapping line-based code chunks."""
        lines = content.splitlines()
        if not lines:
            return []
            
        chunks = []
        total_lines = len(lines)
        start = 0
        chunk_idx = 0

        while start < total_lines:
            end = min(start + max_chunk_lines, total_lines)
            chunk_lines = lines[start:end]
            chunk_text = "\n".join(chunk_lines)
            
            if chunk_text.strip():
                chunks.append({
                    "chunk_index": chunk_idx,
                    "start_line": start + 1, # 1-indexed
                    "end_line": end,
                    "content": chunk_text
                })
                chunk_idx += 1
                
            if end == total_lines:
                break
            start += (max_chunk_lines - overlap)

        return chunks
