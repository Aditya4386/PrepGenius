"""
query_router.py — Query routing for learning assistant.

Routes questions to knowledge_base, web search, or direct answering
based on question type and content signals.
"""

import re
import json
import logging
from typing import Literal, Optional
from dataclasses import dataclass

from app.shared.llm import get_llm_for_task, LLMTask
from app.core.config import settings

logger = logging.getLogger(__name__)

RouteType = Literal["knowledge_base", "web", "direct"]


@dataclass
class RouteDecision:
    route: RouteType
    confidence: float
    reasoning: str


# Rule-based signals for web search
WEB_SIGNALS = [
    r"\b(latest|recent|current|today|this year|this month)\b",
    r"\b(news|announced|released|launched|updated)\b",
    r"\b(salary|compensation|pay scale|hiring trends)\b",
    r"\b(202\d|2025|2026)\b",
    r"\b(version|release|v\d+\.\d+)\b",
    r"\b(how much|what is the cost|pricing)\b",
]

# Rule-based signals for direct answers (greetings, meta)
DIRECT_SIGNALS = [
    r"^\s*(hi|hello|hey|thanks|thank you)\b",
    r"\b(what can you do|what do you do|how can you help)\b",
    r"^\s*(bye|goodbye|see you)\b",
]

KB_SIGNALS = [
    r"\b(what is|how does|explain|define|concept)\b",
    r"\b(algorithm|data structure|design pattern|architecture)\b",
    r"\b(interview|question|answer|prepare)\b",
    r"\b(tutorial|guide|learn|study|roadmap)\b",
    r"\b(rest|graphql|api|endpoint|http)\b",
    r"\b(database|sql|nosql|transaction|acid)\b",
    r"\b(garbage collection|memory management|runtime)\b",
    r"\b(dependency injection|inversion of control|di\b)\b",
    r"\b(cap theorem|distributed system|consistency|availability)\b",
    r"\b(binary search|time complexity|big o|algorithm)\b",
    r"\b(system design|scalability|load balancing|caching)\b",
    r"\b(design pattern|solid|clean code|refactor)\b",
]


def rule_based_route(question: str) -> Optional[RouteDecision]:
    """
    Fast rule-based routing for clear-cut cases.

    Returns None if rules are ambiguous.
    """
    question_lower = question.lower()

    # Check for direct signals first (greetings, meta)
    for pattern in DIRECT_SIGNALS:
        if re.search(pattern, question_lower):
            return RouteDecision(
                route="direct",
                confidence=0.95,
                reasoning=f"Matched direct signal pattern: {pattern}",
            )

    # Check for current-information signals -> web
    for pattern in WEB_SIGNALS:
        if re.search(pattern, question_lower):
            return RouteDecision(
                route="web",
                confidence=0.85,
                reasoning=f"Matched web signal pattern: {pattern}",
            )

    # Check for knowledge-base signals -> knowledge_base
    for pattern in KB_SIGNALS:
        if re.search(pattern, question_lower):
            return RouteDecision(
                route="knowledge_base",
                confidence=0.8,
                reasoning=f"Matched KB signal pattern: {pattern}",
            )

    return None


def llm_classify_route(question: str) -> RouteDecision:
    """
    Use LLM to classify ambiguous questions.

    Falls back to knowledge_base if LLM fails.
    """
    try:
        llm = get_llm_for_task(LLMTask.LEARNING_QUERY_ROUTING)

        prompt = f"""Classify this student question into one of three routes:

QUESTION: {question}

ROUTES:
1. knowledge_base - Factual, conceptual, or educational questions answerable from curated CS/tech learning resources (algorithms, system design, interview prep, programming concepts)
2. web - Questions requiring current information: latest news, recent releases, salary trends, hiring data, version-specific features, pricing
3. direct - Simple conversational questions, greetings, or meta-questions not needing external knowledge

Return ONLY a JSON object:
{{
  "route": "knowledge_base|web|direct",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}}"""

        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        # Extract JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        result = json.loads(content.strip())
        route = result.get("route", "knowledge_base")
        confidence = float(result.get("confidence", 0.7))
        reasoning = result.get("reasoning", "LLM classification")

        if route not in ("knowledge_base", "web", "direct"):
            route = "knowledge_base"

        return RouteDecision(route=route, confidence=confidence, reasoning=reasoning)

    except Exception as e:
        logger.warning(f"LLM routing failed, defaulting to knowledge_base: {e}")
        return RouteDecision(
            route="knowledge_base",
            confidence=0.5,
            reasoning="LLM classification failed, defaulting to knowledge_base",
        )


def route_query(question: str) -> RouteDecision:
    """
    Main routing function: rule-based first, then LLM for ambiguous cases.

    Returns RouteDecision with route, confidence, and reasoning.
    """
    # Rule-based fast path
    rule_decision = rule_based_route(question)
    if rule_decision and rule_decision.confidence >= 0.8:
        return rule_decision

    # LLM classification for ambiguous cases
    llm_decision = llm_classify_route(question)

    # If rule-based gave a weak signal, combine with LLM
    if rule_decision:
        # Weighted combination
        if rule_decision.route == llm_decision.route:
            return RouteDecision(
                route=llm_decision.route,
                confidence=min(0.95, (rule_decision.confidence + llm_decision.confidence) / 2 + 0.1),
                reasoning=f"Rule + LLM agreement: {rule_decision.reasoning}; {llm_decision.reasoning}",
            )
        else:
            # Disagreement - trust LLM more for nuanced cases
            return RouteDecision(
                route=llm_decision.route,
                confidence=llm_decision.confidence * 0.9,
                reasoning=f"Rule/LLM disagreement. LLM: {llm_decision.reasoning}. Rule: {rule_decision.reasoning}",
            )

    return llm_decision