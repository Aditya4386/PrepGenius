from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_student_id
from app.modules.profile.schemas import ProfileResponse, ProfileUpdate
from app.modules.profile.service import (
    get_student_profile,
    upsert_student_profile,
    is_profile_complete,
)

router = APIRouter(prefix="/profile", tags=["Profile"])


def _map_to_response(profile) -> ProfileResponse:
    return ProfileResponse(
        id=profile.id,
        student_id=profile.student_id,
        target_role=profile.target_role,
        company_type=profile.company_type,
        target_companies=profile.target_companies or [],
        career_goal=profile.career_goal,
        weekly_study_hours=profile.weekly_study_hours,
        preparation_deadline=profile.preparation_deadline,
        skills=profile.skills or [],
        education=profile.education or [],
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        is_profile_complete=is_profile_complete(profile),
    )


@router.get("", response_model=ProfileResponse)
def get_profile(
    student_id: str = Depends(get_current_student_id),
    db: Session = Depends(get_db),
):
    """
    Retrieve the profile for the authenticated student.
    Triggers just-in-time creation if this is the student's first API call.
    """
    profile = get_student_profile(db, student_id)
    return _map_to_response(profile)


@router.put("", response_model=ProfileResponse)
def update_profile(
    data: ProfileUpdate,
    student_id: str = Depends(get_current_student_id),
    db: Session = Depends(get_db),
):
    """
    Update profile details for the authenticated student.
    Strictly bound to authenticated student token; client-supplied IDs are ignored.
    """
    profile = upsert_student_profile(db, student_id, data)
    return _map_to_response(profile)
