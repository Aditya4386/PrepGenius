"""
Resume SQLAlchemy models for TiDB persistence.

Matches the database design in docs/PrepGenius_Roadmap_v2.md §17.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Float,
    Integer,
    Text,
    JSON,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from app.db.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class ResumeAnalysis(Base):
    __tablename__ = "resume_analyses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(
        String(255),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_title = Column(String(255), nullable=True)
    job_description = Column(Text, nullable=True)
    extracted_text = Column(Text, nullable=True)  # redacted
    sections = Column(JSON, nullable=True, default=list)
    deterministic_checks = Column(JSON, nullable=True, default=list)
    section_scores = Column(JSON, nullable=True, default=list)
    resume_score = Column(Integer, nullable=True)
    score_breakdown = Column(JSON, nullable=True, default=dict)
    feedback = Column(JSON, nullable=True, default=list)
    improved_content = Column(JSON, nullable=True, default=dict)
    prompt_version = Column(String(50), nullable=True)
    model = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_resume_analysis_student_created", "student_id", "created_at"),
    )


class ResumeBuilderSession(Base):
    __tablename__ = "resume_builder_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(
        String(255),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_title = Column(String(255), nullable=False)
    job_description = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="in_progress")  # in_progress, completed, abandoned
    current_section = Column(String(50), nullable=True)
    answers = Column(JSON, nullable=True, default=list)
    drafts = Column(JSON, nullable=True, default=list)
    approved_sections = Column(JSON, nullable=True, default=list)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_resume_builder_student_status", "student_id", "status"),
    )