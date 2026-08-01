import asyncio
import logging
from typing import List
from sqlalchemy.orm import Session
from app.models.models import Repository, File, CodeChunk
from app.core.gemini import gemini_client, GeminiFatalError, GeminiAPIError
from app.utils.gemini_rate_limiter import GeminiDailyQuotaExceededError
from app.services.parser import RepositoryParserService

logger = logging.getLogger("embedding_service")

class EmbeddingService:
    @staticmethod
    async def process_repository(repo_id: int, zip_path: str, extract_dir: str, db: Session):
        """Processes repository in background: extracts ZIP, chunks files, generates embeddings with batching & rate limiting."""
        try:
            repo = db.query(Repository).filter(Repository.id == repo_id).first()
            if not repo:
                return

            repo.status = "processing"
            db.commit()

            parsed_files = RepositoryParserService.extract_and_parse_zip(zip_path, extract_dir)
            
            pending_chunks = []  # list of tuples: (file_id, chunk_dict, contextualized_text)

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
                    contextualized_text = f"File: {f_info['path']} (Lines {chunk['start_line']}-{chunk['end_line']})\n{chunk['content']}"
                    pending_chunks.append((file_obj.id, chunk, contextualized_text))

            if not pending_chunks:
                repo.file_count = len(parsed_files)
                repo.chunk_count = 0
                repo.status = "ready"
                db.commit()
                print(f"✅ [EmbeddingService] Ingested Repo ID {repo_id}: 0 chunks.")
                return

            all_texts = [item[2] for item in pending_chunks]

            try:
                embeddings = await gemini_client.generate_embeddings_batch(all_texts)
            except (GeminiFatalError, GeminiDailyQuotaExceededError) as fe:
                logger.error(f"[EmbeddingService] Fatal or Quota API error on Repo ID {repo_id}: {fe}")
                repo.status = "error"
                db.commit()
                print(f"❌ [EmbeddingService] Aborted ingestion for Repo ID {repo_id}: {fe}")
                return
            except GeminiAPIError as ae:
                logger.error(f"[EmbeddingService] API error on Repo ID {repo_id}: {ae}")
                repo.status = "error"
                db.commit()
                print(f"❌ [EmbeddingService] Aborted ingestion for Repo ID {repo_id}: {ae}")
                return

            for idx, (file_id, chunk_dict, _) in enumerate(pending_chunks):
                if idx >= len(embeddings):
                    raise ValueError(f"Missing embedding vector for chunk index {idx} (received {len(embeddings)} embeddings for {len(pending_chunks)} chunks)")
                embedding_vec = embeddings[idx]

                chunk_obj = CodeChunk(
                    file_id=file_id,
                    repo_id=repo.id,
                    chunk_index=chunk_dict["chunk_index"],
                    start_line=chunk_dict["start_line"],
                    end_line=chunk_dict["end_line"],
                    content=chunk_dict["content"]
                )
                chunk_obj.set_embedding(embedding_vec)
                db.add(chunk_obj)

            repo.file_count = len(parsed_files)
            repo.chunk_count = len(pending_chunks)
            repo.status = "ready"
            db.commit()
            print(f"✅ [EmbeddingService] Successfully ingested Repo ID {repo_id}: {len(parsed_files)} files, {len(pending_chunks)} chunks.")

        except Exception as e:
            logger.error(f"[EmbeddingService] Unexpected error processing repo {repo_id}: {e}")
            repo = db.query(Repository).filter(Repository.id == repo_id).first()
            if repo:
                repo.status = "error"
                db.commit()
