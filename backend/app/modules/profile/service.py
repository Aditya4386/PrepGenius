import uuid
from typing import Optional
from sqlalchemy.orm import Session
from app.modules.profile.models import Student, StudentProfile
from app.modules.profile.schemas import ProfileUpdate


def get_or_create_student(
    db: Session,
    student_id: str,
    email: Optional[str] = None,
) -> Student:
    """
    Just-In-Time (JIT) provisioning of student record upon first authenticated request.
    If the student record doesn't exist, create it along with an empty initial profile.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        student = Student(id=student_id, email=email)
        db.add(student)
        db.flush()

        # Initialize profile record for the new student
        profile = StudentProfile(
            id=str(uuid.uuid4()),
            student_id=student.id,
            target_role=None,
            company_type=None,
            target_companies=[],
            career_goal=None,
            weekly_study_hours=10.0,
            preparation_deadline=None,
            skills=[],
            education=[],
        )
        db.add(profile)
        db.commit()
        db.refresh(student)
    elif not student.profile:
        # Guarantee profile existence if student was somehow created without one
        profile = StudentProfile(
            id=str(uuid.uuid4()),
            student_id=student.id,
            target_role=None,
            company_type=None,
            target_companies=[],
            career_goal=None,
            weekly_study_hours=10.0,
            preparation_deadline=None,
            skills=[],
            education=[],
        )
        db.add(profile)
        db.commit()
        db.refresh(student)

    return student


def get_student_profile(db: Session, student_id: str) -> StudentProfile:
    """
    Retrieves the authenticated student's profile, triggering JIT creation if needed.
    """
    student = get_or_create_student(db, student_id)
    return student.profile


def upsert_student_profile(
    db: Session,
    student_id: str,
    data: ProfileUpdate,
    email: Optional[str] = None,
) -> StudentProfile:
    """
    Updates the authenticated student's profile. Strict data ownership is enforced
    via the authenticated student_id.
    """
    student = get_or_create_student(db, student_id, email=email)
    profile = student.profile

    if data.target_role is not None:
        profile.target_role = data.target_role.value if hasattr(data.target_role, "value") else str(data.target_role)

    if data.company_type is not None:
        profile.company_type = data.company_type.value if hasattr(data.company_type, "value") else str(data.company_type)

    if data.target_companies is not None:
        profile.target_companies = [c.strip() for c in data.target_companies if c.strip()]

    if data.career_goal is not None:
        profile.career_goal = data.career_goal.strip()

    if data.weekly_study_hours is not None:
        profile.weekly_study_hours = data.weekly_study_hours

    if data.preparation_deadline is not None:
        profile.preparation_deadline = data.preparation_deadline

    if data.skills is not None:
        profile.skills = [s.model_dump() for s in data.skills]

    if data.education is not None:
        profile.education = [e.model_dump() for e in data.education]

    db.commit()
    db.refresh(profile)
    return profile


def is_profile_complete(profile: StudentProfile) -> bool:
    """
    Determines if the student has provided the minimum necessary context for AI modules.
    """
    return bool(
        profile.target_role
        and profile.company_type
        and (profile.weekly_study_hours or 0) > 0
        and profile.skills
        and len(profile.skills) > 0
    )
