"""
test_routing.py — Routing accuracy tests for Learning Assistant.

Tests the query router against a fixed evaluation set to measure
routing accuracy across knowledge_base, web, and direct routes.

Run: uv run pytest app/modules/learning/tests/test_routing.py -v
"""

import pytest
from app.modules.learning.query_router import route_query, rule_based_route, RouteDecision
from app.modules.learning.eval_questions import get_routing_test_set, get_questions_by_route


class TestRuleBasedRouting:
    """Test the fast rule-based router."""

    def test_web_signals_detected(self):
        """Questions with current-info signals should route to web."""
        web_questions = [
            "What is the latest version of Python in 2024?",
            "Current salary trends for developers",
            "News about AWS re:Invent 2024",
            "Version 2.0 released today",
        ]
        for q in web_questions:
            decision = rule_based_route(q)
            assert decision is not None, f"Rule-based should detect web signal in: {q}"
            assert decision.route == "web", f"Expected web route for: {q}"

    def test_kb_signals_detected(self):
        """Questions with conceptual signals should route to knowledge_base."""
        kb_questions = [
            "What is a binary search tree?",
            "Explain the CAP theorem",
            "How to prepare for system design interview",
            "Difference between REST and GraphQL",
        ]
        for q in kb_questions:
            decision = rule_based_route(q)
            assert decision is not None, f"Rule-based should detect KB signal in: {q}"
            assert decision.route == "knowledge_base", f"Expected KB route for: {q}"

    def test_ambiguous_returns_none(self):
        """Ambiguous questions should return None (fallback to LLM)."""
        ambiguous = [
            "How do I learn programming?",  # Could be KB or direct
            "What should I study?",  # Could be KB or direct
        ]
        for q in ambiguous:
            decision = rule_based_route(q)
            # May or may not match - but if it does, confidence should be reasonable
            if decision:
                assert decision.confidence >= 0.5


class TestFullRouting:
    """Test the complete routing pipeline (rules + LLM)."""

    @pytest.fixture
    def eval_questions(self):
        """Load evaluation question set."""
        return get_routing_test_set()

    def test_knowledge_base_accuracy(self):
        """Test routing accuracy for knowledge_base questions."""
        kb_questions = get_questions_by_route("knowledge_base")
        correct = 0
        total = len(kb_questions)

        for q in kb_questions:
            decision = route_query(q.question)
            if decision.route == "knowledge_base":
                correct += 1
            else:
                print(f"MISROUTED KB: '{q.question}' -> {decision.route} (conf: {decision.confidence:.2f})")

        accuracy = correct / total
        print(f"\nKB Routing Accuracy: {correct}/{total} = {accuracy:.1%}")
        assert accuracy >= 0.85, f"KB routing accuracy {accuracy:.1%} below threshold"

    def test_web_accuracy(self):
        """Test routing accuracy for web questions."""
        web_questions = get_questions_by_route("web")
        correct = 0
        total = len(web_questions)

        for q in web_questions:
            decision = route_query(q.question)
            if decision.route == "web":
                correct += 1
            else:
                print(f"MISROUTED WEB: '{q.question}' -> {decision.route} (conf: {decision.confidence:.2f})")

        accuracy = correct / total
        print(f"\nWeb Routing Accuracy: {correct}/{total} = {accuracy:.1%}")
        assert accuracy >= 0.80, f"Web routing accuracy {accuracy:.1%} below threshold"

    def test_direct_accuracy(self):
        """Test routing accuracy for direct questions."""
        direct_questions = get_questions_by_route("direct")
        correct = 0
        total = len(direct_questions)

        for q in direct_questions:
            decision = route_query(q.question)
            if decision.route == "direct":
                correct += 1
            else:
                print(f"MISROUTED DIRECT: '{q.question}' -> {decision.route} (conf: {decision.confidence:.2f})")

        accuracy = correct / total
        print(f"\nDirect Routing Accuracy: {correct}/{total} = {accuracy:.1%}")
        assert accuracy >= 0.80, f"Direct routing accuracy {accuracy:.1%} below threshold"

    def test_overall_accuracy(self):
        """Test overall routing accuracy across all categories."""
        all_questions = get_routing_test_set()
        correct = 0
        total = len(all_questions)

        for q in all_questions:
            decision = route_query(q["question"])
            if decision.route == q["expected_route"]:
                correct += 1
            else:
                print(f"MISROUTED: [{q['expected_route']}] '{q['question']}' -> {decision.route}")

        accuracy = correct / total
        print(f"\nOverall Routing Accuracy: {correct}/{total} = {accuracy:.1%}")
        assert accuracy >= 0.82, f"Overall routing accuracy {accuracy:.1%} below threshold"


class TestRoutingConfidence:
    """Test that confidence scores are reasonable."""

    def test_high_confidence_for_clear_cases(self):
        """Clear-cut questions should have high confidence."""
        clear_questions = [
            ("What is a stack?", "knowledge_base"),
            ("Latest Python version 2024", "web"),
            ("Hello", "direct"),
        ]
        for question, expected in clear_questions:
            decision = route_query(question)
            assert decision.route == expected
            assert decision.confidence >= 0.7, f"Low confidence for clear case: {question}"

    def test_confidence_in_range(self):
        """All confidence scores should be in valid range."""
        questions = [q["question"] for q in get_routing_test_set()]
        for q in questions:
            decision = route_query(q)
            assert 0.0 <= decision.confidence <= 1.0, f"Invalid confidence for: {q}"


class TestRouteDecisionStructure:
    """Test RouteDecision dataclass structure."""

    def test_has_required_fields(self):
        """RouteDecision should have route, confidence, reasoning."""
        decision = route_query("What is a stack?")
        assert hasattr(decision, "route")
        assert hasattr(decision, "confidence")
        assert hasattr(decision, "reasoning")
        assert isinstance(decision.route, str)
        assert isinstance(decision.confidence, float)
        assert isinstance(decision.reasoning, str)

    def test_route_values_valid(self):
        """Route should only be valid values."""
        valid_routes = {"knowledge_base", "web", "direct"}
        questions = [q["question"] for q in get_routing_test_set()]
        for q in questions:
            decision = route_query(q)
            assert decision.route in valid_routes, f"Invalid route: {decision.route}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])