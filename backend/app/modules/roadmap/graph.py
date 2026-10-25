"""
graph.py — LangGraph subgraph for personalized roadmap generation.
"""

import json
import logging
from typing import Dict, Any, Optional, TypedDict, List

from langgraph.graph import StateGraph, START, END

from app.modules.roadmap.schemas import RoadmapTask
from app.modules.roadmap.feasibility import check_feasibility, FeasibilityViolation, repair_plan_prompt
from app.modules.roadmap.prompts import ROLE_TEMPLATE_PROMPT, REPAIR_PROMPT, ANALYZE_GAPS_PROMPT
from app.shared.llm import get_llm, LLMError
from app.core.config import settings

logger = logging.getLogger(__name__)


class RoadmapState(TypedDict):
    student_id: str
    target_role: str
    company_type: str
    skills: List[Dict[str, Any]]
    education: List[Dict[str, Any]]
    weekly_hours: float
    planning_weeks: int
    prep_deadline: Optional[str]

    role_template: Dict[str, Any]
    skill_gaps: Dict[str, Any]
    roadmap_draft: Dict[str, Any]
    feasibility_violations: List[FeasibilityViolation]
    retry_count: int
    final_roadmap: Optional[Dict[str, Any]]
    error: Optional[str]


def load_role_template(state: RoadmapState) -> Dict[str, Any]:
    """Load and adjust role template based on company type."""
    logger.info("Loading role template for %s (%s)", state["target_role"], state["company_type"])

    role_file_map = {
        "Backend Developer": "backend_developer.json",
        "Full-Stack Developer": "full_stack_developer.json",
        "Data Analyst": "data_analyst.json",
        "AI/ML Engineer": "ai_ml_engineer.json",
    }

    filename = role_file_map.get(state["target_role"], "backend_developer.json")
    import os
    template_path = os.path.join(
        os.path.dirname(__file__), "role_templates", filename
    )

    with open(template_path, "r") as f:
        template = json.load(f)

    # Apply company type adjustments
    company_type = state["company_type"] or "product"
    adjustments = template.get("company_type_adjustments", {}).get(company_type, {})
    template["company_emphasis"] = adjustments.get("emphasis", [])
    template["additional_topics"] = adjustments.get("additional_topics", [])

    return {"role_template": template}


def analyze_gaps(state: RoadmapState) -> Dict[str, Any]:
    """Analyze skill gaps using LLM."""
    logger.info("Analyzing skill gaps")
    llm = get_llm(temperature=0.1)

    role_template = state["role_template"]
    role_requirements = {
        "core_topics": role_template.get("core_topics", []),
        "skills": role_template.get("skills", []),
        "company_emphasis": role_template.get("company_emphasis", []),
    }

    prompt = ANALYZE_GAPS_PROMPT.format(
        target_role=state["target_role"],
        company_type=state["company_type"],
        skills=json.dumps(state["skills"]),
        education=json.dumps(state["education"]),
        role_requirements=json.dumps(role_requirements, indent=2),
    )

    try:
        response = llm.invoke(prompt)
        # Parse JSON from response
        content = response.content if hasattr(response, "content") else str(response)
        # Extract JSON from markdown if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        gaps = json.loads(content.strip())
        return {"skill_gaps": gaps}
    except Exception as e:
        logger.error("Gap analysis failed: %s", e)
        # Fallback to simple heuristic
        student_skills = {s["name"].lower() for s in state["skills"]}
        required_skills = {s["name"].lower() for s in role_template.get("skills", [])}
        missing = required_skills - student_skills
        return {
            "skill_gaps": {
                "critical_gaps": list(missing)[:5],
                "moderate_gaps": [],
                "strengths": list(student_skills & required_skills),
                "priority_topics": role_template.get("core_topics", [])[:5],
            }
        }


def generate_plan(state: RoadmapState) -> Dict[str, Any]:
    """Generate roadmap plan using LLM."""
    logger.info("Generating roadmap plan")
    llm = get_llm(temperature=0.2)

    role_template = state["role_template"]
    skill_gaps = state["skill_gaps"]
    weekly_hours = state["weekly_hours"]
    planning_weeks = state["planning_weeks"]
    max_hours = weekly_hours * planning_weeks

    prompt = ROLE_TEMPLATE_PROMPT.format(
        target_role=state["target_role"],
        company_type=state["company_type"],
        skills=json.dumps(state["skills"]),
        weekly_hours=weekly_hours,
        planning_weeks=planning_weeks,
        prep_deadline=state.get("prep_deadline", "Not specified"),
        role_template=json.dumps(role_template, indent=2),
        max_hours=max_hours,
        company_emphasis=", ".join(role_template.get("company_emphasis", [])),
    )

    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        roadmap = json.loads(content.strip())
        return {"roadmap_draft": roadmap, "retry_count": 0}
    except Exception as e:
        logger.error("Plan generation failed: %s", e)
        raise LLMError(f"Roadmap generation failed: {e}") from e


