"""
state.py — State definitions for resume builder subgraph.
"""

from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime


class BuilderState(TypedDict):
    session_id: str
    student_id: str
    job_title: str
    job_description: str
    status: str
    current_section: Optional[str]
    section_index: int
    answers: List[Dict[str, Any]]
    drafts: List[Dict[str, Any]]
    approved_sections: List[Dict[str, Any]]
    job_keywords: List[str]
    followup_counts: Dict[str, int]  # per-section follow-up count
    max_followups: int
    error: Optional[str]
    jd_parsed: bool  # Track if JD has been parsed