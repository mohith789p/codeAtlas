from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, EmailStr

# Auth Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime

    class Config:
        from_attributes = True

# Repository Schemas
class RepositoryResponse(BaseModel):
    id: int
    name: str
    status: str
    file_count: int
    chunk_count: int
    created_at: datetime

    class Config:
        from_attributes = True

class FileResponse(BaseModel):
    id: int
    path: str
    extension: Optional[str]
    size_bytes: int
    content: Optional[str] = None

    class Config:
        from_attributes = True

class TreeNode(BaseModel):
    path: str
    name: str
    type: str # file or dir
    children: Optional[List['TreeNode']] = None

# Search Schemas
class SearchQuery(BaseModel):
    query: str
    top_k: int = 5

class ChunkResult(BaseModel):
    id: int
    file_path: str
    start_line: int
    end_line: int
    content: str
    score: float

# Chat Schemas
class CreateSessionRequest(BaseModel):
    repo_id: int
    title: Optional[str] = "New Conversation"

class ChatSessionResponse(BaseModel):
    id: int
    repo_id: int
    title: str
    created_at: datetime

    class Config:
        from_attributes = True

class ChatQueryRequest(BaseModel):
    session_id: int
    query: str

class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    sources: Optional[List[Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Doc Schemas
class GenerateDocRequest(BaseModel):
    repo_id: int
    doc_type: str # readme or architecture

class GeneratedDocResponse(BaseModel):
    id: int
    repo_id: int
    doc_type: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
