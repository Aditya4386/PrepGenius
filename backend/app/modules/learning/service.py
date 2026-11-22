"""
service.py — Learning Assistant service layer.

Orchestrates the learning subgraph and handles persistence.
"""

import logging
from typing import Optional, List
from sqlalchemy.orm import Session

from app.modules.learning.graph import learning_graph, LearningState
from app.modules.learning.schemas import LearningResponse, LearningQueryResponse
from app.modules.learning.models import LearningQuery
from app.shared.llm import LLMError

logger = logging.getLogger(__name__)


def ask_question(
    db: Session,
    student_id: str,
    question: str,
) -> LearningResponse:
    """
    Process a learning question through the RAG pipeline.

    Args:
        db: Database session
        student_id: Authenticated student ID
        question: Student's question

    Returns:
        LearningResponse with answer, citations, and metadata

    Raises:
        LLMError: If LLM calls fail irrecoverably
        ValueError: If graph execution fails
    """
    initial_state: LearningState = {
        "student_id": student_id,
        "question": question,
        "route_decision": None,
        "kb_chunks": [],
        "web_results": [],
        "unified_evidence": [],
        "answer": "",
        "grounding": "none",
        "verified": False,
        "insufficient_evidence": False,
        "citations": [],
        "final_response": None,
        "error": None,
    }

    logger.info(f"Processing learning question for student {student_id}: {question[:100]}")

    try:
        final_state = learning_graph.invoke(initial_state)
    except LLMError:
        raise
    except Exception as e:
        logger.error(f"Learning graph execution failed: {e}")
        raise LLMError(f"Learning assistant failed: {e}") from e

    # Check for errors
    if final_state.get("error"):
        raise ValueError(final_state["error"])

    final_response = final_state.get("final_response")
    if not final_response:
        raise ValueError("Learning graph completed without producing a response")

    # Persist the learning query
    learning_query = LearningQuery(
        student_id=student_id,
        question=question,
        route=final_response.route,
        grounding=final_response.grounding,
        verified=final_response.verified,
        answer=final_response.answer,
        citations=[c.model_dump() for c in final_response.citations],
    )
    db.add(learning_query)
    db.commit()
    db.refresh(learning_query)

    logger.info(f"Learning query persisted: {learning_query.id}")

    return final_response


def get_learning_history(
    db: Session,
    student_id: str,
    limit: int = 50,
    offset: int = 0,
) -> List[LearningQueryResponse]:
    """Retrieve learning query history for a student."""
    queries = (
        db.query(LearningQuery)
        .filter(LearningQuery.student_id == student_id)
        .order_by(LearningQuery.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return [
        LearningQueryResponse(
            id=q.id,
            student_id=q.student_id,
            question=q.question,
            route=q.route,
            grounding=q.grounding,
            verified=q.verified,
            answer=q.answer,
            citations=q.citations,
            created_at=q.created_at,
        )
        for q in queries
    ]


def get_learning_query(
    db: Session,
    student_id: str,
    query_id: str,
) -> Optional[LearningQueryResponse]:
    """Retrieve a specific learning query by ID."""
    query = (
        db.query(LearningQuery)
        .filter(LearningQuery.student_id == student_id, LearningQuery.id == query_id)
        .first()
    )

    if not query:
        return None

    return LearningQueryResponse(
        id=query.id,
        student_id=query.student_id,
        question=query.question,
        route=query.route,
        grounding=query.grounding,
        verified=query.verified,
        answer=query.answer,
        citations=query.citations,
        created_at=query.created_at,
    )