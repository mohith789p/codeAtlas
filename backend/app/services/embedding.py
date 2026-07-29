import asyncio
import logging
from typing import List
from sqlalchemy.orm import Session
from app.models.models import Repository, File, CodeChunk
from app.core.gemini import gemini_client, GeminiFatalError, GeminiAPIError
from app.services.parser import RepositoryParserService

logger = logging.getLogger("embedding_service")

class EmbeddingService:
    @staticmethod
    async def process_repository(repo_id: int, zip_path: str, extract_dir: str, db: Session):
        """Processes repository in background: extracts ZIP, chunks files, generates embeddings with fail-fast error handling."""
        try:
            repo = db.query(Repository).filter(Repository.id == repo_id).first()
            if not repo:
                return

            repo.status = "processing"
            db.commit()

            parsed_files = RepositoryParserService.extract_and_parse_zip(zip_path, extract_dir)
            
            total_chunks = 0

            for f_info in parsed_files:
                file_obj = File(
                    repo_id=repo.id,
                    path=f_info["path"],
                    extension=f_info["extension"],
                    content=f_info["content"],
                    size_bytes=f_info["size_bytes"]
                )
                db.add(file_obj)
                db.flush() # get file_obj.id

                raw_chunks = RepositoryParserService.chunk_file_content(f_info["content"])
                for chunk in raw_chunks:
                    # Enrich chunk text with file context
                    contextualized_text = f"File: {f_info['path']} (Lines {chunk['start_line']}-{chunk['end_line']})\n{chunk['content']}"
                    
                    try:
                        embedding_vec = await gemini_client.generate_embedding(contextualized_text)
                    except GeminiFatalError as fe:
                        # Fail-fast immediately on fatal client error (e.g. 404, 401)
                        logger.error(f"[EmbeddingService] Fatal API error on Repo ID {repo_id}: {fe}")
                        repo.status = "error"
                        db.commit()
                        print(f"❌ [EmbeddingService] Aborted ingestion for Repo ID {repo_id}: {fe}")
                        return  # STOP processing immediately, do not loop over remaining chunks!
                    except GeminiAPIError as ae:
                        logger.error(f"[EmbeddingService] API error on Repo ID {repo_id}: {ae}")
                        repo.status = "error"
                        db.commit()
                        print(f"❌ [EmbeddingService] Aborted ingestion for Repo ID {repo_id}: {ae}")
                        return
                    
                    chunk_obj = CodeChunk(
                        file_id=file_obj.id,
                        repo_id=repo.id,
                        chunk_index=chunk["chunk_index"],
                        start_line=chunk["start_line"],
                        end_line=chunk["end_line"],
                        content=chunk["content"]
                    )
                    chunk_obj.set_embedding(embedding_vec)
                    db.add(chunk_obj)
                    total_chunks += 1
                
                await asyncio.sleep(0.02)

            repo.file_count = len(parsed_files)
            repo.chunk_count = total_chunks
            repo.status = "ready"
            db.commit()
            print(f"✅ [EmbeddingService] Successfully ingested Repo ID {repo_id}: {len(parsed_files)} files, {total_chunks} chunks.")

        except Exception as e:
            logger.error(f"[EmbeddingService] Unexpected error processing repo {repo_id}: {e}")
            repo = db.query(Repository).filter(Repository.id == repo_id).first()
            if repo:
                repo.status = "error"
                db.commit()
