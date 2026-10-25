"""
feasibility.py — Deterministic feasibility checks for roadmap generation.

Validates that generated roadmaps meet all constraints before persistence.
"""

from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class FeasibilityViolation:
    code: str
    message: str
    severity: str = "error"  # error or warning


def check_feasibility(
    roadmap_data: Dict[str, Any],
    weekly_hours: float,
    planning_weeks: int,
    role_template: Dict[str, Any],
) -> List[FeasibilityViolation]:
    """
    Run deterministic feasibility checks on the generated roadmap.

    Args:
        roadmap_data: The generated roadmap with phases and tasks
        weekly_hours: Student's available weekly study hours
        planning_weeks: Number of weeks until deadline (or default 12)
        role_template: Role template with expected topic hours

    Returns:
        List of FeasibilityViolation objects. Empty if all checks pass.
    """
    violations = []

    # Extract all tasks
    all_tasks = []
    for phase in roadmap_data.get("phases", []):
        for task in phase.get("tasks", []):
            all_tasks.append({**task, "phase_name": phase.get("name", "")})

    if not all_tasks:
        violations.append(FeasibilityViolation(
            code="EMPTY_ROADMAP",
            message="Roadmap must contain at least one task",
        ))
        return violations

    # Check 1: Total hours within budget
    total_hours = sum(t.get("estimated_hours", 0) for t in all_tasks)
    max_hours = weekly_hours * planning_weeks
    if total_hours > max_hours:
        violations.append(FeasibilityViolation(
            code="HOURS_EXCEED_BUDGET",
            message=f"Total estimated hours ({total_hours:.1f}) exceeds budget ({max_hours:.1f} hours = {weekly_hours}h/week × {planning_weeks} weeks)",
        ))

    # Check 2: Each task within hour bounds
    for task in all_tasks:
        hours = task.get("estimated_hours", 0)
        if hours < 0.5 or hours > 8.0:
            violations.append(FeasibilityViolation(
                code="TASK_HOURS_OUT_OF_BOUNDS",
                message=f"Task '{task.get('title', 'Unknown')}' has {hours} hours (must be 0.5-8.0)",
            ))

    # Check 3: Every task has required fields
    for task in all_tasks:
        if not task.get("title", "").strip():
            violations.append(FeasibilityViolation(
                code="MISSING_TASK_TITLE",
                message="Task missing title",
            ))
        if not task.get("success_criteria", "").strip():
            violations.append(FeasibilityViolation(
                code="MISSING_SUCCESS_CRITERIA",
                message=f"Task '{task.get('title', 'Unknown')}' missing success criteria",
            ))

    # Check 4: Task maps to role template topic or identified gap
    template_topics = set(role_template.get("core_topics", []))
    template_skills = {s["name"].lower() for s in role_template.get("skills", [])}
    all_template_keywords = template_topics.union(template_skills)

    for task in all_tasks:
        topic_tags = [t.lower() for t in task.get("topic_tags", [])]
        title_lower = task.get("title", "").lower()

        # Check if any topic tag or title keyword matches template
        matched = False
        for keyword in all_template_keywords:
            if keyword.lower() in title_lower or any(keyword.lower() in tag for tag in topic_tags):
                matched = True
                break

        if not matched and topic_tags:
            # Allow if custom tags provided but warn
            violations.append(FeasibilityViolation(
                code="TASK_TOPIC_UNMATCHED",
                message=f"Task '{task.get('title', 'Unknown')}' topics {topic_tags} don't match role template",
                severity="warning",
            ))

    # Check 5: Phases are ordered and non-empty
    phases = roadmap_data.get("phases", [])
    for i, phase in enumerate(phases):
        if not phase.get("tasks"):
            violations.append(FeasibilityViolation(
                code="EMPTY_PHASE",
                message=f"Phase '{phase.get('name', f'Phase {i+1}')}' has no tasks",
            ))
        if phase.get("position", i + 1) != i + 1:
            violations.append(FeasibilityViolation(
                code="PHASE_POSITION_MISMATCH",
                message=f"Phase positions must be sequential starting from 1",
            ))

    # Check 6: Task positions within phases are sequential
    for phase in phases:
        for j, task in enumerate(phase.get("tasks", [])):
            if task.get("position", j + 1) != j + 1:
                violations.append(FeasibilityViolation(
                    code="TASK_POSITION_MISMATCH",
                    message=f"Task positions in phase '{phase.get('name')}' must be sequential",
                ))

    return violations


def repair_plan_prompt(violations: List[FeasibilityViolation], roadmap_data: Dict[str, Any]) -> str:
    """Generate a prompt for the LLM to repair the roadmap based on violations."""
    violation_msgs = "\n".join(f"- {v.code}: {v.message}" for v in violations if v.severity == "error")

    return f"""The generated roadmap has the following feasibility violations that must be fixed:

{violation_msgs}

Current roadmap:
{roadmap_data}

Please regenerate the roadmap to fix these issues while maintaining relevance to the target role.
Ensure:
1. Total hours <= weekly_hours × planning_weeks
2. Each task is 0.5-8 hours
3. Every task has title, hours, success criteria
4. Tasks map to role template topics
5. Phases and tasks are sequentially numbered
"""