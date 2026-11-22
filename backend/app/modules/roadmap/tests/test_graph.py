"""
test_graph.py — Unit tests for roadmap LangGraph subgraph.

Tests graph nodes, routing, and state transitions with mocked LLMs.

Run: uv run pytest app/modules/roadmap/tests/test_graph.py -v
"""

import pytest
from unittest.mock import patch, MagicMock
import json

from app.modules.roadmap.graph import (
    RoadmapState,
    load_role_template,
    analyze_gaps,
    generate_plan,
    validate_schema,
    check_feasibility_node,
    should_retry,
    repair_plan,
    fail_generation,
    persist_roadmap,
)
from app.modules.roadmap.feasibility import FeasibilityViolation


def make_mock_llm():
    """Create a mock LLM that returns appropriate responses based on prompt."""
    def mock_invoke(prompt):
        mock_response = MagicMock()
        if "Skills Gap Analyst" in prompt:
            mock_response.content = json.dumps({
                "critical_gaps": ["Docker", "Kubernetes"],
                "moderate_gaps": ["System Design"],
                "strengths": ["Python", "FastAPI"],
                "priority_topics": ["Containerization", "Cloud"]
            })
        elif "Career Coach and Technical Curriculum Designer" in prompt:
            mock_response.content = json.dumps({
                "title": "Backend Developer Preparation",
                "target_role": "Backend Developer",
                "phases": [
                    {
                        "name": "Core Foundations",
                        "position": 1,
                        "description": "Build fundamentals",
                        "tasks": [
                            {
                                "title": "Master Python",
                                "estimated_hours": 6,
                                "success_criteria": "Complete course",
                                "topic_tags": ["python"],
                                "position": 1
                            },
                        ]
                    },
                ]
            })
        elif "The previous roadmap had feasibility violations" in prompt:
            mock_response.content = json.dumps({
                "title": "Backend Developer Preparation",
                "target_role": "Backend Developer",
                "phases": [
                    {
                        "name": "Core Foundations",
                        "position": 1,
                        "description": "Build fundamentals",
                        "tasks": [
                            {
                                "title": "Master Python",
                                "estimated_hours": 4,
                                "success_criteria": "Complete course",
                                "topic_tags": ["python"],
                                "position": 1
                            },
                        ]
                    },
                ]
            })
        else:
            mock_response.content = "{}"
        return mock_response

    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = mock_invoke
    return mock_llm


class TestLoadRoleTemplate:
    """Test load_role_template node."""

    def test_loads_correct_template(self):
        state = {
            "target_role": "Backend Developer",
            "company_type": "product",
            "skills": [],
            "education": [],
            "weekly_hours": 10.0,
            "planning_weeks": 12,
        }
        result = load_role_template(state)

        assert "role_template" in result
        assert result["role_template"]["role"] == "Backend Developer"
        assert "company_emphasis" in result["role_template"]
        assert "additional_topics" in result["role_template"]

    def test_company_type_adjustments_applied(self):
        state = {
            "target_role": "Backend Developer",
            "company_type": "startup",
            "skills": [],
            "education": [],
            "weekly_hours": 10.0,
            "planning_weeks": 12,
        }
        result = load_role_template(state)

        assert result["role_template"]["company_emphasis"] == ["Full-Stack Exposure", "Rapid Prototyping", "Pragmatic Architecture", "Cost Optimization"]
        assert "MVP Development" in result["role_template"]["additional_topics"]

    def test_unknown_role_defaults_to_backend(self):
        state = {
            "target_role": "Unknown Role",
            "company_type": "product",
            "skills": [],
            "education": [],
            "weekly_hours": 10.0,
            "planning_weeks": 12,
        }
        result = load_role_template(state)

        assert result["role_template"]["role"] == "Backend Developer"


class TestAnalyzeGaps:
    """Test analyze_gaps node."""

    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_returns_skill_gaps(self, mock_get_llm):
        mock_get_llm.return_value = make_mock_llm()

        state = {
            "target_role": "Backend Developer",
            "company_type": "product",
            "skills": [{"name": "Python", "level": "advanced"}],
            "education": [],
            "weekly_hours": 10.0,
            "planning_weeks": 12,
            "role_template": {
                "core_topics": ["Python", "SQL"],
                "skills": [{"name": "Python"}],
                "company_emphasis": [],
            },
        }
        result = analyze_gaps(state)

        assert "skill_gaps" in result
        gaps = result["skill_gaps"]
        assert "critical_gaps" in gaps
        assert "strengths" in gaps
        assert "priority_topics" in gaps


