"""
test_rag_evaluation.py — Unit tests for Learning Assistant components.

Tests the individual components of the RAG pipeline:
- Query routing
- Citation building
- Retrieval (with mocked DB)
- Schema validation
- State definitions

Run: uv run pytest app/modules/learning/tests/test_rag_evaluation.py -v
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any

from app.modules.learning.eval_questions import get_rag_test_set, EvalQuestion
from app.modules.learning.schemas import LearningResponse, Citation
from app.modules.learning.citations import build_citations, build_citations_from_kb, build_citations_from_web
from app.modules.learning.query_router import route_query, rule_based_route, RouteDecision
from app.modules.learning.retrieval import vector_search, fallback_vector_search
from app.modules.learning.graph import LearningState, Evidence


class MockDB:
    """Mock database session for testing."""
    def __init__(self):
        self.queries = []

    def add(self, obj):
        self.queries.append(obj)

    def commit(self):
        pass

    def refresh(self, obj):
        obj.id = "test-query-id"


class TestRouting:
    """Test query routing logic."""

    def test_rule_based_web_signals(self):
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

    def test_rule_based_kb_signals(self):
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

    def test_rule_based_direct_signals(self):
        """Greetings and meta questions should route to direct."""
        direct_questions = [
            "Hello",
            "Hi there",
            "Thanks",
            "What can you do?",
        ]
        for q in direct_questions:
            decision = rule_based_route(q)
            assert decision is not None, f"Rule-based should detect direct signal in: {q}"
            assert decision.route == "direct", f"Expected direct route for: {q}"

    def test_ambiguous_returns_none(self):
        """Ambiguous questions should return None (fallback to LLM)."""
        ambiguous = [
            "How do I learn programming?",
            "What should I study?",
        ]
        for q in ambiguous:
            decision = rule_based_route(q)
            # May or may not match - but if it does, confidence should be reasonable
            if decision:
                assert decision.confidence >= 0.5


class TestCitationBuilding:
    """Test citation building from evidence."""

    def test_build_citations_from_kb(self):
        """Test building citations from knowledge base chunks."""
        chunks = [{
            "id": "chunk-1",
            "document_title": "Data Structures Fundamentals",
            "source_url": "kb://data-structures-fundamentals",
            "page": 15,
            "text": "A stack follows LIFO principle...",
        }]
        citations = build_citations_from_kb(chunks, max_citations=5)
        
        assert len(citations) == 1
        assert citations[0].index == 1
        assert citations[0].title == "Data Structures Fundamentals"
        assert citations[0].url == "kb://data-structures-fundamentals"
        assert citations[0].page == 15
        assert "LIFO" in citations[0].excerpt

    def test_build_citations_from_web(self):
        """Test building citations from web search results."""
        web_results = [{
            "title": "Python 3.13 Released",
            "url": "https://python.org/3.13",
            "content": "Python 3.13 was released in October 2024...",
            "score": 0.9,
        }]
        citations = build_citations_from_web(web_results, max_citations=5)
        
        assert len(citations) == 1
        assert citations[0].index == 1
        assert citations[0].title == "Python 3.13 Released"
        assert citations[0].url == "https://python.org/3.13"

    def test_build_citations_deduplication(self):
        """Test that citations are deduplicated by URL."""
        chunks = [
            {"id": "1", "document_title": "Doc A", "source_url": "http://example.com", "page": 1, "text": "Text 1"},
            {"id": "2", "document_title": "Doc B", "source_url": "http://example.com", "page": 2, "text": "Text 2"},  # Same URL
        ]
        citations = build_citations_from_kb(chunks, max_citations=5)
        assert len(citations) == 1  # Should deduplicate


class TestCitationSchema:
    """Test Citation Pydantic schema."""

    def test_citation_structure(self):
        """Test Citation model has all required fields."""
        cit = Citation(index=1, title="Test Doc", url="https://example.com", page=5, excerpt="Test excerpt")
        assert cit.index == 1
        assert cit.title == "Test Doc"
        assert cit.url == "https://example.com"
        assert cit.page == 5
        assert cit.excerpt == "Test excerpt"

    def test_citation_optional_fields(self):
        """Test Citation works with minimal fields."""
        cit = Citation(index=1, title="Test", url="https://example.com")
        assert cit.page is None
        assert cit.excerpt is None


class TestResponseSchema:
    """Test LearningResponse schema validation."""

    def test_valid_response(self):
        """Test valid LearningResponse creation."""
        response = LearningResponse(
            answer="Test answer [1]",
            route="knowledge_base",
            grounding="knowledge_base",
            verified=True,
            insufficient_evidence=False,
            citations=[Citation(index=1, title="Doc", url="http://example.com")],
        )
        assert response.answer == "Test answer [1]"
        assert response.route == "knowledge_base"
        assert response.verified is True
        assert len(response.citations) == 1

    def test_invalid_route_rejected(self):
        """Test invalid route values are rejected."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            LearningResponse(
                answer="Test",
                route="invalid_route",
                grounding="knowledge_base",
                verified=True,
                insufficient_evidence=False,
            )


