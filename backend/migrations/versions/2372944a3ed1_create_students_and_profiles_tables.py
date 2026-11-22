"""create_students_and_profiles_tables

Revision ID: 2372944a3ed1
Revises: 
Create Date: 2026-10-21 15:28:18.120589

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2372944a3ed1'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Students table
    op.create_table(
        "students",
        sa.Column("id", sa.String(255), primary_key=True, index=True),
        sa.Column("email", sa.String(255), unique=True, index=True, nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Student profiles table
    op.create_table(
        "student_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(255), sa.ForeignKey("students.id", ondelete="CASCADE"), unique=True, nullable=False, index=True),
        sa.Column("target_role", sa.String(100), nullable=True),
        sa.Column("company_type", sa.String(50), nullable=True),
        sa.Column("target_companies", sa.JSON(), nullable=True),
        sa.Column("career_goal", sa.Text(), nullable=True),
        sa.Column("weekly_study_hours", sa.Float(), nullable=True, default=10.0),
        sa.Column("preparation_deadline", sa.Date(), nullable=True),
        sa.Column("skills", sa.JSON(), nullable=True),
        sa.Column("education", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Roadmaps table
    op.create_table(
        "roadmaps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(255), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=False, nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("target_role", sa.String(100), nullable=False),
        sa.Column("total_estimated_hours", sa.Float(), nullable=False, default=0.0),
        sa.Column("source", sa.String(20), nullable=False, default="generated"),
        sa.Column("prompt_version", sa.String(50), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_roadmap_student_version", "roadmaps", ["student_id", "version"])
    op.create_index("ix_roadmap_student_active", "roadmaps", ["student_id", "is_active"])

    # Roadmap phases table
    op.create_table(
        "roadmap_phases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("roadmap_id", sa.String(36), sa.ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )

    # Roadmap tasks table
    op.create_table(
        "roadmap_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("roadmap_id", sa.String(36), sa.ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("phase_id", sa.String(36), sa.ForeignKey("roadmap_phases.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("estimated_hours", sa.Float(), nullable=False),
        sa.Column("success_criteria", sa.Text(), nullable=False),
        sa.Column("topic_tags", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, default="pending"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(20), nullable=False, default="generated"),
    )

    # Roadmap adaptations table
    op.create_table(
        "roadmap_adaptations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("roadmap_id", sa.String(36), sa.ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("proposed_tasks", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="proposed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Resume analyses table
    op.create_table(
        "resume_analyses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(255), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("job_title", sa.String(255), nullable=True),
        sa.Column("job_description", sa.Text(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("sections", sa.JSON(), nullable=True),
        sa.Column("deterministic_checks", sa.JSON(), nullable=True),
        sa.Column("section_scores", sa.JSON(), nullable=True),
        sa.Column("resume_score", sa.Integer(), nullable=True),
        sa.Column("score_breakdown", sa.JSON(), nullable=True),
        sa.Column("feedback", sa.JSON(), nullable=True),
        sa.Column("improved_content", sa.JSON(), nullable=True),
        sa.Column("prompt_version", sa.String(50), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resume_analysis_student_created", "resume_analyses", ["student_id", "created_at"])

    # Resume builder sessions table
    op.create_table(
        "resume_builder_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(255), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("job_title", sa.String(255), nullable=False),
        sa.Column("job_description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="in_progress"),
        sa.Column("current_section", sa.String(50), nullable=True),
        sa.Column("answers", sa.JSON(), nullable=True),
        sa.Column("drafts", sa.JSON(), nullable=True),
        sa.Column("approved_sections", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resume_builder_student_status", "resume_builder_sessions", ["student_id", "status"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_resume_builder_student_status", table_name="resume_builder_sessions")
    op.drop_table("resume_builder_sessions")
    op.drop_index("ix_resume_analysis_student_created", table_name="resume_analyses")
    op.drop_table("resume_analyses")
    op.drop_table("roadmap_adaptations")
    op.drop_table("roadmap_tasks")
    op.drop_table("roadmap_phases")
    op.drop_index("ix_roadmap_student_active", table_name="roadmaps")
    op.drop_constraint("uq_roadmap_student_version", "roadmaps", type_="unique")
    op.drop_table("roadmaps")
    op.drop_table("student_profiles")
    op.drop_table("students")