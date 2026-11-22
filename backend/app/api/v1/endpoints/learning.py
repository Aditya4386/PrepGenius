"""
learning.py — API routes for Learning Assistant (RAG + Web Search).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_student_id
from app.db.session import get_db
from app.modules.learning.schemas import (
    LearningAskRequest,
    LearningResponse,
    LearningHistoryResponse,
    LearningQueryResponse,
)
from app.modules.learning.service import (
    ask_question,
    get_learning_history,
    get_learning_query,
)

router = APIRouter(prefix="/learning", tags=["Learning Assistant"])


@router.post(
    "/ask",
    response_model=LearningResponse,
    summary="Ask the learning assistant",
    description=(
        "Submit a question to the Verified Learning Assistant. "
        "Routes to knowledge base, web search, or direct answer. "
        "Returns grounded answer with citations."
    ),
)
def ask_learning_question(
    request: LearningAskRequest,
    student_id: str = Depends(get_current_student_id),
    db: Session = Depends(get_db),
):
    try:
        return ask_question(db, student_id, request.question)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log the actual error for debugging
        import logging
        logging.getLogger(__name__).error(f"Learning ask failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="The learning assistant is temporarily unavailable. Please try again later.",
        )


@router.get(
    "/history",
    response_model=LearningHistoryResponse,
    summary="Get learning question history",
    description="Retrieve past questions and answers for the authenticated student.",
)
def get_learning_history_endpoint(
    limit: int = 50,
    offset: int = 0,
    student_id: str = Depends(get_current_student_id),
    db: Session = Depends(get_db),
):
    queries = get_learning_history(db, student_id, limit, offset)
    return {"queries": queries, "total": len(queries)}


@router.get(
    "/history/{query_id}",
    response_model=LearningQueryResponse,
    summary="Get a specific learning query",
    description="Retrieve a specific learning question and answer by ID.",
)
def get_learning_query_endpoint(
    query_id: str,
    student_id: str = Depends(get_current_student_id),
    db: Session = Depends(get_db),
):
    query = get_learning_query(db, student_id, query_id)
    if not query:
        raise HTTPException(status_code=404, detail="Learning query not found")
    return query