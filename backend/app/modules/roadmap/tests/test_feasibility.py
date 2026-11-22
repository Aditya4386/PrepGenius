"""
test_feasibility.py — Unit tests for deterministic feasibility checks.

Run: uv run pytest app/modules/roadmap/tests/test_feasibility.py -v
"""

import pytest
from app.modules.roadmap.feasibility import check_feasibility, FeasibilityViolation


class TestFeasibilityChecks:
    """Unit tests for check_feasibility function."""

    def _base_roadmap(self):
        """Valid minimal roadmap for testing."""
        return {
            "title": "Test Roadmap",
            "target_role": "Backend Developer",
            "phases": [
                {
                    "name": "Phase 1",
                    "position": 1,
                    "tasks": [
                        {
                            "title": "Learn Python",
                            "estimated_hours": 4.0,
                            "success_criteria": "Complete tutorial",
                            "topic_tags": ["python"],
                            "position": 1,
                        }
                    ],
                }
            ],
        }

    def _base_role_template(self):
        """Valid role template for testing."""
        return {
            "core_topics": ["Python", "SQL"],
            "skills": [{"name": "Python"}, {"name": "SQL"}],
        }

    # --- Happy Path ---

    def test_valid_roadmap_passes_all_checks(self):
        """A valid roadmap should produce zero error violations."""
        roadmap = self._base_roadmap()
        template = self._base_role_template()
        violations = check_feasibility(roadmap, weekly_hours=10, planning_weeks=4, role_template=template)

        error_violations = [v for v in violations if v.severity == "error"]
        assert len(error_violations) == 0

    # --- Hours Budget ---

    def test_hours_exceed_budget_raises_error(self):
        """Total hours > weekly_hours * planning_weeks should error."""
        roadmap = self._base_roadmap()
        roadmap["phases"][0]["tasks"] = [
            {"title": f"Task {i}", "estimated_hours": 10.0, "success_criteria": "Done", "topic_tags": ["python"], "position": i}
            for i in range(1, 6)  # 50 hours total
        ]

        violations = check_feasibility(roadmap, weekly_hours=10, planning_weeks=4, role_template=self._base_role_template())

        assert any(v.code == "HOURS_EXCEED_BUDGET" for v in violations)
        assert any(v.severity == "error" for v in violations)

    def test_hours_at_budget_boundary_passes(self):
        """Exactly at budget should pass (no error)."""
        roadmap = self._base_roadmap()
        roadmap["phases"][0]["tasks"] = [
            {"title": "Task 1", "estimated_hours": 20.0, "success_criteria": "Done", "topic_tags": ["python"], "position": 1},
            {"title": "Task 2", "estimated_hours": 20.0, "success_criteria": "Done", "topic_tags": ["sql"], "position": 2},
        ]  # 40 hours = 10 * 4

        violations = check_feasibility(roadmap, weekly_hours=10, planning_weeks=4, role_template=self._base_role_template())

        assert not any(v.code == "HOURS_EXCEED_BUDGET" for v in violations)

    # --- Task Hours Bounds ---

    def test_task_hours_too_high_raises_error(self):
        """Task > 8 hours should error."""
        roadmap = self._base_roadmap()
        roadmap["phases"][0]["tasks"][0]["estimated_hours"] = 10.0

        violations = check_feasibility(roadmap, weekly_hours=10, planning_weeks=4, role_template=self._base_role_template())

        assert any(v.code == "TASK_HOURS_OUT_OF_BOUNDS" for v in violations)
        assert any(v.severity == "error" for v in violations)

    def test_task_hours_too_low_raises_error(self):
        """Task < 0.5 hours should error."""
        roadmap = self._base_roadmap()
        roadmap["phases"][0]["tasks"][0]["estimated_hours"] = 0.1

        violations = check_feasibility(roadmap, weekly_hours=10, planning_weeks=4, role_template=self._base_role_template())

        assert any(v.code == "TASK_HOURS_OUT_OF_BOUNDS" for v in violations)

    def test_task_hours_at_boundary_passes(self):
        """0.5 and 8.0 hours should pass."""
        for hours in [0.5, 8.0]:
            roadmap = self._base_roadmap()
            roadmap["phases"][0]["tasks"][0]["estimated_hours"] = hours
            violations = check_feasibility(roadmap, weekly_hours=10, planning_weeks=4, role_template=self._base_role_template())
            assert not any(v.code == "TASK_HOURS_OUT_OF_BOUNDS" for v in violations)

    # --- Required Fields ---

    def test_missing_task_title_raises_error(self):
        """Empty task title should error."""
        roadmap = self._base_roadmap()
        roadmap["phases"][0]["tasks"][0]["title"] = ""

        violations = check_feasibility(roadmap, weekly_hours=10, planning_weeks=4, role_template=self._base_role_template())

        assert any(v.code == "MISSING_TASK_TITLE" for v in violations)

    def test_missing_success_criteria_raises_error(self):
        """Empty success_criteria should error."""
        roadmap = self._base_roadmap()
        roadmap["phases"][0]["tasks"][0]["success_criteria"] = ""

        violations = check_feasibility(roadmap, weekly_hours=10, planning_weeks=4, role_template=self._base_role_template())

        assert any(v.code == "MISSING_SUCCESS_CRITERIA" for v in violations)

    def test_whitespace_only_title_rejected(self):
        """Whitespace-only title should be treated as missing."""
        roadmap = self._base_roadmap()
        roadmap["phases"][0]["tasks"][0]["title"] = "   "

        violations = check_feasibility(roadmap, weekly_hours=10, planning_weeks=4, role_template=self._base_role_template())

        assert any(v.code == "MISSING_TASK_TITLE" for v in violations)

    # --- Phase & Task Ordering ---

    def test_empty_phase_raises_error(self):
        """Phase with no tasks should error."""
        roadmap = self._base_roadmap()
        roadmap["phases"].append({"name": "Empty Phase", "position": 2, "tasks": []})

        violations = check_feasibility(roadmap, weekly_hours=10, planning_weeks=4, role_template=self._base_role_template())

        assert any(v.code == "EMPTY_PHASE" for v in violations)

    def test_phase_position_mismatch_raises_error(self):
        """Non-sequential phase positions should error."""
        roadmap = self._base_roadmap()
        roadmap["phases"][0]["position"] = 2  # Should be 1

        violations = check_feasibility(roadmap, weekly_hours=10, planning_weeks=4, role_template=self._base_role_template())

        assert any(v.code == "PHASE_POSITION_MISMATCH" for v in violations)

    def test_task_position_mismatch_raises_error(self):
        """Non-sequential task positions within phase should error."""
        roadmap = self._base_roadmap()
        roadmap["phases"][0]["tasks"][0]["position"] = 5  # Should be 1

        violations = check_feasibility(roadmap, weekly_hours=10, planning_weeks=4, role_template=self._base_role_template())

        assert any(v.code == "TASK_POSITION_MISMATCH" for v in violations)

    def test_empty_roadmap_raises_error(self):
        """Roadmap with no tasks should error."""
        roadmap = {"title": "Empty", "target_role": "Backend Developer", "phases": []}

        violations = check_feasibility(roadmap, weekly_hours=10, planning_weeks=4, role_template=self._base_role_template())

        assert any(v.code == "EMPTY_ROADMAP" for v in violations)

    # --- Topic Matching (Warnings) ---

    def test_task_topic_unmatched_emits_warning(self):
        """Task with topics not in role template should warn (not error)."""
        roadmap = self._base_roadmap()
        # Change title to not match any template keyword
        roadmap["phases"][0]["tasks"][0]["title"] = "Learn Unknown Topic"
        roadmap["phases"][0]["tasks"][0]["topic_tags"] = ["unknown_topic_xyz"]

        violations = check_feasibility(roadmap, weekly_hours=10, planning_weeks=4, role_template=self._base_role_template())

        warning = next((v for v in violations if v.code == "TASK_TOPIC_UNMATCHED"), None)
        assert warning is not None
        assert warning.severity == "warning"

    def test_task_topic_matched_no_warning(self):
        """Task with matching topic should not warn."""
        roadmap = self._base_roadmap()
        roadmap["phases"][0]["tasks"][0]["topic_tags"] = ["python"]

        violations = check_feasibility(roadmap, weekly_hours=10, planning_weeks=4, role_template=self._base_role_template())

        assert not any(v.code == "TASK_TOPIC_UNMATCHED" for v in violations)

    def test_task_title_contains_topic_keyword_passes(self):
        """Task title containing template keyword should match even without tags."""
        roadmap = self._base_roadmap()
        roadmap["phases"][0]["tasks"][0]["title"] = "Master Python Advanced Concepts"
        roadmap["phases"][0]["tasks"][0]["topic_tags"] = []

        violations = check_feasibility(roadmap, weekly_hours=10, planning_weeks=4, role_template=self._base_role_template())

        assert not any(v.code == "TASK_TOPIC_UNMATCHED" for v in violations)

    # --- Multiple Violations ---

    def test_multiple_violations_all_reported(self):
        """All violations should be collected, not short-circuited."""
        roadmap = {
            "title": "Bad Roadmap",
            "target_role": "Backend Developer",
            "phases": [
                {
                    "name": "Phase 1",
                    "position": 2,  # Wrong position
                    "tasks": [
                        {"title": "", "estimated_hours": 10.0, "success_criteria": "", "topic_tags": ["unknown"], "position": 1}
                    ],
                }
            ],
        }

        violations = check_feasibility(roadmap, weekly_hours=10, planning_weeks=4, role_template=self._base_role_template())

        codes = {v.code for v in violations}
        assert "PHASE_POSITION_MISMATCH" in codes
        assert "MISSING_TASK_TITLE" in codes
        assert "MISSING_SUCCESS_CRITERIA" in codes
        assert "TASK_HOURS_OUT_OF_BOUNDS" in codes
        assert "TASK_TOPIC_UNMATCHED" in codes


class TestFeasibilityViolationDataclass:
    """Test the FeasibilityViolation dataclass."""

    def test_default_severity_is_error(self):
        v = FeasibilityViolation(code="TEST", message="Test message")
        assert v.severity == "error"

    def test_can_set_warning_severity(self):
        v = FeasibilityViolation(code="TEST", message="Test", severity="warning")
        assert v.severity == "warning"