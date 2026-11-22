"""
roadmap.py — API routes for roadmap module.
"""

from typing import List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_student_id
from app.db.session import get_db
from app.modules.profile.service import get_student_profile, is_profile_complete
from app.modules.roadmap.schemas import (
    RoadmapResponse,
    RoadmapGenerationRequest,
    RoadmapTaskUpdate,
    TaskStatusEnum,
    TaskCompletionRequest,
    RoadmapAdaptationAction,
    RoadmapAdaptationCreate,
)
from app.modules.roadmap.service import (
    generate_roadmap,
    get_roadmap,
    get_roadmap_history,
    update_task_status,
    update_task_details,
    get_completion_percentage,
    create_adaptation_proposal,
    apply_adaptation,
    reject_adaptation,
)

router = APIRouter(prefix="/roadmap", tags=["Roadmap"])


def _profile_to_dict(profile) -> dict:
    """Convert StudentProfile model to dict for roadmap generation."""
    return {
        "target_role": profile.target_role,
        "company_type": profile.company_type,
        "skills": profile.skills or [],
        "education": profile.education or [],
        "weekly_study_hours": profile.weekly_study_hours or 10.0,
        "preparation_deadline": profile.preparation_deadline,
    }


@router.post(
    "/generate",
    response_model=RoadmapResponse,
    summary="Generate a personalized roadmap",
    description="Generates a new roadmap based on the student's profile. Creates a new version and makes it active.",
)
def generate_roadmap_endpoint(
    request: RoadmapGenerationRequest = None,
    student_id: str = Depends(get_current_student_id),
    db: Session = Depends(get_db),
):
    try:
        # Get student's actual profile from database
        profile = get_student_profile(db, student_id)
        
        if not is_profile_complete(profile):
            raise HTTPException(
                status_code=400,
                detail="Profile incomplete. Please set target_role, company_type, skills, and weekly_study_hours before generating a roadmap."
            )
        
        profile_data = _profile_to_dict(profile)
        return generate_roadmap(student_id, profile_data, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate roadmap: {str(e)}")


@router.get(
    "",
    response_model=RoadmapResponse,
    summary="Get active roadmap",
    description="Retrieves the currently active roadmap for the authenticated student.",
)
def get_roadmap_endpoint(
    student_id: str = Depends(get_current_student_id),
):
    roadmap = get_roadmap(student_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="No active roadmap found. Generate one first.")
    return roadmap


@router.get(
    "/history",
    response_model=List[RoadmapResponse],
    summary="Get roadmap history",
    description="Retrieves all roadmap versions for the authenticated student.",
)
def get_roadmap_history_endpoint(
    student_id: str = Depends(get_current_student_id),
):
    return get_roadmap_history(student_id)


@router.get(
    "/completion",
    summary="Get roadmap completion percentage",
    description="Returns the completion percentage based on completed task hours.",
)
def get_completion_endpoint(
    student_id: str = Depends(get_current_student_id),
):
    percentage = get_completion_percentage(student_id)
    return {"completion_percentage": round(percentage, 2)}


@router.patch(
    "/tasks/{task_id}/status",
    summary="Update task completion status",
    description="Mark a task as completed or pending.",
)
def update_task_status_endpoint(
    task_id: str,
    request: TaskCompletionRequest,
    student_id: str = Depends(get_current_student_id),
):
    task = update_task_status(student_id, task_id, request.status)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task status updated", "task_id": task_id, "status": request.status.value}


@router.patch(
    "/tasks/{task_id}",
    summary="Update task details",
    description="Update task title, hours, success criteria, topic tags, or due date.",
)
def update_task_endpoint(
    task_id: str,
    data: RoadmapTaskUpdate,
    student_id: str = Depends(get_current_student_id),
):
    task = update_task_details(student_id, task_id, data)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task updated", "task_id": task_id}


@router.post(
    "/adaptations",
    summary="Create adaptation proposal",
    description="Create a roadmap adaptation proposal from interview or resume analysis.",
)
def create_adaptation_endpoint(
    data: RoadmapAdaptationCreate,
    student_id: str = Depends(get_current_student_id),
):
    try:
        adaptation = create_adaptation_proposal(student_id, data.source_type, data.source_id, data.proposed_tasks)
        return {
            "id": adaptation["id"],
            "roadmap_id": adaptation["roadmap_id"],
            "source_type": adaptation["source_type"],
            "source_id": adaptation["source_id"],
            "proposed_tasks": adaptation["proposed_tasks"],
            "status": adaptation["status"],
            "created_at": adaptation["created_at"],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/adaptations",
    summary="Get adaptation proposals",
    description="Retrieve all adaptation proposals for the active roadmap.",
)
def get_adaptations_endpoint(
    student_id: str = Depends(get_current_student_id),
):
    roadmap = get_roadmap(student_id)
    if not roadmap:
        return []
    
    # Get adaptations from in-memory storage
    from app.modules.roadmap.service import _adaptations
    roadmap_id = roadmap.id
    adaptations = [a for a in _adaptations.values() if a.get("roadmap_id") == roadmap_id]
    adaptations.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return [
        {
            "id": a["id"],
            "roadmap_id": a["roadmap_id"],
            "source_type": a["source_type"],
            "source_id": a["source_id"],
            "proposed_tasks": a["proposed_tasks"],
            "status": a["status"],
            "created_at": a["created_at"],
        }
        for a in adaptations
    ]


@router.post(
    "/adaptations/{adaptation_id}/action",
    summary="Approve or reject adaptation",
    description="Approve to apply proposed tasks to roadmap, or reject.",
)
def adaptation_action_endpoint(
    adaptation_id: str,
    action: RoadmapAdaptationAction,
    student_id: str = Depends(get_current_student_id),
):
    try:
        if action.action == "approve":
            apply_adaptation(student_id, adaptation_id)
            return {"message": "Adaptation applied successfully"}
        else:
            reject_adaptation(student_id, adaptation_id)
            return {"message": "Adaptation rejected"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))