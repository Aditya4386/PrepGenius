from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Section-level models
# ---------------------------------------------------------------------------

class SectionAnalysis(BaseModel):
    """Analysis result for one resume section (e.g. Education, Skills)."""
    section_name: str
    is_present: bool
    score: Optional[int] = Field(None, ge=0, le=100)
    strengths: List[str] = []
    weaknesses: List[str] = []
    suggestions: List[str] = []
    notes: Optional[str] = None


class SkillMatch(BaseModel):
    """How one skill from the job description maps onto the resume."""
    skill: str
    # "demonstrated" | "mentioned" | "missing"
    status: str
    evidence: Optional[str] = None  # Quote or reference from the resume


class JobMatchAnalysis(BaseModel):
    """Populated only when a job description is provided."""
    matched_skills: List[SkillMatch] = []
    missing_skills: List[str] = []
    relevant_projects: List[str] = []
    relevant_experience: List[str] = []
    gap_summary: str = ""


class Recommendation(BaseModel):
    priority: str          # "high" | "medium" | "low"
    area: str              # e.g. "Projects", "Skills", "Formatting"
    suggestion: str


# ---------------------------------------------------------------------------
# Node-specific models for LangGraph multi-agent pipeline
# ---------------------------------------------------------------------------

class SectionAnalysisBatch(BaseModel):
    """Output produced by the Section Analyzer agent node."""
    section_analysis: List[SectionAnalysis]
    overall_strengths: List[str] = []
    overall_weaknesses: List[str] = []
    missing_information: List[str] = []


class JobMatchResult(BaseModel):
    """Output produced by the Job Matcher agent node."""
    job_match_score: Optional[int] = Field(None, ge=0, le=100)
    job_match_analysis: Optional[JobMatchAnalysis] = None


class SynthesisResult(BaseModel):
    """Output produced by the Recommendation Synthesizer agent node."""
    overall_score: int = Field(ge=0, le=100)
    recommendations: List[Recommendation] = []


# ---------------------------------------------------------------------------
# What Gemini returns (internal model, not the final API response)
# ---------------------------------------------------------------------------

class GeminiAnalysisResult(BaseModel):
    """
    The structured object representing full analysis result.
    Validated before being used in the API response.
    """
    overall_score: int = Field(ge=0, le=100)
    ats_readiness_score: int = Field(ge=0, le=100)
    job_match_score: Optional[int] = Field(None, ge=0, le=100)

    section_analysis: List[SectionAnalysis]

    overall_strengths: List[str]
    overall_weaknesses: List[str]
    missing_information: List[str]

    job_match_analysis: Optional[JobMatchAnalysis] = None
    recommendations: List[Recommendation]


# ---------------------------------------------------------------------------
# Final API response
# ---------------------------------------------------------------------------

class AnalysisResponse(BaseModel):
    """The JSON object the endpoint returns to the client."""
    success: bool
    analysis_mode: str   # "general" | "job_title_only" | "job_description" | "full"

    overall_score: int
    ats_readiness_score: int
    job_match_score: Optional[int] = None

    section_analysis: List[SectionAnalysis]

    overall_strengths: List[str]
    overall_weaknesses: List[str]
    missing_information: List[str]

    job_match_analysis: Optional[JobMatchAnalysis] = None
    recommendations: List[Recommendation]


class ResumeAnalysisResponse(BaseModel):
    id: str
    student_id: str
    job_title: Optional[str] = None
    job_description: Optional[str] = None
    resume_score: Optional[int] = None
    score_breakdown: Optional[dict] = None
    section_analysis: List[SectionAnalysis] = []
    overall_strengths: List[str] = []
    overall_weaknesses: List[str] = []
    missing_information: List[str] = []
    job_match_analysis: Optional[JobMatchAnalysis] = None
    recommendations: List[Recommendation] = []
    prompt_version: Optional[str] = None
    model: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeBuilderSessionResponse(BaseModel):
    id: str
    student_id: str
    job_title: str
    job_description: str
    status: str
    current_section: Optional[str] = None
    answers: List[dict] = []
    drafts: List[dict] = []
    approved_sections: List[dict] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResumeBuilderAnswerRequest(BaseModel):
    section: str
    answer: str


class ResumeBuilderAnswerResponse(BaseModel):
    section: str
    draft: str
    needs_followup: bool
    followup_question: Optional[str] = None