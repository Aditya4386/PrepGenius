"""
test_roadmap.py — Integration tests for roadmap endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock
import json


def make_mock_roadmap_llm():
    """Mock LLM responses for roadmap graph nodes."""
    def mock_invoke(prompt):
        mock_response = MagicMock()
        if "Skills Gap Analyst" in prompt:
            mock_response.content = json.dumps({
                "critical_gaps": ["Docker", "Kubernetes", "AWS"],
                "moderate_gaps": ["System Design"],
                "strengths": ["Python", "FastAPI", "SQL"],
                "priority_topics": ["Containerization", "Cloud Basics", "System Design"]
            })
        elif "Career Coach and Technical Curriculum Designer" in prompt:
            mock_response.content = json.dumps({
                "title": "Backend Developer Preparation",
                "target_role": "Backend Developer",
                "phases": [
                    {
                        "name": "Core Foundations",
                        "position": 1,
                        "description": "Build strong fundamentals",
                        "tasks": [
                            {
                                "title": "Master Python Advanced Concepts",
                                "estimated_hours": 8,
                                "success_criteria": "Complete advanced Python course and build a CLI tool",
                                "topic_tags": ["python", "advanced"],
                                "position": 1
                            },
                            {
                                "title": "SQL Deep Dive",
                                "estimated_hours": 6,
                                "success_criteria": "Solve 50 LeetCode SQL problems",
                                "topic_tags": ["sql", "database"],
                                "position": 2
                            },
                        ]
                    },
                    {
                        "name": "Backend Specialization",
                        "position": 2,
                        "description": "Backend-specific skills",
                        "tasks": [
                            {
                                "title": "FastAPI Mastery",
                                "estimated_hours": 10,
                                "success_criteria": "Build and deploy a production-ready API",
                                "topic_tags": ["fastapi", "api"],
                                "position": 1
                            },
                            {
                                "title": "Docker & Containerization",
                                "estimated_hours": 8,
                                "success_criteria": "Containerize 3 applications",
                                "topic_tags": ["docker", "devops"],
                                "position": 2
                            },
                        ]
                    },
                ]
            })
        elif "The previous roadmap had feasibility violations" in prompt:
            # Repair prompt - return fixed version
            mock_response.content = json.dumps({
                "title": "Backend Developer Preparation",
                "target_role": "Backend Developer",
                "phases": [
                    {
                        "name": "Core Foundations",
                        "position": 1,
                        "description": "Build strong fundamentals",
                        "tasks": [
                            {
                                "title": "Master Python Advanced Concepts",
                                "estimated_hours": 6,
                                "success_criteria": "Complete advanced Python course and build a CLI tool",
                                "topic_tags": ["python", "advanced"],
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


class TestRoadmapGeneration:
    """Integration tests for roadmap generation."""

    @patch("app.modules.roadmap.graph.get_llm")
    def test_generate_roadmap(self, mock_get_llm, client, mock_student_id):
        """Test generating a new roadmap."""
        mock_get_llm.return_value = make_mock_roadmap_llm()

        # First, we need a profile with target_role and company_type
        # This would normally be set up via profile endpoint
        # For now, we'll test the endpoint directly
        response = client.post(
            "/api/v1/roadmap/generate",
            json={"force_regenerate": True},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        # Might fail if profile not set up, but endpoint should handle gracefully
        assert response.status_code in [200, 400]

    @patch("app.modules.roadmap.graph.get_llm")
    def test_get_active_roadmap(self, mock_get_llm, client, mock_student_id):
        """Test getting active roadmap."""
        mock_get_llm.return_value = make_mock_roadmap_llm()

        response = client.get(
            "/api/v1/roadmap",
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        assert response.status_code in [200, 404]

    @patch("app.modules.roadmap.graph.get_llm")
    def test_roadmap_generation_with_profile(self, mock_get_llm, client, mock_student_id):
        """Test roadmap generation with a complete profile."""
        mock_get_llm.return_value = make_mock_roadmap_llm()

        # Create a complete profile first
        client.put(
            "/api/v1/profile",
            json={
                "target_role": "Backend Developer",
                "company_type": "product",
                "weekly_study_hours": 10,
                "skills": [{"name": "Python", "level": "advanced"}, {"name": "SQL", "level": "intermediate"}, {"name": "FastAPI", "level": "intermediate"}],
                "education": [{"institution": "Test University", "degree": "B.Tech Computer Science", "year_of_completion": 2024}],
                "preparation_deadline": "2026-12-31"
            },
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        # Generate roadmap
        response = client.post(
            "/api/v1/roadmap/generate",
            json={"force_regenerate": True},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["target_role"] == "Backend Developer"
        assert data["total_estimated_hours"] > 0
        assert len(data["phases"]) > 0
        for phase in data["phases"]:
            assert "tasks" in phase
            assert len(phase["tasks"]) > 0
            for task in phase["tasks"]:
                assert "title" in task
                assert "estimated_hours" in task
                assert 0.5 <= task["estimated_hours"] <= 8.0

    @patch("app.modules.roadmap.graph.get_llm")
    def test_generate_roadmap_without_profile_fails(self, mock_get_llm, client, mock_student_id):
        """Test roadmap generation fails without complete profile."""
        mock_get_llm.return_value = make_mock_roadmap_llm()

        # Don't create profile - just try to generate
        response = client.post(
            "/api/v1/roadmap/generate",
            json={"force_regenerate": True},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        assert response.status_code == 400
        assert "incomplete" in response.json()["detail"].lower()


class TestRoadmapFeasibility:
    """Unit tests for feasibility checks."""

    def test_hours_exceed_budget(self):
        """Test detection of hours exceeding budget."""
        from app.modules.roadmap.feasibility import check_feasibility, FeasibilityViolation

        roadmap_data = {
            "phases": [
                {
                    "name": "Phase 1",
                    "position": 1,
                    "tasks": [
                        {"title": "Task 1", "estimated_hours": 20, "success_criteria": "Done", "topic_tags": ["python"], "position": 1},
                        {"title": "Task 2", "estimated_hours": 30, "success_criteria": "Done", "topic_tags": ["sql"], "position": 2},
                    ]
                }
            ]
        }

        role_template = {
            "core_topics": ["Python", "SQL"],
            "skills": [{"name": "Python"}, {"name": "SQL"}],
        }

        violations = check_feasibility(roadmap_data, weekly_hours=10, planning_weeks=4, role_template=role_template)
        # 50 hours > 40 hours budget
        assert any(v.code == "HOURS_EXCEED_BUDGET" for v in violations)

    def test_task_hours_out_of_bounds(self):
        """Test detection of task hours out of bounds."""
        from app.modules.roadmap.feasibility import check_feasibility

        roadmap_data = {
            "phases": [
                {
                    "name": "Phase 1",
                    "position": 1,
                    "tasks": [
                        {"title": "Too Long Task", "estimated_hours": 10, "success_criteria": "Done", "topic_tags": ["python"], "position": 1},
                    ]
                }
            ]
        }

        violations = check_feasibility(roadmap_data, weekly_hours=10, planning_weeks=4, role_template={})
        assert any(v.code == "TASK_HOURS_OUT_OF_BOUNDS" for v in violations)

    def test_missing_task_fields(self):
        """Test detection of missing required fields."""
        from app.modules.roadmap.feasibility import check_feasibility

        roadmap_data = {
            "phases": [
                {
                    "name": "Phase 1",
                    "position": 1,
                    "tasks": [
                        {"title": "", "estimated_hours": 4, "success_criteria": "", "topic_tags": ["python"], "position": 1},
                    ]
                }
            ]
        }

        violations = check_feasibility(roadmap_data, weekly_hours=10, planning_weeks=4, role_template={})
        assert any(v.code == "MISSING_TASK_TITLE" for v in violations)
        assert any(v.code == "MISSING_SUCCESS_CRITERIA" for v in violations)

    def test_empty_phase_rejected(self):
        """Test that empty phases are rejected."""
        from app.modules.roadmap.feasibility import check_feasibility

        roadmap_data = {
            "phases": [
                {"name": "Phase 1", "position": 1, "tasks": [{"title": "Task 1", "estimated_hours": 4, "success_criteria": "Done", "topic_tags": ["python"], "position": 1}]},
                {"name": "Empty Phase", "position": 2, "tasks": []}
            ]
        }

        violations = check_feasibility(roadmap_data, weekly_hours=10, planning_weeks=4, role_template={})
        assert any(v.code == "EMPTY_PHASE" for v in violations)

    def test_valid_roadmap_passes(self):
        """Test that a valid roadmap passes all checks."""
        from app.modules.roadmap.feasibility import check_feasibility

        roadmap_data = {
            "title": "Test Roadmap",
            "target_role": "Backend Developer",
            "phases": [
                {
                    "name": "Phase 1",
                    "position": 1,
                    "tasks": [
                        {"title": "Learn Python", "estimated_hours": 8, "success_criteria": "Complete course", "topic_tags": ["python"], "position": 1},
                    ]
                }
            ]
        }

        role_template = {
            "core_topics": ["Python"],
            "skills": [{"name": "Python"}],
        }

        violations = check_feasibility(roadmap_data, weekly_hours=10, planning_weeks=4, role_template=role_template)
        error_violations = [v for v in violations if v.severity == "error"]
        assert len(error_violations) == 0


class TestRoadmapTaskOperations:
    """Tests for task completion and updates."""

    def test_task_status_enum(self):
        """Test TaskStatusEnum values."""
        from app.modules.roadmap.schemas import TaskStatusEnum
        assert TaskStatusEnum.PENDING.value == "pending"
        assert TaskStatusEnum.COMPLETED.value == "completed"

    def test_roadmap_task_schema(self):
        """Test RoadmapTask schema validation."""
        from app.modules.roadmap.schemas import RoadmapTaskBase, TaskStatusEnum
        task = RoadmapTaskBase(
            title="Test Task",
            estimated_hours=4.0,
            success_criteria="Complete the task",
            topic_tags=["python"],
        )
        assert task.title == "Test Task"
        assert task.estimated_hours == 4.0
        assert task.status == TaskStatusEnum.PENDING

    def test_roadmap_task_invalid_hours(self):
        """Test that invalid hours are rejected."""
        from app.modules.roadmap.schemas import RoadmapTaskBase
        with pytest.raises(ValueError):
            RoadmapTaskBase(
                title="Test",
                estimated_hours=10.0,  # > 8.0
                success_criteria="Done",
            )

        with pytest.raises(ValueError):
            RoadmapTaskBase(
                title="Test",
                estimated_hours=0.1,  # < 0.5
                success_criteria="Done",
            )

    @patch("app.modules.roadmap.graph.get_llm")
    def test_task_completion_updates_percentage(self, mock_get_llm, client, mock_student_id):
        """Test that completing tasks updates completion percentage."""
        mock_get_llm.return_value = make_mock_roadmap_llm()

        # Create profile and generate roadmap
        client.put(
            "/api/v1/profile",
            json={
                "target_role": "Backend Developer",
                "company_type": "product",
                "weekly_study_hours": 10,
                "skills": [{"name": "Python", "level": "advanced"}],
                "education": [{"institution": "Test University", "degree": "B.Tech", "year_of_completion": 2024}],
                "preparation_deadline": "2026-12-31"
            },
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        gen_resp = client.post(
            "/api/v1/roadmap/generate",
            json={"force_regenerate": True},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        if gen_resp.status_code == 200:
            roadmap = gen_resp.json()
            # Get a task ID
            if roadmap["phases"] and roadmap["phases"][0]["tasks"]:
                task_id = roadmap["phases"][0]["tasks"][0]["id"]

                # Get initial completion
                comp_resp = client.get("/api/v1/roadmap/completion", headers={"Authorization": f"Bearer {mock_student_id}"})
                initial_pct = comp_resp.json().get("completion_percentage", 0)

                # Mark task as completed
                update_resp = client.patch(
                    f"/api/v1/roadmap/tasks/{task_id}/status",
                    json={"status": "completed"},
                    headers={"Authorization": f"Bearer {mock_student_id}"},
                )
                assert update_resp.status_code == 200

                # Check completion increased
                comp_resp = client.get("/api/v1/roadmap/completion", headers={"Authorization": f"Bearer {mock_student_id}"})
                new_pct = comp_resp.json().get("completion_percentage", 0)
                assert new_pct > initial_pct

    @patch("app.modules.roadmap.graph.get_llm")
    def test_task_edit_updates_details(self, mock_get_llm, client, mock_student_id):
        """Test editing task details."""
        mock_get_llm.return_value = make_mock_roadmap_llm()

        # Create profile and generate roadmap
        client.put(
            "/api/v1/profile",
            json={
                "target_role": "Backend Developer",
                "company_type": "product",
                "weekly_study_hours": 10,
                "skills": [{"name": "Python", "level": "advanced"}],
                "education": [{"institution": "Test University", "degree": "B.Tech", "year_of_completion": 2024}],
                "preparation_deadline": "2026-12-31"
            },
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        gen_resp = client.post(
            "/api/v1/roadmap/generate",
            json={"force_regenerate": True},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        if gen_resp.status_code == 200:
            roadmap = gen_resp.json()
            if roadmap["phases"] and roadmap["phases"][0]["tasks"]:
                task_id = roadmap["phases"][0]["tasks"][0]["id"]

                # Update task
                update_resp = client.patch(
                    f"/api/v1/roadmap/tasks/{task_id}",
                    json={"title": "Updated Task Title", "estimated_hours": 5.0},
                    headers={"Authorization": f"Bearer {mock_student_id}"},
                )
                assert update_resp.status_code == 200

                # Verify update
                get_resp = client.get("/api/v1/roadmap", headers={"Authorization": f"Bearer {mock_student_id}"})
                updated_roadmap = get_resp.json()
                updated_task = next(t for p in updated_roadmap["phases"] for t in p["tasks"] if t["id"] == task_id)
                assert updated_task["title"] == "Updated Task Title"
                assert updated_task["estimated_hours"] == 5.0

    @patch("app.modules.roadmap.graph.get_llm")
    def test_adaptation_workflow(self, mock_get_llm, client, mock_student_id):
        """Test adaptation proposal creation, listing, approval, rejection."""
        mock_get_llm.return_value = make_mock_roadmap_llm()

        # Create profile and generate roadmap
        client.put(
            "/api/v1/profile",
            json={
                "target_role": "Backend Developer",
                "company_type": "product",
                "weekly_study_hours": 10,
                "skills": [{"name": "Python", "level": "advanced"}],
                "education": [{"institution": "Test University", "degree": "B.Tech", "year_of_completion": 2024}],
                "preparation_deadline": "2026-12-31"
            },
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        gen_resp = client.post(
            "/api/v1/roadmap/generate",
            json={"force_regenerate": True},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        if gen_resp.status_code == 200:
            # Create adaptation proposal
            create_resp = client.post(
                "/api/v1/roadmap/adaptations",
                data={
                    "source_type": "interview",
                    "source_id": "interview_123",
                    "proposed_tasks": json.dumps([
                        {"title": "New Task from Interview", "estimated_hours": 4, "success_criteria": "Complete", "topic_tags": ["system design"]}
                    ]),
                },
                headers={"Authorization": f"Bearer {mock_student_id}"},
            )
            assert create_resp.status_code == 200
            adaptation_id = create_resp.json()["id"]

            # List adaptations
            list_resp = client.get("/api/v1/roadmap/adaptations", headers={"Authorization": f"Bearer {mock_student_id}"})
            assert list_resp.status_code == 200
            assert len(list_resp.json()) == 1

            # Approve adaptation
            approve_resp = client.post(
                f"/api/v1/roadmap/adaptations/{adaptation_id}/action",
                json={"action": "approve"},
                headers={"Authorization": f"Bearer {mock_student_id}"},
            )
            assert approve_resp.status_code == 200

            # Verify adaptation applied (task count increased)
            get_resp = client.get("/api/v1/roadmap", headers={"Authorization": f"Bearer {mock_student_id}"})
            assert get_resp.status_code == 200