def validate_schema(state: RoadmapState) -> Dict[str, Any]:
    """Validate roadmap schema."""
    logger.info("Validating roadmap schema")
    roadmap = state["roadmap_draft"]

    required_keys = ["title", "target_role", "phases"]
    for key in required_keys:
        if key not in roadmap:
            raise ValueError(f"Missing required key: {key}")

    if not isinstance(roadmap["phases"], list) or len(roadmap["phases"]) == 0:
        raise ValueError("Phases must be a non-empty list")

    for i, phase in enumerate(roadmap["phases"]):
        if "name" not in phase or "tasks" not in phase:
            raise ValueError(f"Phase {i} missing name or tasks")
        if not isinstance(phase["tasks"], list):
            raise ValueError(f"Phase {i} tasks must be a list")

    return {}


def check_feasibility_node(state: RoadmapState) -> Dict[str, Any]:
    """Check roadmap feasibility."""
    logger.info("Checking roadmap feasibility")
    roadmap = state["roadmap_draft"]
    role_template = state["role_template"]
    weekly_hours = state["weekly_hours"]
    planning_weeks = state["planning_weeks"]

    violations = check_feasibility(roadmap, weekly_hours, planning_weeks, role_template)
    return {"feasibility_violations": violations}


def should_retry(state: RoadmapState) -> str:
    """Decide whether to retry or fail."""
    violations = state["feasibility_violations"]
    retry_count = state.get("retry_count", 0)

    error_violations = [v for v in violations if v.severity == "error"]
    if not error_violations:
        return "persist"
    if retry_count >= 2:
        return "fail"
    return "repair"


def repair_plan(state: RoadmapState) -> Dict[str, Any]:
    """Repair roadmap based on violations."""
    logger.info("Repairing roadmap (attempt %d)", state.get("retry_count", 0) + 1)
    llm = get_llm(temperature=0.2)

    violations = state["feasibility_violations"]
    roadmap = state["roadmap_draft"]
    weekly_hours = state["weekly_hours"]
    planning_weeks = state["planning_weeks"]
    max_hours = weekly_hours * planning_weeks

    error_violations = [v for v in violations if v.severity == "error"]
    prompt = REPAIR_PROMPT.format(
        violations="\n".join(f"- {v.code}: {v.message}" for v in error_violations),
        current_roadmap=json.dumps(roadmap, indent=2),
        max_hours=max_hours,
    )

    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        repaired = json.loads(content.strip())
        return {"roadmap_draft": repaired, "retry_count": retry_count + 1}
    except Exception as e:
        logger.error("Repair failed: %s", e)
        raise LLMError(f"Roadmap repair failed: {e}") from e


def fail_generation(state: RoadmapState) -> Dict[str, Any]:
    """Handle generation failure."""
    violations = state["feasibility_violations"]
    error_msgs = [v.message for v in violations if v.severity == "error"]
    error = "Roadmap generation failed after retries: " + "; ".join(error_msgs)
    logger.error(error)
    return {"error": error}


def persist_roadmap(state: RoadmapState) -> Dict[str, Any]:
    """Mark roadmap as ready for persistence (actual persistence in service)."""
    logger.info("Roadmap ready for persistence")
    return {"final_roadmap": state["roadmap_draft"]}


def create_roadmap_graph():
    """Build and compile the roadmap generation subgraph."""
    workflow = StateGraph(RoadmapState)

    workflow.add_node("load_role_template", load_role_template)
    workflow.add_node("analyze_gaps", analyze_gaps)
    workflow.add_node("generate_plan", generate_plan)
    workflow.add_node("validate_schema", validate_schema)
    workflow.add_node("check_feasibility", check_feasibility_node)
    workflow.add_node("repair_plan", repair_plan)
    workflow.add_node("fail_generation", fail_generation)
    workflow.add_node("persist_roadmap", persist_roadmap)

    workflow.add_edge(START, "load_role_template")
    workflow.add_edge("load_role_template", "analyze_gaps")
    workflow.add_edge("analyze_gaps", "generate_plan")
    workflow.add_edge("generate_plan", "validate_schema")
    workflow.add_edge("validate_schema", "check_feasibility")

    workflow.add_conditional_edges(
        "check_feasibility",
        should_retry,
        {
            "persist": "persist_roadmap",
            "repair": "repair_plan",
            "fail": "fail_generation",
        },
    )

    workflow.add_edge("repair_plan", "validate_schema")
    workflow.add_edge("persist_roadmap", END)
    workflow.add_edge("fail_generation", END)

    return workflow.compile()


roadmap_generation_graph = create_roadmap_graph()