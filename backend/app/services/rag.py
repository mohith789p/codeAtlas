import json
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.models import ChatMessage, GeneratedDoc, File, Repository
from app.services.retrieval import RetrievalService
from app.core.gemini import gemini_client

class RAGService:
    @staticmethod
    async def answer_question(repo_id: int, session_id: int, query: str, db: Session) -> Dict[str, Any]:
        """Performs vector search, constructs RAG prompt with ONLY retrieved chunks, and generates Gemini response."""
        # 1. Retrieve top 5 relevant code chunks
        top_chunks = await RetrievalService.search_relevant_chunks(
            repo_id=repo_id, query=query, top_k=5, db=db
        )

        # 2. Build grounded context string
        context_blocks = []
        citations = []
        for i, chunk in enumerate(top_chunks, 1):
            context_blocks.append(
                f"--- Source [{i}]: {chunk['file_path']} (Lines {chunk['start_line']}-{chunk['end_line']}) ---\n{chunk['content']}"
            )
            citations.append({
                "source_index": i,
                "file_path": chunk['file_path'],
                "start_line": chunk['start_line'],
                "end_line": chunk['end_line'],
                "score": chunk['score']
            })

        context_str = "\n\n".join(context_blocks)

        system_instruction = (
            "You are CodeAtlas, a Senior Software Architect AI. "
            "Your task is to answer user questions about a software repository using ONLY the provided code snippets. "
            "Do NOT invent code or generate new source code. "
            "Be precise, clear, and cite sources using [Source X] notation when referencing specific files or lines."
        )

        user_prompt = (
            f"RELEVANT CODE SNIPPETS FROM REPOSITORY:\n\n{context_str}\n\n"
            f"USER QUESTION: {query}\n\n"
            "Please provide a comprehensive, clear architectural explanation based on the code snippets above."
        )

        # 3. Call Gemini
        ai_response = await gemini_client.generate_response(user_prompt, system_instruction)

        # 4. Save Chat Messages in Database
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=query
        )
        ai_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=ai_response,
            sources=json.dumps(citations)
        )

        db.add(user_msg)
        db.add(ai_msg)
        db.commit()
        db.refresh(ai_msg)

        return {
            "id": ai_msg.id,
            "role": "assistant",
            "content": ai_response,
            "sources": citations,
            "created_at": ai_msg.created_at
        }

    @staticmethod
    async def generate_repository_doc(repo_id: int, doc_type: str, db: Session) -> Dict[str, Any]:
        """Generates README or Architecture Summary documentation using repository files."""
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        files = db.query(File).filter(File.repo_id == repo_id).all()
        
        file_paths = [f.path for f in files]
        file_tree_summary = "\n".join(file_paths[:100]) # First 100 files overview

        if doc_type == "readme":
            prompt = (
                f"Repository Name: {repo.name}\n"
                f"File Structure Overview:\n{file_tree_summary}\n\n"
                "Task: Generate a comprehensive, beautiful GitHub README.md for this repository. "
                "Include project overview, key features, directory breakdown, architecture pattern, and setup guide."
            )
        else: # architecture
            prompt = (
                f"Repository Name: {repo.name}\n"
                f"File Structure Overview:\n{file_tree_summary}\n\n"
                "Task: Generate a Senior Software Architecture Summary for this codebase. "
                "Detail system components, data flows, layer responsibilities, design patterns used, and key dependencies."
            )

        system_instruction = "You are a Principal Software Architect generating clear technical markdown documentation."
        doc_content = await gemini_client.generate_response(prompt, system_instruction)

        doc = GeneratedDoc(
            repo_id=repo_id,
            doc_type=doc_type,
            content=doc_content
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        return {
            "id": doc.id,
            "repo_id": doc.repo_id,
            "doc_type": doc.doc_type,
            "content": doc.content,
            "created_at": doc.created_at
        }
