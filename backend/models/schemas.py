from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, field_validator

class RepoCreate(BaseModel):
    github_url: str

    @field_validator("github_url")
    @classmethod
    def must_be_github_url(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        if not v.startswith("https://github.com/"):
            raise ValueError("URL must start with https://github.com/")
        parts = v.replace("https://github.com/", "").split("/")
        if len(parts) < 2 or not parts[0] or not parts[1]:
            raise ValueError("URL must be in the format https://github.com/owner/repo")
        return v

class RepoResponse(BaseModel):
    id: UUID
    github_url: str
    owner: str
    repo_name: str
    default_branch: str
    status: Literal["pending", "indexing", "ready", "failed"]
    error_message: Optional[str] = None
    file_count: Optional[int] = None
    chunk_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class IndexingStatus(BaseModel):
    id: UUID
    status: Literal["pending", "indexing", "ready", "failed"]
    file_count: Optional[int] = None
    chunk_count: Optional[int] = None
    error_message: Optional[str] = None

class QueryRequest(BaseModel):
    repo_id: UUID
    question: str
    top_k: int = 5

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("question must not be empty")
        return v

    @field_validator("top_k")
    @classmethod
    def top_k_in_range(cls, v: int) -> int:
        if not (1 <= v <= 20):
            raise ValueError("top_k must be between 1 and 20")
        return v

class ChunkCitation(BaseModel):
    id: UUID
    file_path: str
    start_line: int
    end_line: int
    language: Optional[str] = None
    content: str
    score: float

class QueryResponse(BaseModel):
    answer: str
    citations: list[ChunkCitation]

class ErrorResponse(BaseModel):
    detail: str
