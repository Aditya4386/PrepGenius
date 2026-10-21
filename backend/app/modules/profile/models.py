import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Float,
    Date,
    Text,
    JSON,
    ForeignKey,
    Boolean,
)
from sqlalchemy.orm import relationship
from app.db.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class Student(Base):
    __tablename__ = "students"

    # User identifier (e.g. 'std_uuid' or Clerk 'sub' claim)
    id = Column(String(255), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # 1-to-1 relationship with StudentProfile
    profile = relationship(
        "StudentProfile",
        back_populates="student",
        uselist=False,
        cascade="all, delete-orphan",
    )


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(
        String(255),
        ForeignKey("students.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Career Target Configuration
    target_role = Column(String(100), nullable=True)
    company_type = Column(String(50), nullable=True)  # product, service, startup
    target_companies = Column(JSON, nullable=True, default=list)
    career_goal = Column(Text, nullable=True)

    # Planning & Feasibility Parameters
    weekly_study_hours = Column(Float, nullable=True, default=10.0)
    preparation_deadline = Column(Date, nullable=True)

    # Skills with proficiency levels [{"name": "Python", "level": "intermediate"}]
    skills = Column(JSON, nullable=True, default=list)

    # Academic History [{"institution": "...", "degree": "...", "year_of_completion": 2026, "cgpa": 8.5}]
    education = Column(JSON, nullable=True, default=list)

    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationship back to Student
    student = relationship("Student", back_populates="profile")
