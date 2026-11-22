"""
test_api_integration.py — Integration tests for roadmap API endpoints.

Run: uv run pytest app/modules/roadmap/tests/test_api_integration.py -v
"""

import pytest
from unittest.mock import patch, MagicMock
import json
from fastapi.testclient import TestClient

from app.main import app
from app.modules.roadmap.schemas import TaskStatusEnum, SourceTypeEnum
from app.modules.roadmap import service as roadmap_service


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


def make_mock_llm_for_task():
    """Mock for get_llm_for_task that returns appropriate mock based on task."""
    def mock_get_llm_for_task(task):
        return make_mock_roadmap_llm()
    return mock_get_llm_for_task


@pytest.fixture
def client():
    """Test client with in-memory database."""
    from app.db.session import get_db
    from app.db.base import Base
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    # Use in-memory SQLite for testing
    TEST_DATABASE_URL = "sqlite:///./test.db"
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_student_id():
    """Mock student ID for testing (works with DEV_MOCK_AUTH)."""
    return "mock_test_student_123"


@pytest.fixture
def auth_headers(mock_student_id):
    """Authorization headers for mock auth."""
    return {"Authorization": f"Bearer {mock_student_id}"}


@pytest.fixture(autouse=True)
def clear_roadmap_storage():
    """Clear in-memory roadmap storage before each test."""
    roadmap_service._roadmaps.clear()
    roadmap_service._roadmap_phases.clear()
    roadmap_service._roadmap_tasks.clear()
    roadmap_service._adaptations.clear()
    yield
    roadmap_service._roadmaps.clear()
    roadmap_service._roadmap_phases.clear()
    roadmap_service._roadmap_tasks.clear()
    roadmap_service._adaptations.clear()


