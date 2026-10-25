"""
graph.py — LangGraph subgraph for resume builder (turn-based Q&A).

Fixed section order: contact, education, skills, projects, experience, achievements, summary

Key design principles:
- JD parsing happens ONCE at session start (not on every answer)
- Drafts are created but NOT auto-approved; student must explicitly approve via endpoint
- Follow-up counts are tracked per-section
- Student can edit drafts before approving
"""

import json
import logging
from typing import Dict, Any, List, Optional

from langgraph.graph import StateGraph, START, END

from app.modules.resume.builder.state import BuilderState
from app.modules.resume.builder.prompts import (
    PARSE_JD_PROMPT,
    GENERATE_QUESTION_PROMPT,
    CHECK_COMPLETENESS_PROMPT,
    DRAFT_SECTION_PROMPT,
    ASSEMBLE_RESUME_PROMPT,
)
from app.shared.llm import get_llm, LLMError
from app.modules.resume.schemas import ResumeBuilderAnswerResponse

logger = logging.getLogger(__name__)

SECTION_ORDER = [
    "contact",
    "education",
    "skills",
    "projects",
    "experience",
    "achievements",
    "summary",
]

SECTION_DISPLAY_NAMES = {
    "contact": "Contact Information",
    "education": "Education",
    "skills": "Technical Skills",
    "projects": "Projects",
    "experience": "Work Experience / Internships",
    "achievements": "Achievements",
    "summary": "Professional Summary",
}


def parse_job_description(state: BuilderState) -> Dict[str, Any]:
    """Parse job description to extract required skills and keywords. Runs ONCE per session."""
    logger.info("Parsing job description for keywords")
    llm = get_llm(temperature=0.1)

    prompt = PARSE_JD_PROMPT.format(
        job_title=state["job_title"],
        job_description=state["job_description"],
    )

    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        keywords = json.loads(content.strip())
        return {
            "job_keywords": keywords.get("keywords", []),
            "current_section": SECTION_ORDER[0],
            "section_index": 0,
            "jd_parsed": True,
        }
    except Exception as e:
        logger.error("JD parsing failed: %s", e)
        return {
            "job_keywords": [],
            "current_section": SECTION_ORDER[0],
            "section_index": 0,
            "jd_parsed": True,
        }


def generate_question(state: BuilderState) -> Dict[str, Any]:
    """Generate a targeted question for the current section."""
    logger.info("Generating question for section: %s", state["current_section"])
    llm = get_llm(temperature=0.3)

    section = state["current_section"]
    section_name = SECTION_DISPLAY_NAMES.get(section, section)
    previous_answers = state.get("answers", [])
    job_keywords = state.get("job_keywords", [])

    prompt = GENERATE_QUESTION_PROMPT.format(
        section_name=section_name,
        section=section,
        job_title=state["job_title"],
        job_keywords=", ".join(job_keywords),
        previous_answers=json.dumps(previous_answers, indent=2),
    )

    try:
        response = llm.invoke(prompt)
        question = response.content if hasattr(response, "content") else str(response)
        return {"drafts": state.get("drafts", []) + [{"section": section, "question": question.strip()}]}
    except Exception as e:
        logger.error("Question generation failed: %s", e)
        raise LLMError(f"Question generation failed: {e}") from e


def validate_answer(state: BuilderState) -> Dict[str, Any]:
    """Validate the student's answer (non-empty, minimum length)."""
    logger.info("Validating answer for section: %s", state["current_section"])
    answers = state.get("answers", [])
    if not answers:
        return {"error": "No answer provided"}

    latest_answer = answers[-1].get("answer", "").strip()
    if not latest_answer:
        return {"error": "Answer cannot be empty"}
    if len(latest_answer) < 10:
        return {"error": "Answer is too short. Please provide more detail."}

    return {}


def check_completeness(state: BuilderState) -> Dict[str, Any]:
    """Check if the answer is complete or needs follow-up."""
    logger.info("Checking completeness for section: %s", state["current_section"])
    llm = get_llm(temperature=0.1)

    section = state["current_section"]
    section_name = SECTION_DISPLAY_NAMES.get(section, section)
    latest_answer = state.get("answers", [])[-1].get("answer", "") if state.get("answers") else ""
    job_keywords = state.get("job_keywords", [])
    followup_counts = state.get("followup_counts", {})
    followup_count = followup_counts.get(section, 0)

    prompt = CHECK_COMPLETENESS_PROMPT.format(
        section_name=section_name,
        section=section,
        job_title=state["job_title"],
        job_keywords=", ".join(job_keywords),
        student_answer=latest_answer,
        followup_count=followup_count,
    )

    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        result = json.loads(content.strip())
        needs_followup = result.get("needs_followup", False)
        followup_question = result.get("followup_question")
        return {"needs_followup": needs_followup, "followup_question": followup_question}
    except Exception as e:
        logger.error("Completeness check failed: %s", e)
        return {"needs_followup": False, "followup_question": None}


