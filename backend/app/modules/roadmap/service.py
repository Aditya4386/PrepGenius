"""
service.py — Roadmap service layer (stateless, in-memory).
"""

import json
import uuid
from datetime import datetime, date, timezone
from typing import Optional, List, Dict, Any

from app.modules.roadmap.schemas import (
    RoadmapGenerationRequest,
    RoadmapResponse,
    RoadmapTaskUpdate,
    TaskStatusEnum,
    RoadmapAdaptationAction,
    RoadmapPhaseResponse,
    RoadmapTaskResponse,
)
from app.modules.roadmap.graph import roadmap_generation_graph
from app.core.config import settings
from app.shared.llm import LLMError

import logging
logger = logging.getLogger(__name__)

# In-memory storage
_roadmaps: Dict[str, Dict[str, Any]] = {}  # student_id -> {roadmap_id -> roadmap_data}
_roadmap_phases: Dict[str, List[Dict[str, Any]]] = {}  # roadmap_id -> phases
_roadmap_tasks: Dict[str, List[Dict[str, Any]]] = {}  # roadmap_id -> tasks
_adaptations: Dict[str, Dict[str, Any]] = {}  # adaptation_id -> adaptation_data


def utc_now():
    return datetime.now(timezone.utc)


def calculate_planning_weeks(prep_deadline: Optional[date]) -> int:
    """Calculate planning weeks from deadline."""
    if prep_deadline:
        delta = prep_deadline - date.today()
        weeks = max(1, delta.days // 7)
        return min(weeks, 52)
    return 12


def get_active_roadmap(student_id: str) -> Optional[Dict[str, Any]]:
    """Get the active roadmap for a student."""
    student_roadmaps = _roadmaps.get(student_id, {})
    for roadmap in student_roadmaps.values():
        if roadmap.get("is_active"):
            return roadmap
    return None


def get_roadmap_by_id(roadmap_id: str, student_id: str) -> Optional[Dict[str, Any]]:
    """Get roadmap by ID."""
    student_roadmaps = _roadmaps.get(student_id, {})
    return student_roadmaps.get(roadmap_id)


def generate_roadmap(
    student_id: str,
    profile_data: Dict[str, Any],
    request: RoadmapGenerationRequest = None,
) -> RoadmapResponse:
    """
    Generate a new roadmap for the student.
    Creates a new version and makes it active.
    """
    # Validate profile
    if not profile_data:
        raise ValueError("Student profile not found. Please complete your profile first.")

    target_role = profile_data.get("target_role")
    company_type = profile_data.get("company_type")
    if not target_role or not company_type:
        raise ValueError("Target role and company type are required for roadmap generation.")

    # Check if there's an existing active roadmap
    existing = get_active_roadmap(student_id)
    if existing and not (request and request.force_regenerate):
        raise ValueError("Active roadmap exists. Use force_regenerate=true to create a new version.")

    # Prepare input for graph
    planning_weeks = calculate_planning_weeks(profile_data.get("preparation_deadline"))
    weekly_hours = profile_data.get("weekly_study_hours") or 10.0

    input_state = {
        "student_id": student_id,
        "target_role": target_role,
        "company_type": company_type,
        "skills": profile_data.get("skills") or [],
        "education": profile_data.get("education") or [],
        "weekly_hours": weekly_hours,
        "planning_weeks": planning_weeks,
        "prep_deadline": profile_data.get("preparation_deadline").isoformat() if profile_data.get("preparation_deadline") else None,
    }

    # Run the graph
    try:
        result = roadmap_generation_graph.invoke(input_state)
    except LLMError as e:
        logger.error("Roadmap generation failed: %s", e)
        raise ValueError(f"Roadmap generation failed: {e}")

    if result.get("error"):
        raise ValueError(result["error"])

    final_roadmap = result.get("final_roadmap")
    if not final_roadmap:
        raise ValueError("Roadmap generation did not produce a valid roadmap.")

    # Determine new version number
    new_version = 1
    student_roadmaps = _roadmaps.get(student_id, {})
    if existing:
        existing["is_active"] = False
        max_version = max((r["version"] for r in student_roadmaps.values()), default=0)
        new_version = max_version + 1

    # Create new roadmap
    roadmap_id = str(uuid.uuid4())
    total_hours = sum(
        t["estimated_hours"]
        for p in final_roadmap["phases"]
        for t in p["tasks"]
    )

    roadmap = {
        "id": roadmap_id,
        "student_id": student_id,
        "version": new_version,
        "is_active": True,
        "title": final_roadmap["title"],
        "target_role": final_roadmap["target_role"],
        "total_estimated_hours": total_hours,
        "source": "generated",
        "prompt_version": "v1",
        "model": settings.GROQ_MODEL,
        "created_at": utc_now(),
    }

    # Store phases and tasks in memory
    phases = []
    tasks = []
    for phase_data in final_roadmap["phases"]:
        phase_id = str(uuid.uuid4())
        phase = {
            "id": phase_id,
            "roadmap_id": roadmap_id,
            "position": phase_data["position"],
            "name": phase_data["name"],
            "description": phase_data.get("description"),
        }
        phases.append(phase)

        for task_data in phase_data["tasks"]:
            task_id = str(uuid.uuid4())
            task = {
                "id": task_id,
                "roadmap_id": roadmap_id,
                "phase_id": phase_id,
                "position": task_data["position"],
                "title": task_data["title"],
                "estimated_hours": task_data["estimated_hours"],
                "success_criteria": task_data["success_criteria"],
                "topic_tags": task_data.get("topic_tags", []),
                "status": TaskStatusEnum.PENDING.value,
                "completed_at": None,
                "due_date": task_data.get("due_date"),
                "source": "generated",
            }
            tasks.append(task)

    # Store in memory
    if student_id not in _roadmaps:
        _roadmaps[student_id] = {}
    _roadmaps[student_id][roadmap_id] = roadmap
    _roadmap_phases[roadmap_id] = phases
    _roadmap_tasks[roadmap_id] = tasks

    return map_roadmap_to_response(roadmap, phases, tasks)


def map_roadmap_to_response(roadmap: Dict[str, Any], phases: List[Dict[str, Any]], tasks: List[Dict[str, Any]]) -> RoadmapResponse:
    """Map roadmap dict to response schema."""
    phase_responses = []
    for phase in phases:
        phase_tasks = [t for t in tasks if t["phase_id"] == phase["id"]]
        phase_tasks.sort(key=lambda x: x["position"])

        task_responses = []
        for task in phase_tasks:
            task_responses.append({
                "id": task["id"],
                "roadmap_id": task["roadmap_id"],
                "phase_id": task["phase_id"],
                "position": task["position"],
                "title": task["title"],
                "estimated_hours": task["estimated_hours"],
                "success_criteria": task["success_criteria"],
                "topic_tags": task.get("topic_tags", []),
                "status": task["status"],
                "completed_at": task.get("completed_at"),
                "due_date": task.get("due_date"),
                "source": task["source"],
            })

        phase_responses.append({
            "id": phase["id"],
            "roadmap_id": phase["roadmap_id"],
            "position": phase["position"],
            "name": phase["name"],
            "description": phase.get("description"),
            "tasks": task_responses,
        })

    return RoadmapResponse(
        id=roadmap["id"],
        student_id=roadmap["student_id"],
        version=roadmap["version"],
        is_active=roadmap["is_active"],
        title=roadmap["title"],
        target_role=roadmap["target_role"],
        total_estimated_hours=roadmap["total_estimated_hours"],
        source=roadmap["source"],
        prompt_version=roadmap.get("prompt_version"),
        model=roadmap.get("model"),
        created_at=roadmap["created_at"],
        phases=phase_responses,
    )


def get_roadmap(student_id: str) -> Optional[RoadmapResponse]:
    """Get the active roadmap for a student."""
    roadmap = get_active_roadmap(student_id)
    if not roadmap:
        return None
    phases = _roadmap_phases.get(roadmap["id"], [])
    tasks = _roadmap_tasks.get(roadmap["id"], [])
    return map_roadmap_to_response(roadmap, phases, tasks)


def get_roadmap_history(student_id: str) -> List[RoadmapResponse]:
    """Get all roadmap versions for a student."""
    student_roadmaps = _roadmaps.get(student_id, {})
    roadmaps = list(student_roadmaps.values())
    roadmaps.sort(key=lambda x: x["version"], reverse=True)

    results = []
    for r in roadmaps:
        phases = _roadmap_phases.get(r["id"], [])
        tasks = _roadmap_tasks.get(r["id"], [])
        results.append(map_roadmap_to_response(r, phases, tasks))
    return results


def update_task_status(
    student_id: str,
    task_id: str,
    status: TaskStatusEnum,
) -> Optional[Dict[str, Any]]:
    """Update a task's status."""
    # Find the task across all student's roadmaps
    student_roadmaps = _roadmaps.get(student_id, {})
    for roadmap in student_roadmaps.values():
        if not roadmap.get("is_active"):
            continue
        roadmap_tasks = _roadmap_tasks.get(roadmap["id"], [])
        for task in roadmap_tasks:
            if task["id"] == task_id:
                task["status"] = status.value
                if status == TaskStatusEnum.COMPLETED:
                    task["completed_at"] = utc_now()
                else:
                    task["completed_at"] = None
                return task
    return None


def update_task_details(
    student_id: str,
    task_id: str,
    data: RoadmapTaskUpdate,
) -> Optional[Dict[str, Any]]:
    """Update task details."""
    student_roadmaps = _roadmaps.get(student_id, {})
    for roadmap in student_roadmaps.values():
        if not roadmap.get("is_active"):
            continue
        roadmap_tasks = _roadmap_tasks.get(roadmap["id"], [])
        for task in roadmap_tasks:
            if task["id"] == task_id:
                if data.title is not None:
                    task["title"] = data.title
                if data.estimated_hours is not None:
                    task["estimated_hours"] = data.estimated_hours
                if data.success_criteria is not None:
                    task["success_criteria"] = data.success_criteria
                if data.topic_tags is not None:
                    task["topic_tags"] = data.topic_tags
                if data.status is not None:
                    task["status"] = data.status.value
                    if data.status == TaskStatusEnum.COMPLETED:
                        task["completed_at"] = utc_now()
                    else:
                        task["completed_at"] = None
                if data.due_date is not None:
                    task["due_date"] = data.due_date
                return task
    return None


def get_completion_percentage(student_id: str) -> float:
    """Calculate roadmap completion percentage based on task hours."""
    roadmap = get_active_roadmap(student_id)
    if not roadmap or roadmap.get("total_estimated_hours", 0) == 0:
        return 0.0

    roadmap_tasks = _roadmap_tasks.get(roadmap["id"], [])
    completed_hours = sum(t["estimated_hours"] for t in roadmap_tasks if t["status"] == TaskStatusEnum.COMPLETED.value)
    return min(100.0, (completed_hours / roadmap["total_estimated_hours"]) * 100)


def create_adaptation_proposal(
    student_id: str,
    source_type: str,
    source_id: str,
    proposed_tasks: List[dict],
) -> Dict[str, Any]:
    """Create a roadmap adaptation proposal."""
    roadmap = get_active_roadmap(student_id)
    if not roadmap:
        raise ValueError("No active roadmap found")

    adaptation_id = str(uuid.uuid4())
    adaptation = {
        "id": adaptation_id,
        "roadmap_id": roadmap["id"],
        "source_type": source_type,
        "source_id": source_id,
        "proposed_tasks": proposed_tasks,
        "status": "proposed",
        "created_at": utc_now(),
    }
    _adaptations[adaptation_id] = adaptation
    return adaptation


def apply_adaptation(
    student_id: str,
    adaptation_id: str,
) -> Dict[str, Any]:
    """Apply an approved adaptation to the active roadmap."""
    adaptation = _adaptations.get(adaptation_id)
    if not adaptation:
        raise ValueError("Adaptation not found")

    if adaptation["status"] != "proposed":
        raise ValueError("Adaptation already processed")

    roadmap = get_roadmap_by_id(adaptation["roadmap_id"], student_id)
    if not roadmap:
        raise ValueError("Roadmap not found")

    roadmap_tasks = _roadmap_tasks.get(roadmap["id"], [])
    roadmap_phases = _roadmap_phases.get(roadmap["id"], [])

    if not roadmap_phases:
        raise ValueError("Roadmap has no phases")

    last_phase = max(roadmap_phases, key=lambda x: x["position"])
    next_task_position = len([t for t in roadmap_tasks if t["phase_id"] == last_phase["id"]]) + 1

    added_hours = 0
    for i, task_data in enumerate(adaptation["proposed_tasks"]):
        task = {
            "id": str(uuid.uuid4()),
            "roadmap_id": roadmap["id"],
            "phase_id": last_phase["id"],
            "position": next_task_position + i,
            "title": task_data["title"],
            "estimated_hours": task_data["estimated_hours"],
            "success_criteria": task_data["success_criteria"],
            "topic_tags": task_data.get("topic_tags", []),
            "status": TaskStatusEnum.PENDING.value,
            "completed_at": None,
            "due_date": None,
            "source": adaptation["source_type"],
        }
        roadmap_tasks.append(task)
        added_hours += task_data["estimated_hours"]

    roadmap["total_estimated_hours"] += added_hours
    adaptation["status"] = "applied"

    return roadmap


def reject_adaptation(
    student_id: str,
    adaptation_id: str,
) -> Dict[str, Any]:
    """Reject an adaptation proposal."""
    adaptation = _adaptations.get(adaptation_id)
    if not adaptation:
        raise ValueError("Adaptation not found")

    adaptation["status"] = "rejected"
    return adaptation