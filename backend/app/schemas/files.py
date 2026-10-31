from pydantic import BaseModel, Field


class FileNode(BaseModel):
    name: str
    path: str
    type: str  # 'file' | 'directory'
    children: list["FileNode"] | None = None
    size: int | None = None


class FileTreeResponse(BaseModel):
    tree: list[FileNode]


class FileContentResponse(BaseModel):
    content: str
    language: str
    size: int | None = None
    encoding: str = "utf-8"
