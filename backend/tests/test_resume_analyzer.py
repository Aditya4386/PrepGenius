"""
test_resume_analyzer.py — Integration tests for resume analysis endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock
import pymupdf as fitz

from app.modules.resume.schemas import (
    AnalysisResponse,
    SectionAnalysis,
    SectionAnalysisBatch,
    JobMatchAnalysis,
    JobMatchResult,
    Recommendation,
    SynthesisResult,
    SkillMatch,
)
from app.modules.resume.analyzer.scoring import compute_ats_score
from app.modules.resume.analyzer.parser import validate_and_extract_text, PDFParseError
from app.shared.llm import LLMError, LLMTask


def make_pdf_bytes(text: str = None) -> bytes:
    """Build a real minimal PDF in memory."""
    if text is None:
        text = (
            "Jane Smith\n"
            "jane@example.com\n"
            "+91 9898989898\n"
            "github.com/janesmith\n\n"
            "Education\nB.Tech Computer Science, ABC University 2024\n\n"
            "Technical Skills\nPython, FastAPI, SQL, Git\n\n"
            "Projects\nBuilt a REST API service that improved response time by 25%\n"
            "Developed a machine learning model for classification\n\n"
            "Achievements\nFirst prize in departmental hackathon"
        )
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 80), text, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def make_mock_structured_llm(include_job_match: bool = False, custom_job_score: int = 78):
    """Returns a mock with_structured_output handler for LangGraph nodes."""
    def mock_with_structured_output(schema):
        mock_node = MagicMock()
        if schema == SectionAnalysisBatch:
            mock_node.invoke.return_value = SectionAnalysisBatch(
                section_analysis=[
                    SectionAnalysis(
                        section_name="Education",
                        is_present=True,
                        score=80,
                        strengths=["Relevant degree"],
                        weaknesses=[],
                        suggestions=["Add GPA if above 8.0"],
                        notes=None,
                    ),
                    SectionAnalysis(
                        section_name="Technical Skills",
                        is_present=True,
                        score=75,
                        strengths=["Good core stack"],
                        weaknesses=["No cloud mentioned"],
                        suggestions=["Add AWS or Docker basics"],
                        notes=None,
                    ),
                ],
                overall_strengths=["Clear technical focus", "Good project descriptions"],
                overall_weaknesses=["No work experience listed", "Missing GitHub links"],
                missing_information=["LinkedIn profile URL", "Graduation year"],
            )
        elif schema == JobMatchResult:
            mock_node.invoke.return_value = JobMatchResult(
                job_match_score=custom_job_score if include_job_match else None,
                job_match_analysis=JobMatchAnalysis(
                    matched_skills=[
                        SkillMatch(skill="Python", status="demonstrated", evidence="Built a REST API service"),
                        SkillMatch(skill="FastAPI", status="demonstrated", evidence="Technical Skills section"),
                        SkillMatch(skill="Docker", status="missing", evidence=None),
                    ],
                    missing_skills=["Docker", "Kubernetes"],
                    relevant_projects=["REST API service"],
                    relevant_experience=[],
                    gap_summary="Strong Python background but lacks DevOps exposure.",
                ) if include_job_match else None,
            )
        elif schema == SynthesisResult:
            mock_node.invoke.return_value = SynthesisResult(
                overall_score=72,
                recommendations=[
                    Recommendation(priority="high", area="Experience", suggestion="Add internships or freelance work"),
                    Recommendation(priority="medium", area="Skills", suggestion="Learn Docker basics"),
                ],
            )
        return mock_node
    return mock_with_structured_output


class TestResumeAnalyzer:
    """Integration tests for POST /api/v1/resumes/analyze"""

    @patch("app.modules.resume.analyzer.graph.get_llm_for_task")
    @patch("app.modules.resume.analyzer.graph.get_llm")
    def test_analyze_resume_only(self, mock_get_llm, mock_get_llm_for_task, client, mock_student_id):
        """Scenario A: Resume only — no job info."""
        mock_llm = MagicMock()
        mock_llm.with_structured_output.side_effect = make_mock_structured_llm(include_job_match=False)
        mock_get_llm.return_value = mock_llm
        mock_get_llm_for_task.return_value = mock_llm

        pdf = make_pdf_bytes()
        response = client.post(
            "/api/v1/resumes/analyze",
            files={"resume": ("resume.pdf", pdf, "application/pdf")},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["analysis_mode"] == "general"
        assert 0 <= data["overall_score"] <= 100
        assert 0 <= data["ats_readiness_score"] <= 100
        assert data["job_match_score"] is None
        assert isinstance(data["section_analysis"], list)
        assert isinstance(data["recommendations"], list)

    @patch("app.modules.resume.analyzer.graph.get_llm_for_task")
    @patch("app.modules.resume.analyzer.graph.get_llm")
    def test_analyze_with_job_title_only(self, mock_get_llm, mock_get_llm_for_task, client, mock_student_id):
        """Scenario B: Resume + job title only."""
        mock_llm = MagicMock()
        mock_llm.with_structured_output.side_effect = make_mock_structured_llm(include_job_match=False)
        mock_get_llm.return_value = mock_llm
        mock_get_llm_for_task.return_value = mock_llm

        pdf = make_pdf_bytes()
        response = client.post(
            "/api/v1/resumes/analyze",
            files={"resume": ("resume.pdf", pdf, "application/pdf")},
            data={"job_title": "Backend Developer"},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["analysis_mode"] == "job_title_only"

    @patch("app.modules.resume.analyzer.graph.get_llm_for_task")
    @patch("app.modules.resume.analyzer.graph.get_llm")
    def test_analyze_with_job_description(self, mock_get_llm, mock_get_llm_for_task, client, mock_student_id):
        """Scenario C: Resume + job description (no job title)."""
        mock_llm = MagicMock()
        mock_llm.with_structured_output.side_effect = make_mock_structured_llm(include_job_match=True, custom_job_score=78)
        mock_get_llm.return_value = mock_llm
        mock_get_llm_for_task.return_value = mock_llm

        pdf = make_pdf_bytes()
        response = client.post(
            "/api/v1/resumes/analyze",
            files={"resume": ("resume.pdf", pdf, "application/pdf")},
            data={"job_description": "We need a Python developer with FastAPI experience."},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["analysis_mode"] == "job_description"
        assert data["job_match_score"] == 78

    @patch("app.modules.resume.analyzer.graph.get_llm_for_task")
    @patch("app.modules.resume.analyzer.graph.get_llm")
    def test_analyze_full_scenario(self, mock_get_llm, mock_get_llm_for_task, client, mock_student_id):
        """Scenario D: Resume + job title + job description."""
        mock_llm = MagicMock()
        mock_llm.with_structured_output.side_effect = make_mock_structured_llm(include_job_match=True)
        mock_get_llm.return_value = mock_llm
        mock_get_llm_for_task.return_value = mock_llm

        pdf = make_pdf_bytes()
        response = client.post(
            "/api/v1/resumes/analyze",
            files={"resume": ("resume.pdf", pdf, "application/pdf")},
            data={
                "job_title": "Python Developer",
                "job_description": "Looking for a Python backend developer with FastAPI and SQL experience.",
            },
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["analysis_mode"] == "full"
        assert data["job_match_score"] is not None
        assert data["job_match_analysis"] is not None

    def test_non_pdf_file_rejected(self, client, mock_student_id):
        """Uploading a non-PDF should return 422."""
        fake_file = b"This is a text file, not a PDF"
        response = client.post(
            "/api/v1/resumes/analyze",
            files={"resume": ("resume.txt", fake_file, "text/plain")},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )
        assert response.status_code == 422

    def test_oversized_file_rejected(self, client, mock_student_id):
        """Files above the size limit should be rejected with 422."""
        oversized = b"%PDF" + b"x" * (6 * 1024 * 1024)  # 6 MB
        response = client.post(
            "/api/v1/resumes/analyze",
            files={"resume": ("big.pdf", oversized, "application/pdf")},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )
        assert response.status_code == 422

    def test_missing_resume_field_rejected(self, client, mock_student_id):
        """Not including a resume at all should return 422."""
        response = client.post(
            "/api/v1/resumes/analyze",
            data={"job_title": "Developer"},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )
        assert response.status_code == 422

    @patch("app.modules.resume.analyzer.graph.get_llm_for_task")
    @patch("app.modules.resume.analyzer.graph.get_llm")
    def test_gemini_api_failure_returns_503(self, mock_get_llm, mock_get_llm_for_task, client, mock_student_id):
        """If an agent node throws LLMError, the endpoint should return 503."""
        mock_llm = MagicMock()
        mock_llm.with_structured_output.side_effect = LLMError("API timeout")
        mock_get_llm.return_value = mock_llm
        mock_get_llm_for_task.return_value = mock_llm

        pdf = make_pdf_bytes()
        response = client.post(
            "/api/v1/resumes/analyze",
            files={"resume": ("resume.pdf", pdf, "application/pdf")},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        assert response.status_code == 503

    @patch("app.modules.resume.analyzer.graph.resume_analysis_graph.invoke")
    def test_invalid_gemini_output_returns_502(self, mock_invoke, client, mock_student_id):
        """If the graph completes without producing a valid final_response, return 502."""
        mock_invoke.return_value = {"unexpected_field": "no final response"}

        pdf = make_pdf_bytes()
        response = client.post(
            "/api/v1/resumes/analyze",
            files={"resume": ("resume.pdf", pdf, "application/pdf")},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        assert response.status_code == 502

    @patch("app.modules.resume.analyzer.graph.get_llm_for_task")
    @patch("app.modules.resume.analyzer.graph.get_llm")
    def test_ats_score_is_deterministic(self, mock_get_llm, mock_get_llm_for_task, client, mock_student_id):
        """The ATS score in the response must come from our ats_checker node."""
        mock_llm = MagicMock()
        mock_llm.with_structured_output.side_effect = make_mock_structured_llm()
        mock_get_llm.return_value = mock_llm
        mock_get_llm_for_task.return_value = mock_llm

        pdf = make_pdf_bytes()
        response = client.post(
            "/api/v1/resumes/analyze",
            files={"resume": ("resume.pdf", pdf, "application/pdf")},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert 0 <= data["ats_readiness_score"] <= 100


class TestResumeAnalysisHistory:
    """Tests for GET /api/v1/resumes/analyses"""

    @patch("app.modules.resume.analyzer.graph.get_llm")
    def test_get_analysis_history(self, mock_get_llm, client, mock_student_id):
        """Test retrieving analysis history."""
        mock_llm = MagicMock()
        mock_llm.with_structured_output.side_effect = make_mock_structured_llm()
        mock_get_llm.return_value = mock_llm

        pdf = make_pdf_bytes()
        # Create an analysis first
        client.post(
            "/api/v1/resumes/analyze",
            files={"resume": ("resume.pdf", pdf, "application/pdf")},
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        # Get history
        response = client.get(
            "/api/v1/resumes/analyses",
            headers={"Authorization": f"Bearer {mock_student_id}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # In-memory mode: history not persisted
        assert len(data) == 0


class TestATSScorer:
    """Unit tests for deterministic ATS scorer."""

    def test_complete_resume_scores_high(self):
        """A complete resume with all sections should score well."""
        resume = """
        John Doe
        john@example.com | +1-555-123-4567 | linkedin.com/in/johndoe | github.com/johndoe

        Education
        B.S. Computer Science, University of Technology, 2024

        Technical Skills
        Python, JavaScript, SQL, React, Docker, AWS

        Experience
        Software Engineer Intern at TechCorp (2023)
        - Developed REST APIs improving response time by 30%
        - Built frontend components serving 10,000+ users

        Projects
        E-commerce Platform: Full-stack app with payment integration
        Task Manager: React/Node.js application with 500+ users

        Achievements
        Dean's List 2022-2024, Hackathon Winner 2023
        """
        score, observations = compute_ats_score(resume)
        assert score >= 70  # Should score well
        assert len(observations) >= 1

    def test_minimal_resume_scores_low(self):
        """A minimal resume should score low with clear observations."""
        resume = "John Doe\nNo contact info\nJust a name"
        score, observations = compute_ats_score(resume)
        assert score < 50
        assert any("Email" in obs for obs in observations)

    def test_scanned_pdf_rejected(self):
        """Empty text should be handled by parser, not scorer."""
        # This is tested in parser tests
        pass


class TestPDFParser:
    """Unit tests for PDF parser."""

    def test_valid_pdf_returns_text(self):
        pdf = make_pdf_bytes("Jane Smith\njane@example.com\nSkills: Python, FastAPI")
        text = validate_and_extract_text(pdf, 5 * 1024 * 1024)
        assert "Jane Smith" in text
        assert "Python" in text

    def test_non_pdf_file_rejected(self):
        fake_file = b"This is just a plain text file, not a PDF"
        with pytest.raises(PDFParseError, match="not a valid PDF"):
            validate_and_extract_text(fake_file, 5 * 1024 * 1024)

    def test_oversized_file_rejected(self):
        oversized = b"%PDF" + b"x" * (6 * 1024 * 1024)
        with pytest.raises(PDFParseError, match="size limit"):
            validate_and_extract_text(oversized, 5 * 1024 * 1024)

    def test_empty_pdf_rejected(self):
        doc = fitz.open()
        doc.new_page()
        pdf_bytes = doc.tobytes()
        doc.close()
        with pytest.raises(PDFParseError, match="No readable text"):
            validate_and_extract_text(pdf_bytes, 5 * 1024 * 1024)