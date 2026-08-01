import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.config import settings
from app.core.database import Base, is_sqlite

# Try importing Vector from pgvector if postgres (Gemini native embedding dimension = 3072)
if not is_sqlite:
    try:
        from pgvector.sqlalchemy import Vector
        EmbeddingColumn = Vector(settings.EMBEDDING_DIMENSION)
    except ImportError:
        EmbeddingColumn = Text
else:
    EmbeddingColumn = Text

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    repositories = relationship("Repository", back_populates="owner", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    status = Column(String, default="processing") # processing, ready, error
    file_count = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="repositories")
    files = relationship("File", back_populates="repository", cascade="all, delete-orphan")
    chunks = relationship("CodeChunk", back_populates="repository", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="repository", cascade="all, delete-orphan")
    docs = relationship("GeneratedDoc", back_populates="repository", cascade="all, delete-orphan")

class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    path = Column(String, nullable=False, index=True)
    extension = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    size_bytes = Column(Integer, default=0)

    repository = relationship("Repository", back_populates="files")
    chunks = relationship("CodeChunk", back_populates="file", cascade="all, delete-orphan")

class CodeChunk(Base):
    __tablename__ = "code_chunks"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    
    # Store embedding as Vector(3072) if pgvector, otherwise JSON text string.
    # Note: Gemini embedding vectors are 3072 dimensions natively.
    embedding = Column(EmbeddingColumn, nullable=True)

    file = relationship("File", back_populates="chunks")
    repository = relationship("Repository", back_populates="chunks")

    def set_embedding(self, vec_list: list):
        """
        Sets and validates the embedding vector for the code chunk.
        Gemini embedding vectors are 3072 dimensions natively.
        - For PostgreSQL: requires length == 3072.
        - For SQLite fallback: stores JSON string normally.
        """
        if vec_list is not None:
            if len(vec_list) != settings.EMBEDDING_DIMENSION:
                raise ValueError(
                    f"Invalid embedding dimension: expected {settings.EMBEDDING_DIMENSION}, got {len(vec_list)}"
                )
        if is_sqlite or isinstance(EmbeddingColumn, Text):
            self.embedding = json.dumps(vec_list) if vec_list is not None else None
        else:
            self.embedding = vec_list

    def get_embedding(self):
        if isinstance(self.embedding, str):
            try:
                return json.loads(self.embedding)
            except Exception:
                return []
        return self.embedding or []

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, default="New Conversation")
    created_at = Column(DateTime, default=datetime.utcnow)

    repository = relationship("Repository", back_populates="chat_sessions")
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String, nullable=False) # user or assistant
    content = Column(Text, nullable=False)
    sources = Column(Text, nullable=True) # JSON list of retrieved source citations
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")

class GeneratedDoc(Base):
    __tablename__ = "generated_docs"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    doc_type = Column(String, nullable=False) # readme or architecture
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    repository = relationship("Repository", back_populates="docs")
