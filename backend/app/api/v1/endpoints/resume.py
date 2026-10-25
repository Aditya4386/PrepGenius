"""
resume.py — The resume analysis and builder endpoints (stateless).

Accepts a PDF file + optional job info, runs the analysis pipeline,
and returns a structured JSON response.
"""

import logging
from typing import Optional, Annotated
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Depends, Response

from app.core.config import settings
from app.core.security import get_current_student_id
from app.modules.resume.schemas import (
    AnalysisResponse,
    ResumeBuilderSessionResponse,
    ResumeBuilderAnswerRequest,
    ResumeBuilderAnswerResponse,
)
from app.modules.resume.analyzer.parser import validate_and_extract_text, PDFParseError
from app.modules.resume.analyzer.service import analyze_resume
from app.modules.resume.builder.service import (
    create_builder_session,
    get_builder_session,
    get_active_builder_session,
    submit_answer,
    approve_section,
    get_session_status,
    export_resume,
)
from app.modules.resume.exporter.exporter import create_resume_pdf
from app.shared.llm import LLMError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resumes", tags=["Resume Analysis"])


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    summary="Analyze a resume PDF",
    description=(
        "Upload a PDF resume and optionally supply a target job title and/or "
        "job description. Returns a structured analysis including section scores, "
        "ATS readiness, strengths, weaknesses, and recommendations."
    ),
)
async def analyze_resume_endpoint(
    resume: Annotated[UploadFile, File(description="PDF resume file (max 5 MB)")],
    job_title: Annotated[Optional[str], Form(description="Target job title (optional)")] = None,
    job_description: Annotated[Optional[str], Form(description="Target job description (optional)")] = None,
    student_id: str = Depends(get_current_student_id),
):
    try:
        file_bytes = await resume.read()
    except Exception as e:
        logger.error("Failed to read uploaded file: %s", e)
        raise HTTPException(status_code=400, detail="Could not read the uploaded file.")

    try:
        resume_text = validate_and_extract_text(file_bytes, settings.max_upload_size_bytes)
    except PDFParseError as e:
        raise HTTPException(status_code=422, detail=str(e))

    clean_job_title = job_title.strip() if job_title and job_title.strip() else None
    clean_job_description = job_description.strip() if job_description and job_description.strip() else None

    if len(resume_text) > settings.MAX_TEXT_CHARS_FOR_PROMPT:
        resume_text = resume_text[:settings.MAX_TEXT_CHARS_FOR_PROMPT]
        logger.info("Resume text truncated to %d characters for analysis pipeline.", settings.MAX_TEXT_CHARS_FOR_PROMPT)

    try:
        result = analyze_resume(
            resume_text=resume_text,
            job_title=clean_job_title,
            job_description=clean_job_description,
        )
    except LLMError as e:
        logger.error("Groq API error: %s", e)
        raise HTTPException(
            status_code=503,
            detail="The AI analysis service is temporarily unavailable. Please try again later.",
        )
    except ValueError as e:
        logger.error("Analysis result validation failed: %s", e)
        raise HTTPException(
            status_code=502,
            detail="Received an unexpected response from the AI service.",
        )

    return result


@router.get(
    "/analyses",
    summary="Get resume analysis history",
    description="Retrieve all resume analyses for the authenticated student. (In-memory: returns empty list)",
)
def get_resume_analyses(
    student_id: str = Depends(get_current_student_id),
):
    # In-memory mode: no persistence
    return []


@router.get(
    "/analyses/{analysis_id}",
    summary="Get a specific resume analysis",
    description="Retrieve a specific resume analysis by ID. (In-memory: not available)",
)
def get_resume_analysis(
    analysis_id: str,
    student_id: str = Depends(get_current_student_id),
):
    raise HTTPException(status_code=404, detail="Analysis not found (in-memory mode)")


# ============================================================================
# RESUME BUILDER ENDPOINTS
# ============================================================================

@router.post(
    "/builder/start",
    response_model=ResumeBuilderSessionResponse,
    summary="Start a new resume builder session",
    description="Create a new guided resume builder session with job title and description.",
)
def start_builder_session(
    job_title: Annotated[str, Form(description="Target job title")],
    job_description: Annotated[str, Form(description="Target job description")],
    student_id: str = Depends(get_current_student_id),
):
    session = create_builder_session(student_id, job_title, job_description)
    return session


@router.get(
    "/builder/session",
    response_model=ResumeBuilderSessionResponse,
    summary="Get active builder session",
    description="Get the current in-progress builder session for the student.",
)
def get_builder_session_endpoint(
    student_id: str = Depends(get_current_student_id),
):
    session = get_active_builder_session(student_id)
    if not session:
        raise HTTPException(status_code=404, detail="No active builder session found")
    return session


@router.get(
    "/builder/sessions/{session_id}",
    response_model=ResumeBuilderSessionResponse,
    summary="Get builder session by ID",
    description="Retrieve a specific builder session by ID.",
)
def get_builder_session_by_id(
    session_id: str,
    student_id: str = Depends(get_current_student_id),
):
    session = get_builder_session(session_id, student_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post(
    "/builder/sessions/{session_id}/answer",
    response_model=ResumeBuilderAnswerResponse,
    summary="Submit answer to builder question",
    description="Submit an answer for the current section. Returns next question or drafted section.",
)
def submit_builder_answer(
    session_id: str,
    request: ResumeBuilderAnswerRequest,
    student_id: str = Depends(get_current_student_id),
):
    try:
        return submit_answer(session_id, student_id, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/builder/sessions/{session_id}/approve",
    summary="Approve a drafted section",
    description="Approve a drafted section (student can edit content before approving).",
)
def approve_builder_section(
    session_id: str,
    section: Annotated[str, Form(description="Section name")],
    content: Annotated[str, Form(description="Approved content (can be edited draft)")],
    student_id: str = Depends(get_current_student_id),
):
    try:
        return approve_section(session_id, student_id, section, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/builder/sessions/{session_id}/status",
    summary="Get builder session status",
    description="Get current progress status of the builder session.",
)
def get_builder_status(
    session_id: str,
    student_id: str = Depends(get_current_student_id),
):
    try:
        return get_session_status(session_id, student_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/builder/sessions/{session_id}/export",
    summary="Export completed resume as PDF",
    description="Export the final assembled resume as an ATS-friendly PDF.",
)
def export_builder_resume(
    session_id: str,
    student_id: str = Depends(get_current_student_id),
):
    try:
        resume_text = export_resume(session_id, student_id)
        pdf_bytes = create_resume_pdf(resume_text)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="resume_{session_id}.pdf"'}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/builder/sessions/{session_id}/export-text",
    summary="Export completed resume as text",
    description="Get the final assembled resume as plain text.",
)
def export_builder_resume_text(
    session_id: str,
    student_id: str = Depends(get_current_student_id),
):
    try:
        resume_text = export_resume(session_id, student_id)
        return {"resume_text": resume_text}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))