def draft_section(state: BuilderState) -> Dict[str, Any]:
    """Draft the section from student's answers. Does NOT auto-approve."""
    logger.info("Drafting section: %s", state["current_section"])
    llm = get_llm(temperature=0.2)

    section = state["current_section"]
    section_name = SECTION_DISPLAY_NAMES.get(section, section)
    section_answers = [a for a in state.get("answers", []) if a.get("section") == section]
    job_keywords = state.get("job_keywords", [])

    prompt = DRAFT_SECTION_PROMPT.format(
        section_name=section_name,
        section=section,
        job_title=state["job_title"],
        job_keywords=", ".join(job_keywords),
        student_answers=json.dumps(section_answers, indent=2),
    )

    try:
        response = llm.invoke(prompt)
        draft = response.content if hasattr(response, "content") else str(response)
        drafts = state.get("drafts", [])
        drafts.append({"section": section, "draft": draft.strip()})
        # NOTE: We do NOT add to approved_sections here. Student must explicitly approve.
        return {"drafts": drafts}
    except Exception as e:
        logger.error("Section drafting failed: %s", e)
        raise LLMError(f"Section drafting failed: {e}") from e


def next_section_or_finish(state: BuilderState) -> str:
    """Determine next section or finish."""
    section_index = state.get("section_index", 0)
    if section_index + 1 < len(SECTION_ORDER):
        return "next_section"
    return "assemble"


def advance_section(state: BuilderState) -> Dict[str, Any]:
    """Advance to the next section, resetting followup count for the new section."""
    next_index = state.get("section_index", 0) + 1
    next_section = SECTION_ORDER[next_index]
    followup_counts = state.get("followup_counts", {})
    followup_counts[next_section] = 0
    return {
        "current_section": next_section,
        "section_index": next_index,
        "followup_counts": followup_counts,
    }


def assemble_resume(state: BuilderState) -> Dict[str, Any]:
    """Assemble final resume from APPROVED sections only."""
    logger.info("Assembling final resume")
    llm = get_llm(temperature=0.1)

    approved = state.get("approved_sections", [])
    job_keywords = state.get("job_keywords", [])

    prompt = ASSEMBLE_RESUME_PROMPT.format(
        job_title=state["job_title"],
        job_keywords=", ".join(job_keywords),
        approved_sections=json.dumps(approved, indent=2),
    )

    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        result = json.loads(content.strip())
        return {"final_resume": result.get("resume", ""), "keyword_coverage": result.get("keyword_coverage", {})}
    except Exception as e:
        logger.error("Resume assembly failed: %s", e)
        raise LLMError(f"Resume assembly failed: {e}") from e


def should_followup(state: BuilderState) -> str:
    """Route based on whether follow-up is needed."""
    if state.get("needs_followup", False):
        section = state.get("current_section")
        followup_counts = state.get("followup_counts", {})
        count = followup_counts.get(section, 0)
        if count < state.get("max_followups", 2):
            # Increment followup count for this section
            followup_counts[section] = count + 1
            return "followup"
    return "draft"


def should_parse_jd(state: BuilderState) -> str:
    """Route: parse JD only if not already parsed."""
    if state.get("jd_parsed", False):
        return "generate_question"
    return "parse_jd"


def create_builder_graph():
    """Build and compile the resume builder subgraph."""
    workflow = StateGraph(BuilderState)

    workflow.add_node("parse_jd", parse_job_description)
    workflow.add_node("generate_question", generate_question)
    workflow.add_node("validate_answer", validate_answer)
    workflow.add_node("check_completeness", check_completeness)
    workflow.add_node("draft_section", draft_section)
    workflow.add_node("advance_section", advance_section)
    workflow.add_node("assemble_resume", assemble_resume)

    # Start: check if JD already parsed
    workflow.add_edge(START, "parse_jd")

    # After parse_jd or skip, generate question
    workflow.add_conditional_edges(
        "parse_jd",
        should_parse_jd,
        {
            "parse_jd": "parse_jd",  # shouldn't happen but safe
            "generate_question": "generate_question",
        },
    )

    workflow.add_edge("generate_question", "validate_answer")
    workflow.add_edge("validate_answer", "check_completeness")

    workflow.add_conditional_edges(
        "check_completeness",
        should_followup,
        {
            "followup": "generate_question",
            "draft": "draft_section",
        },
    )

    workflow.add_edge("draft_section", "advance_section")

    workflow.add_conditional_edges(
        "advance_section",
        next_section_or_finish,
        {
            "next_section": "generate_question",
            "assemble": "assemble_resume",
        },
    )

    workflow.add_edge("assemble_resume", END)

    return workflow.compile()


resume_builder_graph = create_builder_graph()