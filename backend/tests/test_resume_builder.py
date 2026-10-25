"""
test_resume_builder.py — Integration tests for resume builder endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock
import json


def make_mock_builder_llm():
    """Mock LLM responses for builder graph nodes."""
    def mock_invoke(prompt):
        mock_response = MagicMock()
        if "Job Description Analyzer" in prompt:
            mock_response.content = json.dumps({"keywords": ["Python", "FastAPI", "SQL", "Docker", "AWS", "REST API"]})
        elif "Resume Writing Coach" in prompt and "Generate ONE targeted question" in prompt:
            mock_response.content = "Describe your experience with Python and FastAPI. Include specific projects where you built REST APIs."
        elif "evaluating if a student's answer is sufficient" in prompt:
            mock_response.content = json.dumps({"needs_followup": False, "followup_question": None})
        elif "Professional Resume Writer" in prompt and "Draft the" in prompt:
            mock_response.content = "• Built REST APIs using Python and FastAPI\n• Implemented authentication and authorization\n• Integrated with PostgreSQL database"
        elif "assembling a complete resume" in prompt:
            mock_response.content = json.dumps({
                "resume": "JANE SMITH\njane@example.com | +91 9898989898 | github.com/janesmith\n\nPROFESSIONAL SUMMARY\nMotivated backend developer with experience in Python, FastAPI, and SQL.\n\nEDUCATION\nB.Tech Computer Science, ABC University, 2024\n\nTECHNICAL SKILLS\nPython, FastAPI, SQL, Git, Docker\n\nPROJECTS\n• REST API Service: Built a REST API service that improved response time by 25%\n• ML Classification Model: Developed a machine learning model for classification\n\nACHIEVEMENTS\n• First prize in departmental hackathon",
                "keyword_coverage": {
                    "covered_keywords": ["Python", "FastAPI", "SQL"],
                    "missing_keywords": ["Docker", "AWS", "REST API"],
                    "coverage_percentage": 50
                }
            })
        else:
            mock_response.content = "Default response"
        return mock_response

    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = mock_invoke
    return mock_llm


class TestResumeBuilder:
    """Integration tests for resume builder endpoints."""

    @patch("app.modules.resume.builder.graph.get_llm")
    def test_start_builder_session(self, mock_get_llm, client, mock_student_id):
        """Test starting a new builder session."""
        mock_get_llm.return_value = make_mock_builder_llm()

        response = client.post(
            "/api/v1/resumes/builder/start",
            data={
                "job_title": "Backend Developer",
                "job_description": "We need a Python developer with FastAPI, SQL, and Docker experience.",
            },
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["job_title"] == "Backend Developer"
        assert data["status"] == "in_progress"
        assert data["current_section"] == "contact"
        assert "id" in data

    @patch("app.modules.resume.builder.graph.get_llm")
    def test_submit_answer_gets_question(self, mock_get_llm, client, mock_student_id):
        """Test submitting an answer returns next question or draft."""
        mock_get_llm.return_value = make_mock_builder_llm()

        # Start session
        start_resp = client.post(
            "/api/v1/resumes/builder/start",
            data={
                "job_title": "Backend Developer",
                "job_description": "Python, FastAPI, SQL, Docker",
            },
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )
        session_id = start_resp.json()["id"]

        # Submit answer for contact section
        response = client.post(
            f"/api/v1/resumes/builder/sessions/{session_id}/answer",
            json={"section": "contact", "answer": "Jane Smith, jane@example.com, +91 9898989898, github.com/janesmith"},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["section"] == "contact"
        assert "draft" in data
        assert "needs_followup" in data

    @patch("app.modules.resume.builder.graph.get_llm")
    def test_submit_wrong_section_rejected(self, mock_get_llm, client, mock_student_id):
        """Test submitting answer for wrong section is rejected."""
        mock_get_llm.return_value = make_mock_builder_llm()

        # Start session
        start_resp = client.post(
            "/api/v1/resumes/builder/start",
            data={
                "job_title": "Backend Developer",
                "job_description": "Python, FastAPI, SQL, Docker",
            },
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )
        session_id = start_resp.json()["id"]

        # Try to submit answer for education section when current is contact
        response = client.post(
            f"/api/v1/resumes/builder/sessions/{session_id}/answer",
            json={"section": "education", "answer": "Some education info"},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        assert response.status_code == 400
        assert "current section" in response.json()["detail"].lower()

    @patch("app.modules.resume.builder.graph.get_llm")
    def test_approve_section(self, mock_get_llm, client, mock_student_id):
        """Test approving a drafted section."""
        mock_get_llm.return_value = make_mock_builder_llm()

        # Start session
        start_resp = client.post(
            "/api/v1/resumes/builder/start",
            data={
                "job_title": "Backend Developer",
                "job_description": "Python, FastAPI, SQL, Docker",
            },
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )
        session_id = start_resp.json()["id"]

        # Submit answer
        client.post(
            f"/api/v1/resumes/builder/sessions/{session_id}/answer",
            json={"section": "contact", "answer": "Jane Smith, jane@example.com, +91 9898989898"},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        # Approve section
        response = client.post(
            f"/api/v1/resumes/builder/sessions/{session_id}/approve",
            data={
                "section": "contact",
                "content": "Jane Smith\njane@example.com\n+91 9898989898\ngithub.com/janesmith",
            },
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["section"] == "contact"
        assert "next_section" in data

    @patch("app.modules.resume.builder.graph.get_llm")
    def test_approve_wrong_section_rejected(self, mock_get_llm, client, mock_student_id):
        """Test approving wrong section is rejected."""
        mock_get_llm.return_value = make_mock_builder_llm()

        # Start session
        start_resp = client.post(
            "/api/v1/resumes/builder/start",
            data={
                "job_title": "Backend Developer",
                "job_description": "Python, FastAPI, SQL, Docker",
            },
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )
        session_id = start_resp.json()["id"]

        # Submit answer for contact
        client.post(
            f"/api/v1/resumes/builder/sessions/{session_id}/answer",
            json={"section": "contact", "answer": "Jane Smith, jane@example.com, +91 9898989898"},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        # Try to approve education section when current is contact
        response = client.post(
            f"/api/v1/resumes/builder/sessions/{session_id}/approve",
            data={
                "section": "education",
                "content": "Some education",
            },
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        assert response.status_code == 400
        assert "current section" in response.json()["detail"].lower()

    @patch("app.modules.resume.builder.graph.get_llm")
    def test_get_session_status(self, mock_get_llm, client, mock_student_id):
        """Test getting session status."""
        mock_get_llm.return_value = make_mock_builder_llm()

        # Start session
        start_resp = client.post(
            "/api/v1/resumes/builder/start",
            data={
                "job_title": "Backend Developer",
                "job_description": "Python, FastAPI, SQL, Docker",
            },
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )
        session_id = start_resp.json()["id"]

        # Get status
        response = client.get(
            f"/api/v1/resumes/builder/sessions/{session_id}/status",
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert data["status"] == "in_progress"
        assert data["current_section"] == "contact"
        assert data["total_sections"] == 7

    @patch("app.modules.resume.builder.graph.get_llm")
    def test_export_resume_not_completed(self, mock_get_llm, client, mock_student_id):
        """Test exporting resume before completion returns error."""
        mock_get_llm.return_value = make_mock_builder_llm()

        # Start session
        start_resp = client.post(
            "/api/v1/resumes/builder/start",
            data={
                "job_title": "Backend Developer",
                "job_description": "Python, FastAPI, SQL, Docker",
            },
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )
        session_id = start_resp.json()["id"]

        # Try to export before completion
        response = client.get(
            f"/api/v1/resumes/builder/sessions/{session_id}/export",
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        assert response.status_code == 400
        assert "not yet completed" in response.json()["detail"].lower()

    @patch("app.modules.resume.builder.graph.get_llm")
    def test_full_workflow_turn_based(self, mock_get_llm, client, mock_student_id):
        """Test the complete turn-based workflow: answer -> draft -> approve -> next section."""
        mock_get_llm.return_value = make_mock_builder_llm()

        # Start session
        start_resp = client.post(
            "/api/v1/resumes/builder/start",
            data={
                "job_title": "Backend Developer",
                "job_description": "Python, FastAPI, SQL, Docker",
            },
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )
        session_id = start_resp.json()["id"]
        assert start_resp.json()["current_section"] == "contact"

        # Submit answer for contact
        resp = client.post(
            f"/api/v1/resumes/builder/sessions/{session_id}/answer",
            json={"section": "contact", "answer": "Jane Smith, jane@example.com, +91 9898989898"},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )
        assert resp.status_code == 200
        assert resp.json()["needs_followup"] is False

        # Approve contact
        resp = client.post(
            f"/api/v1/resumes/builder/sessions/{session_id}/approve",
            data={"section": "contact", "content": "Jane Smith\njane@example.com\n+91 9898989898"},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )
        assert resp.status_code == 200
        assert resp.json()["next_section"] == "education"

        # Verify status
        status_resp = client.get(
            f"/api/v1/resumes/builder/sessions/{session_id}/status",
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )
        assert status_resp.status_code == 200
        assert status_resp.json()["current_section"] == "education"
        assert "contact" in status_resp.json()["completed_sections"]

        # Submit answer for education
        resp = client.post(
            f"/api/v1/resumes/builder/sessions/{session_id}/answer",
            json={"section": "education", "answer": "B.Tech CS, ABC University, 2024"},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )
        assert resp.status_code == 200

        # Approve education
        resp = client.post(
            f"/api/v1/resumes/builder/sessions/{session_id}/approve",
            data={"section": "education", "content": "B.Tech CS, ABC University, 2024"},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )
        assert resp.status_code == 200
        assert resp.json()["next_section"] == "skills"

        # Verify status shows both completed
        status_resp = client.get(
            f"/api/v1/resumes/builder/sessions/{session_id}/status",
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )
        assert "education" in status_resp.json()["completed_sections"]
        assert "contact" in status_resp.json()["completed_sections"]


class TestResumeExporter:
    """Unit tests for PDF exporter."""

    def test_create_resume_pdf(self):
        """Test creating a PDF from resume text."""
        from app.modules.resume.exporter.exporter import create_resume_pdf

        resume_text = """JANE SMITH
