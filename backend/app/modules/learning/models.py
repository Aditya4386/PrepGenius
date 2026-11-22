"""
Learning/Knowledge Base SQLAlchemy models for TiDB persistence.

Matches the database design in docs/PrepGenius_Roadmap_v2.md §17.
Uses TiDB VECTOR(384) column with cosine distance index.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Integer,
    Text,
    JSON,
    ForeignKey,
    Index,
    func,
)
from sqlalchemy.orm import relationship
from app.db.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class KBDocument(Base):
    __tablename__ = "kb_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(500), nullable=False)
    source_url = Column(String(1000), nullable=True)
    license = Column(String(100), nullable=True)
    version = Column(String(50), nullable=True)
    content_hash = Column(String(64), nullable=False, index=True)  # SHA-256 for idempotent upsert
    indexed_at = Column(DateTime, default=utc_now, nullable=False)

    chunks = relationship(
        "KBChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class KBChunk(Base):
    __tablename__ = "kb_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(
        String(36),
        ForeignKey("kb_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index = Column(Integer, nullable=False)
    page = Column(Integer, nullable=True)
    text = Column(Text, nullable=False)
    chunk_metadata = Column(JSON, nullable=True, default=dict)
    # TiDB VECTOR(384) column for embeddings
    embedding = Column(Text, nullable=True)  # Stored as JSON array string; TiDB VECTOR type via raw DDL

    document = relationship("KBDocument", back_populates="chunks")

    __table_args__ = (
        Index("ix_kb_chunk_document_index", "document_id", "chunk_index"),
    )


class LearningQuery(Base):
    __tablename__ = "learning_queries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(
        String(255),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question = Column(Text, nullable=False)
    route = Column(String(20), nullable=False)  # knowledge_base, web, direct
    grounding = Column(String(20), nullable=False)  # knowledge_base, web, none
    verified = Column(String(10), nullable=False)  # true, false
    answer = Column(Text, nullable=False)
    citations = Column(JSON, nullable=True, default=list)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_learning_query_student_created", "student_id", "created_at"),
    )