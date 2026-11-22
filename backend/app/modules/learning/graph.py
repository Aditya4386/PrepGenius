"""
graph.py — LangGraph subgraph for Verified Learning Assistant (RAG).

Implements the learning subgraph from docs/PrepGenius_Roadmap_v2.md §13.2:

validate_question -> route_query -> retrieve_chunks / tavily_search / direct
    -> normalize_evidence -> dedupe_and_rank -> assemble_context
    -> generate_answer -> build_citations -> END

Each node is a single turn; state persisted in learning_queries table.
"""

import json
import logging
from typing import Dict, Any, List, Optional, TypedDict, Literal, Annotated
from dataclasses import dataclass
from operator import add

from langgraph.graph import StateGraph, START, END

from app.modules.learning.query_router import route_query, RouteDecision
from app.modules.learning.retrieval import retrieve_for_question
from app.modules.learning.web_search import search_web_with_fallback, format_web_results_for_context, build_web_citations
from app.modules.learning.citations import build_citations, format_citations_for_display
from app.shared.llm import get_llm_for_task, LLMTask, LLMError
from app.core.config import settings

logger = logging.getLogger(__name__)


# --- State Definition ---

class Evidence(TypedDict):
    """Unified evidence schema for all routes."""
    source: Literal["knowledge_base", "web"]
    title: str
    url: str
    text: str
    score: float
    metadata: Dict[str, Any]


class KB_Evidence(TypedDict):
    """Knowledge base evidence."""
    source: Literal["knowledge_base"]
    title: str
    url: str
    text: str
    score: float
    metadata: Dict[str, Any]


class Web_Evidence(TypedDict):
    """Web search evidence."""
    source: Literal["web"]
    title: str
    url: str
    text: str
    score: float
    metadata: Dict[str, Any]


class LearningState(TypedDict):
    student_id: str
    question: str

    # Routing
    route_decision: Optional[RouteDecision]

    # Evidence (separate keys to avoid concurrent updates)
    kb_chunks: List[Dict[str, Any]]
    web_results: List[Dict[str, Any]]
    kb_evidence: List[Evidence]
    web_evidence: List[Evidence]
    direct_evidence: List[Evidence]
    unified_evidence: List[Evidence]

    # Answer generation
    answer: str
    grounding: Literal["knowledge_base", "web", "none"]
    verified: bool
    insufficient_evidence: bool
    citations: List[Dict[str, Any]]

    # Final response
    final_response: Optional[Dict[str, Any]]

    # Error handling
    error: Optional[str]


# --- Node Functions ---

def validate_question(state: LearningState) -> Dict[str, Any]:
    """Validate and sanitize the input question."""
    question = state["question"].strip()

    if not question:
        return {"error": "Question cannot be empty"}

    if len(question) > 2000:
        return {"error": "Question too long (max 2000 characters)"}

    return {"question": question}


def route_query_node(state: LearningState) -> Dict[str, Any]:
    """Route the question to knowledge_base, web, or direct."""
    decision = route_query(state["question"])
    logger.info(f"Query routed to: {decision.route} (confidence: {decision.confidence:.2f}) - {decision.reasoning}")
    return {"route_decision": decision}


def retrieve_chunks_node(state: LearningState) -> Dict[str, Any]:
    """Retrieve relevant chunks from knowledge base."""
    from app.db.session import SessionLocal

    question = state["question"]
    db = SessionLocal()
    try:
        chunks = retrieve_for_question(
            db,
            question,
            top_k=settings.KB_TOP_K if hasattr(settings, 'KB_TOP_K') else 5,
            distance_threshold=settings.KB_DISTANCE_THRESHOLD if hasattr(settings, 'KB_DISTANCE_THRESHOLD') else 0.7,
        )
        return {"kb_chunks": chunks}
    finally:
        db.close()


def tavily_search_node(state: LearningState) -> Dict[str, Any]:
    """Search the web using Tavily."""
    question = state["question"]
    results = search_web_with_fallback(question, max_results=5)

    web_results = []
    for r in results:
        web_results.append({
            "title": r.title,
            "url": r.url,
            "content": r.content,
            "score": r.score,
        })

    return {"web_results": web_results}


def direct_answer_node(state: LearningState) -> Dict[str, Any]:
    """Handle direct answer (no external evidence needed)."""
    return {
        "kb_chunks": [],
        "web_results": [],
        "kb_evidence": [],
        "web_evidence": [],
        "direct_evidence": [],
    }


def should_retrieve_kb(state: LearningState) -> str:
    """Conditional edge: route to KB retrieval."""
    route = state["route_decision"].route if state.get("route_decision") else "knowledge_base"
    if route == "knowledge_base":
        return "retrieve_chunks"
    return "skip_kb"


