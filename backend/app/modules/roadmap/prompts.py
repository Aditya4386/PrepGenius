"""
prompts.py — Prompt templates for roadmap generation.
"""

from typing import Dict, Any


ROLE_TEMPLATE_PROMPT = """You are an expert Career Coach and Technical Curriculum Designer.
Generate a personalized, time-bounded learning roadmap for a student preparing for campus placements.

STUDENT PROFILE:
- Target Role: {target_role}
- Company Type: {company_type}
- Current Skills: {skills}
- Weekly Study Hours: {weekly_hours}
- Planning Weeks: {planning_weeks}
- Preparation Deadline: {prep_deadline}

ROLE TEMPLATE (adjusted for company type):
{role_template}

INSTRUCTIONS:
1. Analyze the student's current skills against the role requirements
2. Identify skill gaps and prioritize them
3. Create a roadmap with 3-5 phases, each containing 3-8 tasks
4. Each task must have: title, estimated_hours (0.5-8), success_criteria, topic_tags
5. Total estimated hours must NOT exceed {weekly_hours} × {planning_weeks} = {max_hours} hours
6. Tasks must be specific, actionable, and ordered logically
7. Consider company type emphasis: {company_emphasis}

OUTPUT FORMAT (JSON):
{{
  "title": "Roadmap Title",
  "target_role": "{target_role}",
  "phases": [
    {{
      "name": "Phase Name",
      "position": 1,
      "description": "Phase description",
      "tasks": [
        {{
          "title": "Specific task title",
          "estimated_hours": 4.0,
          "success_criteria": "Measurable completion criteria",
          "topic_tags": ["topic1", "topic2"],
          "position": 1
        }}
      ]
    }}
  ]
}}

Return ONLY the JSON. No extra text."""


REPAIR_PROMPT = """The previous roadmap had feasibility violations. Please fix them.

VIOLATIONS:
{violations}

CURRENT ROADMAP:
{current_roadmap}

CONSTRAINTS:
- Max total hours: {max_hours}
- Task hours: 0.5-8.0
- Required fields: title, estimated_hours, success_criteria, topic_tags
- Phases and tasks must be sequentially numbered

Return the CORRECTED roadmap in the same JSON format."""


ANALYZE_GAPS_PROMPT = """You are a Skills Gap Analyst for technical roles.

STUDENT PROFILE:
- Target Role: {target_role}
- Company Type: {company_type}
- Current Skills: {skills}
- Education: {education}

ROLE REQUIREMENTS:
{role_requirements}

Analyze the gaps between the student's current skills and the role requirements.
Return a JSON object with:
{{
  "critical_gaps": ["skill1", "skill2"],
  "moderate_gaps": ["skill3", "skill4"],
  "strengths": ["skill5", "skill6"],
  "priority_topics": ["topic1", "topic2", "topic3"]
}}"""