"""
resume_analyzer.py — Dispatches resume analysis through the LangGraph workflow.
"""

import logging
from typing import Optional

from app.modules.resume.schemas import AnalysisResponse
from app.modules.resume.analyzer.graph import resume_analysis_graph
from app.shared.llm import LLMError

logger = logging.getLogger(__name__)


def _determine_analysis_mode(job_title: Optional[str], job_description: Optional[str]) -> str:
    """Return a human-readable label for which analysis scenario applies."""
    if job_title and job_description:
        return "full"
    elif job_description:
        return "job_description"
    elif job_title:
        return "job_title_only"
    else:
        return "general"


def analyze_resume(
    resume_text: str,
    job_title: Optional[str] = None,
    job_description: Optional[str] = None,
) -> AnalysisResponse:
    """
    Executes the multi-agent LangGraph resume analysis pipeline.

    Args:
        resume_text: Plain text extracted from the uploaded PDF.
        job_title: Optional target job title.
        job_description: Optional target job description.

    Returns:
        AnalysisResponse: The validated analysis result from the graph.

    Raises:
        LLMError: If any LLM agent node encounters an unrecoverable failure.
        ValueError: If graph state does not produce a valid final response.
    """
    mode = _determine_analysis_mode(job_title, job_description)

    initial_state = {
        "resume_text": resume_text,
        "job_title": job_title,
        "job_description": job_description,
        "analysis_mode": mode,
        "ats_score": 0,
        "ats_observations": [],
        "section_analysis": [],
        "overall_strengths": [],
        "overall_weaknesses": [],
        "missing_information": [],
        "job_match_score": None,
        "job_match_analysis": None,
        "overall_score": 0,
        "recommendations": [],
        "final_response": None,
    }

    logger.info("Invoking LangGraph resume analysis workflow with mode: %s", mode)
    final_state = resume_analysis_graph.invoke(initial_state)

    final_response = final_state.get("final_response")
    if not final_response:
        raise ValueError("LangGraph execution completed without producing a final_response.")

    return final_response