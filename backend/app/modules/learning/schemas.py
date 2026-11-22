"""
schemas.py — Pydantic schemas for Learning Assistant module.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class LearningAskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="Student's question")


class Citation(BaseModel):
    index: int
    title: str
    url: str
    page: Optional[int] = None
    excerpt: Optional[str] = None


class LearningResponse(BaseModel):
    answer: str
    route: Literal["knowledge_base", "web", "direct"]
    grounding: Literal["knowledge_base", "web", "none"]
    verified: bool
    insufficient_evidence: bool
    citations: List[Citation] = Field(default_factory=list)


class LearningQueryResponse(BaseModel):
    id: str
    student_id: str
    question: str
    route: str
    grounding: str
    verified: bool
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class LearningHistoryResponse(BaseModel):
    queries: List[LearningQueryResponse]
    total: int