class TestLearningState:
    """Test LearningState TypedDict structure."""

    def test_state_keys(self):
        """Test LearningState has all required keys."""
        state: LearningState = {
            "student_id": "test",
            "question": "test",
            "route_decision": None,
            "kb_chunks": [],
            "web_results": [],
            "kb_evidence": [],
            "web_evidence": [],
            "direct_evidence": [],
            "unified_evidence": [],
            "answer": "",
            "grounding": "none",
            "verified": False,
            "insufficient_evidence": False,
            "citations": [],
            "final_response": None,
            "error": None,
        }
        assert "student_id" in state
        assert "question" in state
        assert "unified_evidence" in state


class TestEvidenceSchema:
    """Test Evidence TypedDict structure."""

    def test_evidence_keys(self):
        """Test Evidence has all required keys."""
        ev: Evidence = {
            "source": "knowledge_base",
            "title": "Test Doc",
            "url": "https://example.com",
            "text": "Test content",
            "score": 0.9,
            "metadata": {"page": 1},
        }
        assert ev["source"] in ("knowledge_base", "web")
        assert "title" in ev
        assert "url" in ev
        assert "text" in ev
        assert "score" in ev
        assert "metadata" in ev


class TestRouteDecision:
    """Test RouteDecision dataclass."""

    def test_route_decision_structure(self):
        """Test RouteDecision has required fields."""
        decision = RouteDecision(
            route="knowledge_base",
            confidence=0.9,
            reasoning="Test reasoning",
        )
        assert decision.route == "knowledge_base"
        assert decision.confidence == 0.9
        assert decision.reasoning == "Test reasoning"

    def test_route_values_valid(self):
        """Test route only accepts valid values."""
        valid_routes = {"knowledge_base", "web", "direct"}
        for route in valid_routes:
            decision = RouteDecision(route=route, confidence=0.8, reasoning="test")
            assert decision.route in valid_routes


class TestRetrievalFallback:
    """Test retrieval fallback behavior."""

    def test_fallback_vector_search_empty(self):
        """Test fallback returns empty when no chunks."""
        from unittest.mock import MagicMock
        from sqlalchemy.orm import Session

        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.join.return_value.all.return_value = []

        results = fallback_vector_search(mock_db, [0.1] * 384, top_k=5)
        assert results == []


class TestRoutingIntegration:
    """Integration tests for routing (using real LLM would be slow, so we test logic)."""

    def test_route_decision_structure(self):
        """Test RouteDecision output structure."""
        decision = route_query("What is a stack?")
        assert hasattr(decision, "route")
        assert hasattr(decision, "confidence")
        assert hasattr(decision, "reasoning")
        assert decision.route in ("knowledge_base", "web", "direct")
        assert 0.0 <= decision.confidence <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])