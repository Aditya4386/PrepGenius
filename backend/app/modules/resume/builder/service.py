"""
service.py — Resume builder service layer (stateless, in-memory).
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from app.modules.resume.schemas import ResumeBuilderAnswerRequest, ResumeBuilderAnswerResponse
from app.modules.resume.builder.graph import resume_builder_graph, SECTION_ORDER
from app.shared.llm import LLMError

logger = logging.getLogger(__name__)

# In-memory session storage (replace with Redis in production)
_builder_sessions: Dict[str, Dict[str, Any]] = {}


def create_builder_session(
    student_id: str,
    job_title: str,
    job_description: str,
) -> Dict[str, Any]:
    """Create a new resume builder session."""
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    session = {
        "id": session_id,
        "student_id": student_id,
        "job_title": job_title,
        "job_description": job_description,
        "status": "in_progress",
        "current_section": SECTION_ORDER[0],
        "section_index": 0,
        "answers": [],
        "drafts": [],
        "approved_sections": [],
        "created_at": now,
        "updated_at": now,
    }
    _builder_sessions[session_id] = session
    return session


def get_builder_session(session_id: str, student_id: str) -> Optional[Dict[str, Any]]:
    """Get a builder session by ID."""
    session = _builder_sessions.get(session_id)
    if session and session.get("student_id") == student_id:
        return session
    return None


def get_active_builder_session(student_id: str) -> Optional[Dict[str, Any]]:
    """Get the active (in_progress) builder session for a student."""
    for session in _builder_sessions.values():
        if session.get("student_id") == student_id and session.get("status") == "in_progress":
            return session
    return None


def submit_answer(
    session_id: str,
    student_id: str,
    request: ResumeBuilderAnswerRequest,
) -> ResumeBuilderAnswerResponse:
    """Submit an answer and get the next question or draft."""
    session = get_builder_session(session_id, student_id)
    if not session:
        raise ValueError("Session not found")

    if session.get("status") != "in_progress":
        raise ValueError("Session is not active")

    # Add answer to session
    answers = session.get("answers", [])
    answers.append({
        "section": request.section,
        "answer": request.answer,
    })
    session["answers"] = answers

    # Prepare state for graph - include session state
    state = {
        "session_id": session_id,
        "student_id": student_id,
        "job_title": session["job_title"],
        "job_description": session["job_description"],
        "status": session["status"],
        "current_section": session["current_section"],
        "section_index": session.get("section_index", 0),
        "answers": answers,
        "drafts": session.get("drafts", []),
        "approved_sections": session.get("approved_sections", []),
        "job_keywords": session.get("job_keywords", []),
        "followup_counts": session.get("followup_counts", {}),
        "max_followups": 2,
        "error": None,
        "jd_parsed": session.get("jd_parsed", False),
    }

    # Run graph
    try:
        result = resume_builder_graph.invoke(state)
    except LLMError as e:
        logger.error("Builder graph failed: %s", e)
        raise ValueError(f"Builder failed: {e}")

    if result.get("error"):
        raise ValueError(result["error"])

    # Update session with result
    session["answers"] = result.get("answers", answers)
    session["drafts"] = result.get("drafts", [])
    session["approved_sections"] = result.get("approved_sections", [])
    session["current_section"] = result.get("current_section")
    session["section_index"] = result.get("section_index", 0)
    session["job_keywords"] = result.get("job_keywords", [])
    session["followup_counts"] = result.get("followup_counts", {})
    session["jd_parsed"] = result.get("jd_parsed", False)

    # Check if complete
    if result.get("final_resume"):
        session["status"] = "completed"
        session["final_resume"] = result.get("final_resume")
        session["keyword_coverage"] = result.get("keyword_coverage", {})

    # Build response
    current_section = result.get("current_section")
    drafts = result.get("drafts", [])
    latest_draft = None
    if drafts:
        for d in reversed(drafts):
            if d.get("section") == request.section:
                latest_draft = d.get("draft")
                break

    needs_followup = result.get("needs_followup", False)
    followup_question = result.get("followup_question")

    return ResumeBuilderAnswerResponse(
        section=request.section,
        draft=latest_draft or "",
        needs_followup=needs_followup,
        followup_question=followup_question,
    )


def approve_section(
    session_id: str,
    student_id: str,
    section: str,
    content: str,
) -> Dict[str, Any]:
    """Approve a drafted section (student can edit content before approving)."""
    session = get_builder_session(session_id, student_id)
    if not session:
        raise ValueError("Session not found")

    approved = session.get("approved_sections", [])
    # Update or add approved section
    found = False
    for a in approved:
        if a.get("section") == section:
            a["content"] = content
            found = True
            break
    if not found:
        approved.append({"section": section, "content": content})
    session["approved_sections"] = approved

    return {"message": "Section approved", "section": section}


def get_session_status(session_id: str, student_id: str) -> Dict[str, Any]:
    """Get current session status."""
    session = get_builder_session(session_id, student_id)
    if not session:
        raise ValueError("Session not found")

    return {
        "id": session["id"],
        "job_title": session["job_title"],
        "status": session["status"],
        "current_section": session["current_section"],
        "completed_sections": [a.get("section") for a in (session.get("approved_sections") or [])],
        "total_sections": len(SECTION_ORDER),
    }


def export_resume(session_id: str, student_id: str) -> str:
    """Get the final assembled resume text."""
    session = get_builder_session(session_id, student_id)
    if not session:
        raise ValueError("Session not found")

    if session.get("status") != "completed":
        raise ValueError("Resume not yet completed")

    return session.get("final_resume", "")