def should_search_web(state: LearningState) -> str:
    """Conditional edge: route to web search."""
    route = state["route_decision"].route if state.get("route_decision") else "knowledge_base"
    if route == "web":
        return "tavily_search"
    return "skip_web"


def normalize_kb_evidence(state: LearningState) -> Dict[str, Any]:
    """Normalize KB chunks into evidence format."""
    kb_evidence = []
    for chunk in state.get("kb_chunks", []):
        kb_evidence.append(Evidence(
            source="knowledge_base",
            title=chunk.get("document_title", "KB Source"),
            url=chunk.get("source_url", f"kb://{chunk.get('id', 'unknown')}"),
            text=chunk.get("text", ""),
            score=chunk.get("similarity", 0.0),
            metadata={
                "chunk_id": chunk.get("id"),
                "page": chunk.get("page"),
                "document_title": chunk.get("document_title"),
            }
        ))
    return {"kb_evidence": kb_evidence}


def normalize_web_evidence(state: LearningState) -> Dict[str, Any]:
    """Normalize web results into evidence format."""
    web_evidence = []
    for result in state.get("web_results", []):
        web_evidence.append(Evidence(
            source="web",
            title=result.get("title", "Web Source"),
            url=result.get("url", ""),
            text=result.get("content", ""),
            score=result.get("score", 0.0),
            metadata={}
        ))
    return {"web_evidence": web_evidence}


def merge_evidence(state: LearningState) -> Dict[str, Any]:
    """Merge all evidence sources and deduplicate."""
    unified = []
    seen_urls = set()

    # KB evidence
    for ev in state.get("kb_evidence", []):
        url = ev["url"]
        if url not in seen_urls:
            seen_urls.add(url)
            unified.append(ev)

    # Web evidence
    for ev in state.get("web_evidence", []):
        url = ev["url"]
        if url not in seen_urls:
            seen_urls.add(url)
            unified.append(ev)

    # Direct evidence (rarely used)
    for ev in state.get("direct_evidence", []):
        url = ev["url"]
        if url not in seen_urls:
            seen_urls.add(url)
            unified.append(ev)

    # Sort by score descending
    unified.sort(key=lambda x: x["score"], reverse=True)

    return {"unified_evidence": unified}


def dedupe_and_rank(state: LearningState) -> Dict[str, Any]:
    """Deduplicate by URL and rank by score."""
    seen_urls = set()
    deduped = []

    for ev in state.get("unified_evidence", []):
        url = ev["url"]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(ev)

    # Sort by score descending
    deduped.sort(key=lambda x: x["score"], reverse=True)

    return {"unified_evidence": deduped}


def assemble_context(state: LearningState) -> Dict[str, Any]:
    """Assemble context within token budget."""
    evidence = state.get("unified_evidence", [])

    # Token budget: reserve ~2000 tokens for answer, ~1000 for prompt
    max_context_tokens = getattr(settings, 'MAX_CONTEXT_TOKENS', 3000)

    context_parts = []
    total_tokens = 0

    for i, ev in enumerate(evidence):
        # Rough token estimation: 1 token ≈ 4 chars
        ev_text = f"[{i+1}] {ev['title']}\n{ev['text']}\n"
        ev_tokens = len(ev_text) // 4

        if total_tokens + ev_tokens > max_context_tokens:
            break

        context_parts.append(ev_text)
        total_tokens += ev_tokens

    context = "\n---\n".join(context_parts) if context_parts else "No relevant evidence found."

    return {"context": context, "evidence_count": len(context_parts)}


def generate_answer(state: LearningState) -> Dict[str, Any]:
    """Generate answer from assembled context using LLM."""
    if state.get("error"):
        return {}

    question = state["question"]
    context = state.get("context", "")
    route = state["route_decision"].route if state.get("route_decision") else "knowledge_base"
    evidence_count = state.get("evidence_count", 0)

    if evidence_count == 0 and route != "direct":
        # Insufficient evidence
        return handle_insufficient_evidence(state)

    llm = get_llm_for_task(LLMTask.LEARNING_ANSWER_GENERATION)

    prompt = f"""You are a Verified Learning Assistant for career readiness.
Answer the student's question using ONLY the provided evidence.
If the evidence doesn't fully answer the question, say so explicitly.

EVIDENCE:
{context}

QUESTION: {question}

INSTRUCTIONS:
1. Answer based ONLY on the evidence above
2. Cite evidence by number like [1], [2] inline
3. If evidence is insufficient, state: "Insufficient evidence to answer fully"
4. Be concise but thorough
5. Do not use external knowledge

ANSWER:"""

    try:
        response = llm.invoke(prompt)
        answer = response.content if hasattr(response, "content") else str(response)

        # Determine grounding
        if route == "knowledge_base" and evidence_count > 0:
            grounding = "knowledge_base"
            verified = True
        elif route == "web" and evidence_count > 0:
            grounding = "web"
            verified = False  # Web sources not verified
        else:
            grounding = "none"
            verified = False

        return {
            "answer": answer.strip(),
            "grounding": grounding,
            "verified": verified,
            "insufficient_evidence": False,
        }

    except Exception as e:
        logger.error(f"Answer generation failed: {e}")
        raise LLMError(f"Answer generation failed: {e}") from e