class TestGeneratePlan:
    """Test generate_plan node."""

    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_returns_roadmap_draft(self, mock_get_llm):
        mock_get_llm.return_value = make_mock_llm()

        state = {
            "target_role": "Backend Developer",
            "company_type": "product",
            "skills": [{"name": "Python", "level": "advanced"}],
            "education": [],
            "weekly_hours": 10.0,
            "planning_weeks": 12,
            "prep_deadline": "2026-12-31",
            "role_template": {
                "core_topics": ["Python", "SQL"],
                "skills": [{"name": "Python"}],
                "company_emphasis": ["System Design"],
                "company_type_adjustments": {},
            },
            "skill_gaps": {
                "critical_gaps": ["Docker"],
                "strengths": ["Python"],
                "priority_topics": ["Containerization"],
            },
        }
        result = generate_plan(state)

        assert "roadmap_draft" in result
        draft = result["roadmap_draft"]
        assert draft["title"] == "Backend Developer Preparation"
        assert "phases" in draft
        assert len(draft["phases"]) >= 1
        assert result["retry_count"] == 0


class TestValidateSchema:
    """Test validate_schema node."""

    def test_valid_schema_passes(self):
        state = {
            "roadmap_draft": {
                "title": "Test Roadmap",
                "target_role": "Backend Developer",
                "phases": [
                    {
                        "name": "Phase 1",
                        "tasks": [
                            {"title": "Task 1", "estimated_hours": 4, "success_criteria": "Done", "topic_tags": ["python"], "position": 1}
                        ],
                        "position": 1,
                    }
                ],
            }
        }
        # Should not raise
        result = validate_schema(state)
        assert result == {}

    def test_missing_title_raises(self):
        state = {"roadmap_draft": {"target_role": "Backend Developer", "phases": []}}
        with pytest.raises(ValueError, match="Missing required key: title"):
            validate_schema(state)

    def test_empty_phases_raises(self):
        state = {"roadmap_draft": {"title": "Test", "target_role": "Backend Developer", "phases": []}}
        with pytest.raises(ValueError, match="non-empty list"):
            validate_schema(state)

    def test_phase_missing_name_raises(self):
        state = {"roadmap_draft": {"title": "Test", "target_role": "Backend Developer", "phases": [{"tasks": []}]}}
        with pytest.raises(ValueError, match="missing name or tasks"):
            validate_schema(state)

    def test_phase_tasks_not_list_raises(self):
        state = {"roadmap_draft": {"title": "Test", "target_role": "Backend Developer", "phases": [{"name": "P", "tasks": "not a list"}]}}
        with pytest.raises(ValueError, match="must be a list"):
            validate_schema(state)


class TestCheckFeasibilityNode:
    """Test check_feasibility_node."""

    def test_no_violations_returns_empty(self):
        state = {
            "roadmap_draft": {
                "title": "Test",
                "target_role": "Backend Developer",
                "phases": [
                    {"name": "Phase 1", "position": 1, "tasks": [
                        {"title": "Task 1", "estimated_hours": 4, "success_criteria": "Done", "topic_tags": ["python"], "position": 1}
                    ]}
                ],
            },
            "role_template": {"core_topics": ["Python"], "skills": [{"name": "Python"}]},
            "weekly_hours": 10.0,
            "planning_weeks": 4,
        }
        result = check_feasibility_node(state)
        assert "feasibility_violations" in result
        assert len(result["feasibility_violations"]) == 0

    def test_returns_violations(self):
        state = {
            "roadmap_draft": {
                "title": "Test",
                "target_role": "Backend Developer",
                "phases": [
                    {"name": "Phase 1", "position": 1, "tasks": [
                        {"title": "Task 1", "estimated_hours": 10, "success_criteria": "Done", "topic_tags": ["python"], "position": 1}
                    ]}
                ],
            },
            "role_template": {"core_topics": ["Python"], "skills": [{"name": "Python"}]},
            "weekly_hours": 10.0,
            "planning_weeks": 4,
        }
        result = check_feasibility_node(state)
        violations = result["feasibility_violations"]
        assert len(violations) > 0
        assert any(v.code == "TASK_HOURS_OUT_OF_BOUNDS" for v in violations)


class TestShouldRetry:
    """Test should_retry conditional edge."""

    def test_no_error_violations_returns_persist(self):
        state = {
            "feasibility_violations": [
                FeasibilityViolation(code="WARNING", message="Warning", severity="warning")
            ],
            "retry_count": 0,
        }
        assert should_retry(state) == "persist"

    def test_error_violations_under_retry_limit_returns_repair(self):
        state = {
            "feasibility_violations": [
                FeasibilityViolation(code="ERROR", message="Error", severity="error")
            ],
            "retry_count": 0,
        }
        assert should_retry(state) == "repair"

    def test_error_violations_at_retry_limit_returns_fail(self):
        state = {
            "feasibility_violations": [
                FeasibilityViolation(code="ERROR", message="Error", severity="error")
            ],
            "retry_count": 2,
        }
        assert should_retry(state) == "fail"

    def test_error_violations_over_retry_limit_returns_fail(self):
        state = {
            "feasibility_violations": [
                FeasibilityViolation(code="ERROR", message="Error", severity="error")
            ],
            "retry_count": 5,
        }
        assert should_retry(state) == "fail"


