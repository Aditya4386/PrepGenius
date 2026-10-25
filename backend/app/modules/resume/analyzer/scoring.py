"""
ats_scorer.py — Deterministic ATS (Applicant Tracking System) checks.

This module does NOT call an LLM. It runs simple, rule-based checks on the
raw resume text to produce an objective ATS readiness score.

Why separate from LLM? These checks are fast, cheap, consistent, and
testable without any external API. LLM handles qualitative judgments;
this module handles structural facts.

Scoring criteria (100 points total):
  - Contact info present          : 20 pts
  - Has measurable achievements   : 15 pts
  - No tables or columns detected : 10 pts  (tables confuse ATS parsers)
  - Reasonable length             : 10 pts  (200-1500 words is ideal)
  - Standard section headings     : 20 pts  (up to 4 recognized headings)
  - Action verbs present          : 15 pts
  - No special characters overuse : 10 pts
"""

import re

KNOWN_HEADINGS = [
    "education", "experience", "skills", "projects", "certifications",
    "summary", "objective", "internship", "achievements", "work experience",
    "technical skills", "publications", "volunteer",
]

ACTION_VERBS = [
    "developed", "built", "designed", "implemented", "created", "managed",
    "led", "improved", "optimized", "analyzed", "researched", "collaborated",
    "automated", "deployed", "tested", "maintained", "contributed", "reduced",
    "increased", "delivered", "launched", "architected", "engineered",
]

ACHIEVEMENT_PATTERNS = [
    r"\d+%",
    r"\$\d+",
    r"\d+\+?\s*(users|clients|students|people|projects|hours|days|months)",
]


def compute_ats_score(resume_text: str) -> tuple[int, list[str]]:
    """
    Run deterministic ATS checks on the resume text.

    Returns:
        (score, observations) — score is 0-100, observations are human-readable notes.
    """
    text_lower = resume_text.lower()
    words = resume_text.split()
    word_count = len(words)

    score = 0
    observations = []

    has_email = bool(re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", resume_text))
    has_phone = bool(re.search(r"[\+\(]?[\d\s\-\(\)]{7,15}", resume_text))
    has_linkedin = "linkedin" in text_lower
    has_github = "github" in text_lower

    contact_pts = 0
    if has_email:
        contact_pts += 10
    if has_phone:
        contact_pts += 6
    if has_linkedin or has_github:
        contact_pts += 4

    score += contact_pts
    if not has_email:
        observations.append("Email address not found — ATS systems require it.")
    if not has_phone:
        observations.append("Phone number not detected.")
    if not has_linkedin and not has_github:
        observations.append("No LinkedIn or GitHub URL found; add at least one for tech roles.")

    headings_found = [h for h in KNOWN_HEADINGS if h in text_lower]
    heading_pts = min(len(headings_found), 4) * 5
    score += heading_pts
    if len(headings_found) < 3:
        observations.append(
            f"Only {len(headings_found)} standard heading(s) detected. "
            "Use recognizable labels like Education, Skills, Experience, Projects."
        )

    has_achievement = any(re.search(p, resume_text, re.IGNORECASE) for p in ACHIEVEMENT_PATTERNS)
    if has_achievement:
        score += 15
    else:
        observations.append(
            "No quantifiable achievements found (e.g. 'improved performance by 30%'). "
            "Adding metrics makes your resume stand out."
        )

    if 200 <= word_count <= 1500:
        score += 10
    elif word_count < 200:
        observations.append(f"Resume is very short ({word_count} words). Aim for at least 300 words.")
    else:
        observations.append(f"Resume is very long ({word_count} words). Consider trimming to under 1500 words.")

    verbs_found = [v for v in ACTION_VERBS if v in text_lower]
    if len(verbs_found) >= 5:
        score += 15
    elif len(verbs_found) >= 2:
        score += 8
        observations.append("Use more strong action verbs (e.g. built, optimized, deployed).")
    else:
        observations.append("Very few action verbs found. Use them to describe your accomplishments.")

    tab_count = resume_text.count("\t")
    pipe_count = resume_text.count("|")
    if tab_count < 10 and pipe_count < 5:
        score += 10
    else:
        observations.append(
            "Heavy table or column formatting detected. "
            "ATS parsers often misread resumes with complex layouts."
        )

    special_char_count = len(re.findall(r"[★✓●•✗→←]", resume_text))
    if special_char_count <= 20:
        score += 10
    else:
        observations.append(
            "Excessive special characters (icons, symbols) detected. "
            "Stick to plain bullet points for better ATS compatibility."
        )

    final_score = min(score, 100)

    if not observations:
        observations.append("Your resume passes all basic ATS readability checks.")

    return final_score, observations