jane@example.com | +91 9898989898 | github.com/janesmith

PROFESSIONAL SUMMARY
Motivated backend developer with experience in Python, FastAPI, and SQL.

EDUCATION
B.Tech Computer Science, ABC University, 2024

TECHNICAL SKILLS
Python, FastAPI, SQL, Git, Docker

PROJECTS
• REST API Service: Built a REST API service that improved response time by 25%
• ML Classification Model: Developed a machine learning model for classification

ACHIEVEMENTS
• First prize in departmental hackathon"""

        pdf_bytes = create_resume_pdf(resume_text)
        assert len(pdf_bytes) > 1000  # Should be a valid PDF
        assert pdf_bytes[:4] == b"%PDF"  # PDF magic bytes

    def test_create_simple_resume_pdf(self):
        """Test creating PDF from structured data."""
        from app.modules.resume.exporter.exporter import create_simple_resume_pdf

        pdf_bytes = create_simple_resume_pdf(
            name="Jane Smith",
            contact_lines=["jane@example.com", "+91 9898989898", "github.com/janesmith"],
            sections={
                "Professional Summary": "Motivated backend developer...",
                "Education": ["B.Tech Computer Science, ABC University, 2024"],
                "Technical Skills": "Python, FastAPI, SQL, Git, Docker",
                "Projects": [
                    "REST API Service: Built a REST API service that improved response time by 25%",
                    "ML Classification Model: Developed a machine learning model for classification",
                ],
                "Achievements": ["First prize in departmental hackathon"],
            },
        )
        assert len(pdf_bytes) > 1000
        assert pdf_bytes[:4] == b"%PDF"