def handle_insufficient_evidence(state: LearningState) -> Dict[str, Any]:
    """Handle case where no relevant evidence was found."""
    llm = get_llm_for_task(LLMTask.LEARNING_INSUFFICIENT_EVIDENCE)

    prompt = f"""The student asked: "{state['question']}"

No relevant evidence was found in the knowledge base or web search.

Generate a helpful response that:
1. Acknowledges the limitation
2. Suggests alternative approaches (rephrase, break down question, try different terms)
3. Does NOT make up an answer

Keep it brief and encouraging."""

    try:
        response = llm.invoke(prompt)
        answer = response.content if hasattr(response, "content") else str(response)
    except Exception:
        answer = ("I couldn't find reliable evidence to answer your question. "
                  "Try rephrasing or breaking it into smaller parts, "
                  "or ask about a specific concept you'd like to learn.")

    return {
        "answer": answer,
        "grounding": "none",
        "verified": False,
        "insufficient_evidence": True,
    }


def build_citations_node(state: LearningState) -> Dict[str, Any]:
    """Build citations from actual retrieved evidence."""
    route = state["route_decision"].route if state.get("route_decision") else "knowledge_base"
    kb_chunks = state.get("kb_chunks", [])
    web_results = state.get("web_results", [])

    citations = build_citations(
        route=route,
        kb_chunks=kb_chunks,
        web_results=web_results,
        max_citations=5,
    )

    return {"citations": citations}


def finalize_response(state: LearningState) -> Dict[str, Any]:
    """Build final response object."""
    from app.modules.learning.schemas import LearningResponse

    response = LearningResponse(
        answer=state.get("answer", ""),
        route=state["route_decision"].route if state.get("route_decision") else "knowledge_base",
        grounding=state.get("grounding", "none"),
        verified=state.get("verified", False),
        insufficient_evidence=state.get("insufficient_evidence", False),
        citations=state.get("citations", []),
    )

    return {"final_response": response}


# --- Graph Construction ---

def create_learning_graph():
    """Build and compile the learning assistant subgraph."""
    workflow = StateGraph(LearningState)

    # Nodes
    workflow.add_node("validate_question", validate_question)
    workflow.add_node("route_query", route_query_node)
    workflow.add_node("retrieve_chunks", retrieve_chunks_node)
    workflow.add_node("tavily_search", tavily_search_node)
    workflow.add_node("direct_answer", direct_answer_node)
    workflow.add_node("normalize_kb_evidence", normalize_kb_evidence)
    workflow.add_node("normalize_web_evidence", normalize_web_evidence)
    workflow.add_node("merge_evidence", merge_evidence)
    workflow.add_node("assemble_context", assemble_context)
    workflow.add_node("generate_answer", generate_answer)
    workflow.add_node("build_citations", build_citations_node)
    workflow.add_node("finalize_response", finalize_response)

    # Edges
    workflow.add_edge(START, "validate_question")
    workflow.add_edge("validate_question", "route_query")

    # Conditional routing from route_query
    workflow.add_conditional_edges(
        "route_query",
        should_retrieve_kb,
        {"retrieve_chunks": "retrieve_chunks", "skip_kb": "normalize_kb_evidence"},
    )
    workflow.add_conditional_edges(
        "route_query",
        should_search_web,
        {"tavily_search": "tavily_search", "skip_web": "normalize_web_evidence"},
    )

    # Parallel retrieval paths -> normalize -> merge
    workflow.add_edge("retrieve_chunks", "normalize_kb_evidence")
    workflow.add_edge("tavily_search", "normalize_web_evidence")
    workflow.add_edge("direct_answer", "merge_evidence")

    # Normalize -> merge
    workflow.add_edge("normalize_kb_evidence", "merge_evidence")
    workflow.add_edge("normalize_web_evidence", "merge_evidence")

    # Merge -> assemble -> generate -> citations -> finalize
    workflow.add_edge("merge_evidence", "assemble_context")
    workflow.add_edge("assemble_context", "generate_answer")
    workflow.add_edge("generate_answer", "build_citations")
    workflow.add_edge("build_citations", "finalize_response")
    workflow.add_edge("finalize_response", END)

    return workflow.compile()


learning_graph = create_learning_graph()