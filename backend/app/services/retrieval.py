import numpy as np
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.models import CodeChunk, File
from app.core.database import is_sqlite
from app.core.gemini import gemini_client

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculates cosine similarity between two float vectors."""
    a = np.array(vec1, dtype=float)
    b = np.array(vec2, dtype=float)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

class RetrievalService:
    @staticmethod
    async def search_relevant_chunks(
        repo_id: int, query: str, top_k: int = 5, db: Session = None
    ) -> List[Dict[str, Any]]:
        """Retrieves top_k most semantically relevant code chunks for a user query."""
        query_vec = await gemini_client.generate_embedding(query)
        
        results = []

        if not is_sqlite:
            try:
                # Use PostgreSQL pgvector similarity operator (<=> cosine distance)
                query_str = f"[{','.join(map(str, query_vec))}]"
                sql = text("""
                    SELECT c.id, c.file_id, c.start_line, c.end_line, c.content, f.path,
                           1 - (c.embedding <=> :query_vec::vector) AS similarity
                    FROM code_chunks c
                    JOIN files f ON c.file_id = f.id
                    WHERE c.repo_id = :repo_id
                    ORDER BY c.embedding <=> :query_vec::vector ASC
                    LIMIT :top_k
                """)
                res = db.execute(sql, {"repo_id": repo_id, "query_vec": query_str, "top_k": top_k}).fetchall()
                for row in res:
                    results.append({
                        "id": row.id,
                        "file_path": row.path,
                        "start_line": row.start_line,
                        "end_line": row.end_line,
                        "content": row.content,
                        "score": round(float(row.similarity), 4)
                    })
                return results
            except Exception as e:
                print(f"[RetrievalService] pgvector query fallback to python match: {e}")

        # Python cosine similarity fallback (SQLite or non-pgvector DB)
        chunks = db.query(CodeChunk).filter(CodeChunk.repo_id == repo_id).all()
        scored_chunks = []

        for chunk in chunks:
            c_vec = chunk.get_embedding()
            if c_vec and len(c_vec) == len(query_vec):
                sim = cosine_similarity(query_vec, c_vec)
                scored_chunks.append((sim, chunk))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_chunks = scored_chunks[:top_k]

        for score, chunk in top_chunks:
            file_obj = db.query(File).filter(File.id == chunk.file_id).first()
            file_path = file_obj.path if file_obj else "unknown"
            results.append({
                "id": chunk.id,
                "file_path": file_path,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "content": chunk.content,
                "score": round(float(score), 4)
            })

        return results