def create_complete_profile(client, auth_headers):
    """Helper to create a complete profile for roadmap generation."""
    response = client.put(
        "/api/v1/profile",
        json={
            "target_role": "Backend Developer",
            "company_type": "product",
            "weekly_study_hours": 10,
            "skills": [
                {"name": "Python", "level": "advanced"},
                {"name": "SQL", "level": "intermediate"},
                {"name": "FastAPI", "level": "intermediate"},
            ],
            "education": [
                {"institution": "Test University", "degree": "B.Tech Computer Science", "year_of_completion": 2024}
            ],
            "preparation_deadline": "2026-12-31"
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    return response.json()


class TestRoadmapGeneration:
    """Integration tests for roadmap generation endpoint."""

    @patch("app.modules.roadmap.graph.get_llm")
    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_generate_roadmap_with_complete_profile(self, mock_get_llm_for_task, mock_get_llm, client, auth_headers):
        """Test generating a roadmap with a complete profile."""
        mock_get_llm.return_value = make_mock_roadmap_llm()
        mock_get_llm_for_task.side_effect = make_mock_llm_for_task()

        create_complete_profile(client, auth_headers)

        response = client.post(
            "/api/v1/roadmap/generate",
            json={"force_regenerate": True},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["target_role"] == "Backend Developer"
        assert data["total_estimated_hours"] > 0
        assert len(data["phases"]) >= 1
        for phase in data["phases"]:
            assert "tasks" in phase
            assert len(phase["tasks"]) >= 1
            for task in phase["tasks"]:
                assert "title" in task
                assert "estimated_hours" in task
                assert 0.5 <= task["estimated_hours"] <= 8.0

    @patch("app.modules.roadmap.graph.get_llm")
    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_generate_roadmap_without_profile_fails(self, mock_get_llm_for_task, mock_get_llm, client, auth_headers):
        """Test roadmap generation fails without complete profile."""
        mock_get_llm.return_value = make_mock_roadmap_llm()
        mock_get_llm_for_task.side_effect = make_mock_llm_for_task()

        # Don't create profile - just try to generate
        response = client.post(
            "/api/v1/roadmap/generate",
            json={"force_regenerate": True},
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "incomplete" in response.json()["detail"].lower()

    @patch("app.modules.roadmap.graph.get_llm")
    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_generate_roadmap_force_regenerate(self, mock_get_llm_for_task, mock_get_llm, client, auth_headers):
        """Test force_regenerate creates new version."""
        mock_get_llm.return_value = make_mock_roadmap_llm()
        mock_get_llm_for_task.side_effect = make_mock_llm_for_task()

        create_complete_profile(client, auth_headers)

        # Generate first roadmap
        resp1 = client.post("/api/v1/roadmap/generate", json={"force_regenerate": True}, headers=auth_headers)
        assert resp1.status_code == 200
        version1 = resp1.json()["version"]

        # Generate second with force
        resp2 = client.post("/api/v1/roadmap/generate", json={"force_regenerate": True}, headers=auth_headers)
        assert resp2.status_code == 200
        version2 = resp2.json()["version"]

        assert version2 > version1

    @patch("app.modules.roadmap.graph.get_llm")
    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_generate_roadmap_without_force_fails_if_exists(self, mock_get_llm_for_task, mock_get_llm, client, auth_headers):
        """Test generation fails if active roadmap exists and force=False."""
        mock_get_llm.return_value = make_mock_roadmap_llm()
        mock_get_llm_for_task.side_effect = make_mock_llm_for_task()

        create_complete_profile(client, auth_headers)

        # Generate first roadmap
        resp1 = client.post("/api/v1/roadmap/generate", json={"force_regenerate": True}, headers=auth_headers)
        assert resp1.status_code == 200

        # Try to generate again without force
        resp2 = client.post("/api/v1/roadmap/generate", json={"force_regenerate": False}, headers=auth_headers)
        assert resp2.status_code == 400
        assert "active roadmap exists" in resp2.json()["detail"].lower()


class TestRoadmapRetrieval:
    """Tests for getting roadmaps."""

    @patch("app.modules.roadmap.graph.get_llm")
    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_get_active_roadmap(self, mock_get_llm_for_task, mock_get_llm, client, auth_headers):
        """Test getting the active roadmap."""
        mock_get_llm.return_value = make_mock_roadmap_llm()
        mock_get_llm_for_task.side_effect = make_mock_llm_for_task()

        create_complete_profile(client, auth_headers)
        client.post("/api/v1/roadmap/generate", json={"force_regenerate": True}, headers=auth_headers)

        response = client.get("/api/v1/roadmap", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True

    @patch("app.modules.roadmap.graph.get_llm")
    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_get_roadmap_history(self, mock_get_llm_for_task, mock_get_llm, client, auth_headers):
        """Test getting roadmap history."""
        mock_get_llm.return_value = make_mock_roadmap_llm()
        mock_get_llm_for_task.side_effect = make_mock_llm_for_task()

        create_complete_profile(client, auth_headers)
        client.post("/api/v1/roadmap/generate", json={"force_regenerate": True}, headers=auth_headers)
        client.post("/api/v1/roadmap/generate", json={"force_regenerate": True}, headers=auth_headers)

        response = client.get("/api/v1/roadmap/history", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        # Should be ordered newest first
        assert data[0]["version"] > data[1]["version"]

    def test_get_active_roadmap_not_found(self, client, auth_headers):
        """Test 404 when no roadmap exists."""
        response = client.get("/api/v1/roadmap", headers=auth_headers)
        assert response.status_code == 404


class TestRoadmapCompletion:
    """Tests for completion percentage endpoint."""

    @patch("app.modules.roadmap.graph.get_llm")
    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_completion_percentage_calculates_correctly(self, mock_get_llm_for_task, mock_get_llm, client, auth_headers):
        """Test completion percentage based on task hours."""
        mock_get_llm.return_value = make_mock_roadmap_llm()
        mock_get_llm_for_task.side_effect = make_mock_llm_for_task()

        create_complete_profile(client, auth_headers)
        gen_resp = client.post("/api/v1/roadmap/generate", json={"force_regenerate": True}, headers=auth_headers)
        roadmap = gen_resp.json()

        # Get initial completion (should be 0%)
        resp = client.get("/api/v1/roadmap/completion", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["completion_percentage"] == 0.0

        # Complete a task
        if roadmap["phases"] and roadmap["phases"][0]["tasks"]:
            task_id = roadmap["phases"][0]["tasks"][0]["id"]
            client.patch(
                f"/api/v1/roadmap/tasks/{task_id}/status",
                json={"status": "completed"},
                headers=auth_headers,
            )

            # Check completion increased
            resp = client.get("/api/v1/roadmap/completion", headers=auth_headers)
            assert resp.status_code == 200
            assert resp.json()["completion_percentage"] > 0.0


class TestRoadmapTaskOperations:
    """Tests for task CRUD operations."""

    @patch("app.modules.roadmap.graph.get_llm")
    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_task_status_update(self, mock_get_llm_for_task, mock_get_llm, client, auth_headers):
        """Test marking task as completed/pending."""
        mock_get_llm.return_value = make_mock_roadmap_llm()
        mock_get_llm_for_task.side_effect = make_mock_llm_for_task()

        create_complete_profile(client, auth_headers)
        gen_resp = client.post("/api/v1/roadmap/generate", json={"force_regenerate": True}, headers=auth_headers)
        roadmap = gen_resp.json()

        if roadmap["phases"] and roadmap["phases"][0]["tasks"]:
            task_id = roadmap["phases"][0]["tasks"][0]["id"]

            # Mark completed
            resp = client.patch(
                f"/api/v1/roadmap/tasks/{task_id}/status",
                json={"status": "completed"},
                headers=auth_headers,
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "completed"

            # Mark pending again
            resp = client.patch(
                f"/api/v1/roadmap/tasks/{task_id}/status",
                json={"status": "pending"},
                headers=auth_headers,
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "pending"

    @patch("app.modules.roadmap.graph.get_llm")
    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_task_status_invalid_rejected(self, mock_get_llm_for_task, mock_get_llm, client, auth_headers):
        """Test invalid status value is rejected."""
        mock_get_llm.return_value = make_mock_roadmap_llm()
        mock_get_llm_for_task.side_effect = make_mock_llm_for_task()

        create_complete_profile(client, auth_headers)
        gen_resp = client.post("/api/v1/roadmap/generate", json={"force_regenerate": True}, headers=auth_headers)
        roadmap = gen_resp.json()

        if roadmap["phases"] and roadmap["phases"][0]["tasks"]:
            task_id = roadmap["phases"][0]["tasks"][0]["id"]

            resp = client.patch(
                f"/api/v1/roadmap/tasks/{task_id}/status",
                json={"status": "invalid_status"},
                headers=auth_headers,
            )
            assert resp.status_code == 422  # Pydantic validation error

    @patch("app.modules.roadmap.graph.get_llm")
    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_task_details_update(self, mock_get_llm_for_task, mock_get_llm, client, auth_headers):
        """Test updating task title, hours, criteria, tags, due_date."""
        mock_get_llm.return_value = make_mock_roadmap_llm()
        mock_get_llm_for_task.side_effect = make_mock_llm_for_task()

        create_complete_profile(client, auth_headers)
        gen_resp = client.post("/api/v1/roadmap/generate", json={"force_regenerate": True}, headers=auth_headers)
        roadmap = gen_resp.json()

        if roadmap["phases"] and roadmap["phases"][0]["tasks"]:
            task_id = roadmap["phases"][0]["tasks"][0]["id"]

            resp = client.patch(
                f"/api/v1/roadmap/tasks/{task_id}",
                json={
                    "title": "Updated Task Title",
                    "estimated_hours": 5.0,
                    "success_criteria": "Updated criteria",
                    "topic_tags": ["updated", "tag"],
                    "due_date": "2026-06-15"
                },
                headers=auth_headers,
            )
            assert resp.status_code == 200

            # Verify update
            get_resp = client.get("/api/v1/roadmap", headers=auth_headers)
            updated_roadmap = get_resp.json()
            updated_task = next(t for p in updated_roadmap["phases"] for t in p["tasks"] if t["id"] == task_id)
            assert updated_task["title"] == "Updated Task Title"
            assert updated_task["estimated_hours"] == 5.0
            assert updated_task["success_criteria"] == "Updated criteria"
            assert updated_task["topic_tags"] == ["updated", "tag"]
            assert updated_task["due_date"] == "2026-06-15"

    @patch("app.modules.roadmap.graph.get_llm")
    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_task_update_invalid_hours_rejected(self, mock_get_llm_for_task, mock_get_llm, client, auth_headers):
        """Test task hours bounds enforced on update."""
        mock_get_llm.return_value = make_mock_roadmap_llm()
        mock_get_llm_for_task.side_effect = make_mock_llm_for_task()

        create_complete_profile(client, auth_headers)
        gen_resp = client.post("/api/v1/roadmap/generate", json={"force_regenerate": True}, headers=auth_headers)
        roadmap = gen_resp.json()

        if roadmap["phases"] and roadmap["phases"][0]["tasks"]:
            task_id = roadmap["phases"][0]["tasks"][0]["id"]

            resp = client.patch(
                f"/api/v1/roadmap/tasks/{task_id}",
                json={"estimated_hours": 10.0},  # > 8.0
                headers=auth_headers,
            )
            assert resp.status_code == 422

    @patch("app.modules.roadmap.graph.get_llm")
    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_task_not_found_returns_404(self, mock_get_llm_for_task, mock_get_llm, client, auth_headers):
        """Test 404 for non-existent task."""
        mock_get_llm.return_value = make_mock_roadmap_llm()
        mock_get_llm_for_task.side_effect = make_mock_llm_for_task()

        create_complete_profile(client, auth_headers)
        client.post("/api/v1/roadmap/generate", json={"force_regenerate": True}, headers=auth_headers)

        resp = client.patch(
            "/api/v1/roadmap/tasks/non-existent-id/status",
            json={"status": "completed"},
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestRoadmapAdaptations:
    """Tests for adaptation proposal workflow."""

    @patch("app.modules.roadmap.graph.get_llm")
    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_create_adaptation_proposal(self, mock_get_llm_for_task, mock_get_llm, client, auth_headers):
        """Test creating an adaptation proposal."""
        mock_get_llm.return_value = make_mock_roadmap_llm()
        mock_get_llm_for_task.side_effect = make_mock_llm_for_task()

        create_complete_profile(client, auth_headers)
        client.post("/api/v1/roadmap/generate", json={"force_regenerate": True}, headers=auth_headers)

        resp = client.post(
            "/api/v1/roadmap/adaptations",
            json={
                "source_type": "interview",
                "source_id": "interview_123",
                "proposed_tasks": [
                    {"title": "System Design Deep Dive", "estimated_hours": 6, "success_criteria": "Design URL shortener", "topic_tags": ["system design"]}
                ],
            },
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["source_type"] == "interview"
        assert data["source_id"] == "interview_123"
        assert data["status"] == "proposed"
        assert len(data["proposed_tasks"]) == 1
        assert "id" in data

    @patch("app.modules.roadmap.graph.get_llm")
    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_list_adaptations(self, mock_get_llm_for_task, mock_get_llm, client, auth_headers):
        """Test listing adaptation proposals."""
        mock_get_llm.return_value = make_mock_roadmap_llm()
        mock_get_llm_for_task.side_effect = make_mock_llm_for_task()

        create_complete_profile(client, auth_headers)
        client.post("/api/v1/roadmap/generate", json={"force_regenerate": True}, headers=auth_headers)

        # Create two proposals
        client.post("/api/v1/roadmap/adaptations", json={
            "source_type": "interview", "source_id": "int_1",
            "proposed_tasks": [{"title": "Task 1", "estimated_hours": 4, "success_criteria": "Done", "topic_tags": ["a"]}],
        }, headers=auth_headers)
        client.post("/api/v1/roadmap/adaptations", json={
            "source_type": "resume", "source_id": "res_1",
            "proposed_tasks": [{"title": "Task 2", "estimated_hours": 4, "success_criteria": "Done", "topic_tags": ["b"]}],
        }, headers=auth_headers)

        resp = client.get("/api/v1/roadmap/adaptations", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        # Newest first
        assert data[0]["source_id"] == "res_1"

    @patch("app.modules.roadmap.graph.get_llm")
    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_approve_adaptation_applies_tasks(self, mock_get_llm_for_task, mock_get_llm, client, auth_headers):
        """Test approving adaptation adds tasks to roadmap."""
        mock_get_llm.return_value = make_mock_roadmap_llm()
        mock_get_llm_for_task.side_effect = make_mock_llm_for_task()

        create_complete_profile(client, auth_headers)
        gen_resp = client.post("/api/v1/roadmap/generate", json={"force_regenerate": True}, headers=auth_headers)
        initial_task_count = sum(len(p["tasks"]) for p in gen_resp.json()["phases"])

        # Create proposal
        create_resp = client.post("/api/v1/roadmap/adaptations", json={
            "source_type": "interview", "source_id": "int_1",
            "proposed_tasks": [
                {"title": "New Task 1", "estimated_hours": 4, "success_criteria": "Done", "topic_tags": ["a"]},
                {"title": "New Task 2", "estimated_hours": 3, "success_criteria": "Done", "topic_tags": ["b"]},
            ],
        }, headers=auth_headers)
        adaptation_id = create_resp.json()["id"]

        # Approve
        approve_resp = client.post(
            f"/api/v1/roadmap/adaptations/{adaptation_id}/action",
            json={"action": "approve"},
            headers=auth_headers,
        )
        assert approve_resp.status_code == 200

        # Verify tasks added
        get_resp = client.get("/api/v1/roadmap", headers=auth_headers)
        final_task_count = sum(len(p["tasks"]) for p in get_resp.json()["phases"])
        assert final_task_count == initial_task_count + 2

    @patch("app.modules.roadmap.graph.get_llm")
    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_reject_adaptation(self, mock_get_llm_for_task, mock_get_llm, client, auth_headers):
        """Test rejecting adaptation marks it rejected."""
        mock_get_llm.return_value = make_mock_roadmap_llm()
        mock_get_llm_for_task.side_effect = make_mock_llm_for_task()

        create_complete_profile(client, auth_headers)
        client.post("/api/v1/roadmap/generate", json={"force_regenerate": True}, headers=auth_headers)

        create_resp = client.post("/api/v1/roadmap/adaptations", json={
            "source_type": "interview", "source_id": "int_1",
            "proposed_tasks": [{"title": "Task", "estimated_hours": 4, "success_criteria": "Done", "topic_tags": ["a"]}],
        }, headers=auth_headers)
        adaptation_id = create_resp.json()["id"]

        reject_resp = client.post(
            f"/api/v1/roadmap/adaptations/{adaptation_id}/action",
            json={"action": "reject"},
            headers=auth_headers,
        )
        assert reject_resp.status_code == 200
        assert reject_resp.json()["message"] == "Adaptation rejected"

        # Verify proposal status
        list_resp = client.get("/api/v1/roadmap/adaptations", headers=auth_headers)
        assert list_resp.json()[0]["status"] == "rejected"

    @patch("app.modules.roadmap.graph.get_llm")
    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_approve_nonexistent_adaptation_400(self, mock_get_llm_for_task, mock_get_llm, client, auth_headers):
        """Test approving non-existent adaptation returns 400."""
        mock_get_llm.return_value = make_mock_roadmap_llm()
        mock_get_llm_for_task.side_effect = make_mock_llm_for_task()

        create_complete_profile(client, auth_headers)
        client.post("/api/v1/roadmap/generate", json={"force_regenerate": True}, headers=auth_headers)

        resp = client.post(
            "/api/v1/roadmap/adaptations/non-existent-id/action",
            json={"action": "approve"},
            headers=auth_headers,
        )
        assert resp.status_code == 400


class TestRoadmapAuthorization:
    """Tests for authorization / data isolation."""

    @patch("app.modules.roadmap.graph.get_llm")
    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_student_cannot_access_other_student_roadmap(self, mock_get_llm_for_task, mock_get_llm, client):
        """Test that student A cannot access student B's roadmap."""
        mock_get_llm.return_value = make_mock_roadmap_llm()
        mock_get_llm_for_task.side_effect = make_mock_llm_for_task()

        # Student A creates profile and roadmap
        headers_a = {"Authorization": "Bearer mock_student_a"}
        client.put("/api/v1/profile", json={
            "target_role": "Backend Developer", "company_type": "product",
            "weekly_study_hours": 10, "skills": [{"name": "Python", "level": "advanced"}],
            "education": [{"institution": "Uni", "degree": "B.Tech", "year_of_completion": 2024}],
        }, headers=headers_a)
        client.post("/api/v1/roadmap/generate", json={"force_regenerate": True}, headers=headers_a)

        # Student B tries to access
        headers_b = {"Authorization": "Bearer mock_student_b"}
        resp = client.get("/api/v1/roadmap", headers=headers_b)
        assert resp.status_code == 404  # No roadmap for student B

        # Student B tries to access student A's roadmap via task operations
        # (tasks are scoped to student's active roadmap)
        resp = client.patch("/api/v1/roadmap/tasks/some-id/status", json={"status": "completed"}, headers=headers_b)
        assert resp.status_code == 404


class TestRoadmapEdgeCases:
    """Edge case tests."""

    @patch("app.modules.roadmap.graph.get_llm")
    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_completion_with_no_roadmap_returns_zero(self, mock_get_llm_for_task, mock_get_llm, client, auth_headers):
        """Completion endpoint returns 0% when no roadmap."""
        mock_get_llm.return_value = make_mock_roadmap_llm()
        mock_get_llm_for_task.side_effect = make_mock_llm_for_task()

        resp = client.get("/api/v1/roadmap/completion", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["completion_percentage"] == 0.0

    @patch("app.modules.roadmap.graph.get_llm")
    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_adaptations_list_empty_when_no_roadmap(self, mock_get_llm_for_task, mock_get_llm, client, auth_headers):
        """Adaptations list returns empty when no roadmap."""
        mock_get_llm.return_value = make_mock_roadmap_llm()
        mock_get_llm_for_task.side_effect = make_mock_llm_for_task()

        resp = client.get("/api/v1/roadmap/adaptations", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @patch("app.modules.roadmap.graph.get_llm")
    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_task_update_due_date(self, mock_get_llm_for_task, mock_get_llm, client, auth_headers):
        """Test updating task due_date."""
        mock_get_llm.return_value = make_mock_roadmap_llm()
        mock_get_llm_for_task.side_effect = make_mock_llm_for_task()

        create_complete_profile(client, auth_headers)
        gen_resp = client.post("/api/v1/roadmap/generate", json={"force_regenerate": True}, headers=auth_headers)
        roadmap = gen_resp.json()

        if roadmap["phases"] and roadmap["phases"][0]["tasks"]:
            task_id = roadmap["phases"][0]["tasks"][0]["id"]

            resp = client.patch(
                f"/api/v1/roadmap/tasks/{task_id}",
                json={"due_date": "2026-07-01"},
                headers=auth_headers,
            )
            assert resp.status_code == 200

            get_resp = client.get("/api/v1/roadmap", headers=auth_headers)
            updated_task = next(t for p in get_resp.json()["phases"] for t in p["tasks"] if t["id"] == task_id)
            assert updated_task["due_date"] == "2026-07-01"

    @patch("app.modules.roadmap.graph.get_llm")
    @patch("app.modules.roadmap.graph.get_llm_for_task")
    def test_task_update_clears_due_date(self, mock_get_llm_for_task, mock_get_llm, client, auth_headers):
        """Test setting due_date to null clears it."""
        mock_get_llm.return_value = make_mock_roadmap_llm()
        mock_get_llm_for_task.side_effect = make_mock_llm_for_task()

        create_complete_profile(client, auth_headers)
        gen_resp = client.post("/api/v1/roadmap/generate", json={"force_regenerate": True}, headers=auth_headers)
        roadmap = gen_resp.json()

        if roadmap["phases"] and roadmap["phases"][0]["tasks"]:
            task_id = roadmap["phases"][0]["tasks"][0]["id"]

            # First set a due date
            client.patch(f"/api/v1/roadmap/tasks/{task_id}", json={"due_date": "2026-07-01"}, headers=auth_headers)

            # Then clear it
            resp = client.patch(
                f"/api/v1/roadmap/tasks/{task_id}",
                json={"due_date": None},
                headers=auth_headers,
            )
            assert resp.status_code == 200

            get_resp = client.get("/api/v1/roadmap", headers=auth_headers)
            updated_task = next(t for p in get_resp.json()["phases"] for t in p["tasks"] if t["id"] == task_id)
            assert updated_task["due_date"] is None