class TestRepairPlan:
    """Test repair_plan node."""

    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_repairs_and_increments_retry(self, mock_get_llm):
        mock_get_llm.return_value = make_mock_llm()

        state = {
            "roadmap_draft": {
                "title": "Test",
                "target_role": "Backend Developer",
                "phases": [{"name": "P", "tasks": [{"title": "T", "estimated_hours": 10, "success_criteria": "C", "topic_tags": [], "position": 1}]}],
            },
            "role_template": {"core_topics": ["Python"]},
            "weekly_hours": 10.0,
            "planning_weeks": 4,
            "feasibility_violations": [
                FeasibilityViolation(code="TASK_HOURS_OUT_OF_BOUNDS", message="Too many hours", severity="error")
            ],
            "retry_count": 0,
        }
        result = repair_plan(state)

        assert "roadmap_draft" in result
        assert result["retry_count"] == 1
        # Repaired roadmap should have reduced hours
        assert result["roadmap_draft"]["phases"][0]["tasks"][0]["estimated_hours"] == 4


class TestFailGeneration:
    """Test fail_generation node."""

    def test_returns_error_message(self):
        state = {
            "feasibility_violations": [
                FeasibilityViolation(code="E1", message="Error 1", severity="error"),
                FeasibilityViolation(code="E2", message="Error 2", severity="error"),
            ],
        }
        result = fail_generation(state)

        assert "error" in result
        assert "Error 1" in result["error"]
        assert "Error 2" in result["error"]


class TestPersistRoadmap:
    """Test persist_roadmap node."""

    def test_returns_final_roadmap(self):
        state = {
            "roadmap_draft": {
                "title": "Final Roadmap",
                "target_role": "Backend Developer",
                "phases": [],
            }
        }
        result = persist_roadmap(state)
        assert result["final_roadmap"] == state["roadmap_draft"]


class TestGraphIntegration:
    """Integration test for the full graph flow."""

    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_full_graph_success_path(self, mock_get_llm):
        """Test successful roadmap generation through full graph."""
        from app.modules.roadmap.graph import roadmap_generation_graph

        mock_get_llm.return_value = make_mock_llm()

        input_state = {
            "student_id": "std-1",
            "target_role": "Backend Developer",
            "company_type": "product",
            "skills": [{"name": "Python", "level": "advanced"}],
            "education": [],
            "weekly_hours": 10.0,
            "planning_weeks": 12,
            "prep_deadline": "2026-12-31",
        }

        result = roadmap_generation_graph.invoke(input_state)

        assert "final_roadmap" in result
        assert result["final_roadmap"] is not None
        assert result.get("error") is None

    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_graph_repair_loop(self, mock_get_llm):
        """Test graph goes through repair loop when feasibility fails."""
        from app.modules.roadmap.graph import roadmap_generation_graph

        # First call returns invalid roadmap, second (repair) returns valid
        call_count = {"count": 0}

        def mock_invoke(prompt):
            mock_response = MagicMock()
            call_count["count"] += 1
            if call_count["count"] == 1:
                # First generation - invalid (hours too high)
                mock_response.content = json.dumps({
                    "title": "Test",
                    "target_role": "Backend Developer",
                    "phases": [{
                        "name": "P1", "position": 1,
                        "tasks": [{"title": "T1", "estimated_hours": 20, "success_criteria": "C", "topic_tags": ["python"], "position": 1}]
                    }]
                })
            else:
                # Repair - valid
                mock_response.content = json.dumps({
                    "title": "Test",
                    "target_role": "Backend Developer",
                    "phases": [{
                        "name": "P1", "position": 1,
                        "tasks": [{"title": "T1", "estimated_hours": 5, "success_criteria": "C", "topic_tags": ["python"], "position": 1}]
                    }]
                })
            return mock_response

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = mock_invoke
        mock_get_llm.return_value = mock_llm

        input_state = {
            "student_id": "std-1",
            "target_role": "Backend Developer",
            "company_type": "product",
            "skills": [{"name": "Python", "level": "advanced"}],
            "education": [],
            "weekly_hours": 10.0,
            "planning_weeks": 4,
            "prep_deadline": "2026-12-31",
        }

        result = roadmap_generation_graph.invoke(input_state)

        assert "final_roadmap" in result
        assert result["final_roadmap"] is not None
        assert call_count["count"] == 2  # Initial + repair