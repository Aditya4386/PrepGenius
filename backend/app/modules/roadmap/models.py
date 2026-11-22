"""
Roadmap SQLAlchemy models for TiDB persistence.

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
    Boolean,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from app.db.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(
        String(255),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    target_role = Column(String(100), nullable=False)
    total_estimated_hours = Column(Float, nullable=False, default=0.0)
    source = Column(String(20), nullable=False, default="generated")  # generated, adapted
    prompt_version = Column(String(50), nullable=True)
    model = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Unique constraint: one version per student
    __table_args__ = (
        UniqueConstraint("student_id", "version", name="uq_roadmap_student_version"),
        Index("ix_roadmap_student_active", "student_id", "is_active"),
    )

    phases = relationship(
        "RoadmapPhase",
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="RoadmapPhase.position",
    )
    adaptations = relationship(
        "RoadmapAdaptation",
        back_populates="roadmap",
        cascade="all, delete-orphan",
    )


class RoadmapPhase(Base):
    __tablename__ = "roadmap_phases"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    roadmap_id = Column(
        String(36),
        ForeignKey("roadmaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    roadmap = relationship("Roadmap", back_populates="phases")
    tasks = relationship(
        "RoadmapTask",
        back_populates="phase",
        cascade="all, delete-orphan",
        order_by="RoadmapTask.position",
    )


class RoadmapTask(Base):
    __tablename__ = "roadmap_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    roadmap_id = Column(
        String(36),
        ForeignKey("roadmaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phase_id = Column(
        String(36),
        ForeignKey("roadmap_phases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position = Column(Integer, nullable=False)
    title = Column(String(500), nullable=False)
    estimated_hours = Column(Float, nullable=False)
    success_criteria = Column(Text, nullable=False)
    topic_tags = Column(JSON, nullable=True, default=list)
    status = Column(String(20), nullable=False, default="pending")  # pending, completed
    completed_at = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    source = Column(String(20), nullable=False, default="generated")  # generated, interview, resume

    phase = relationship("RoadmapPhase", back_populates="tasks")


class RoadmapAdaptation(Base):
    __tablename__ = "roadmap_adaptations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    roadmap_id = Column(
        String(36),
        ForeignKey("roadmaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type = Column(String(20), nullable=False)  # interview, resume
    source_id = Column(String(100), nullable=False)
    proposed_tasks = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default="proposed")  # proposed, applied, rejected
    created_at = Column(DateTime, default=utc_now, nullable=False)

    roadmap = relationship("Roadmap", back_populates="adaptations")