"""
eval_questions.py — Evaluation question set for RAG and routing.

Fixed question set with known supporting sources for measuring:
- Retrieval relevance (contextual relevancy and recall)
- Answer faithfulness to retrieved evidence
- Citation correctness
- Abstention when evidence is insufficient
- Routing accuracy (knowledge_base vs web vs direct)
"""

from typing import List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class EvalQuestion:
    """A single evaluation question with expected behavior."""
    id: str
    question: str
    expected_route: str  # knowledge_base, web, direct
    category: str  # For grouping: concept, current_info, interview_prep, salary, etc.
    # Known supporting sources (title, url) that should be retrieved
    expected_sources: List[Dict[str, str]] = field(default_factory=list)
    # Keywords that must appear in a good answer
    required_keywords: List[str] = field(default_factory=list)
    # Answer should NOT contain these (hallucination check)
    forbidden_keywords: List[str] = field(default_factory=list)
    # Minimum acceptable citation count
    min_citations: int = 1
    # Whether the question expects insufficient evidence behavior
    expects_insufficient_evidence: bool = False


# --- Evaluation Question Set ---

EVAL_QUESTIONS: List[EvalQuestion] = [
    # ===== KNOWLEDGE BASE ROUTE =====

    EvalQuestion(
        id="kb_001",
        question="What is the difference between a stack and a queue?",
        expected_route="knowledge_base",
        category="data_structures",
        expected_sources=[
            {"title": "Data Structures Fundamentals", "url": "kb://data-structures-fundamentals"},
        ],
        required_keywords=["LIFO", "FIFO", "push", "pop", "enqueue", "dequeue"],
        forbidden_keywords=[],
    ),

    EvalQuestion(
        id="kb_002",
        question="Explain the CAP theorem in distributed systems.",
        expected_route="knowledge_base",
        category="system_design",
        expected_sources=[
            {"title": "Distributed Systems Concepts", "url": "kb://distributed-systems-concepts"},
        ],
        required_keywords=["consistency", "availability", "partition tolerance", "trade-off"],
        forbidden_keywords=[],
    ),

    EvalQuestion(
        id="kb_003",
        question="How does garbage collection work in Python?",
        expected_route="knowledge_base",
        category="programming_concepts",
        expected_sources=[
            {"title": "Python Internals", "url": "kb://python-internals"},
        ],
        required_keywords=["reference counting", "generation", "gc module", "circular reference"],
        forbidden_keywords=[],
    ),

    EvalQuestion(
        id="kb_004",
        question="What are the ACID properties of database transactions?",
        expected_route="knowledge_base",
        category="database",
        expected_sources=[
            {"title": "Database Systems", "url": "kb://database-systems"},
        ],
        required_keywords=["atomicity", "consistency", "isolation", "durability"],
        forbidden_keywords=[],
    ),

    EvalQuestion(
        id="kb_005",
        question="Explain the difference between REST and GraphQL.",
        expected_route="knowledge_base",
        category="api_design",
        expected_sources=[
            {"title": "API Design Patterns", "url": "kb://api-design-patterns"},
        ],
        required_keywords=["endpoint", "over-fetching", "under-fetching", "schema", "query"],
        forbidden_keywords=[],
    ),

    EvalQuestion(
        id="kb_006",
        question="What is the time complexity of binary search?",
        expected_route="knowledge_base",
        category="algorithms",
        expected_sources=[
            {"title": "Algorithms and Complexity", "url": "kb://algorithms-complexity"},
        ],
        required_keywords=["O(log n)", "logarithmic", "divide and conquer", "sorted"],
        forbidden_keywords=[],
    ),

    EvalQuestion(
        id="kb_007",
        question="How do you prepare for a system design interview?",
        expected_route="knowledge_base",
        category="interview_prep",
        expected_sources=[
            {"title": "System Design Interview Guide", "url": "kb://system-design-interview"},
        ],
        required_keywords=["requirements", "scale", "api", "database", "cache", "trade-offs"],
        forbidden_keywords=[],
    ),

    EvalQuestion(
        id="kb_008",
        question="What is dependency injection and why is it useful?",
        expected_route="knowledge_base",
        category="software_engineering",
        expected_sources=[
            {"title": "Design Patterns", "url": "kb://design-patterns"},
        ],
        required_keywords=["inversion of control", "testability", "decoupling", "container"],
        forbidden_keywords=[],
    ),

    # ===== WEB SEARCH ROUTE (Current Information) =====

    EvalQuestion(
        id="web_001",
        question="What is the latest version of Python released in 2024?",
        expected_route="web",
        category="current_version",
        expected_sources=[],
        required_keywords=["3.12", "3.13", "release", "2024"],
        forbidden_keywords=[],
    ),

    EvalQuestion(
        id="web_002",
        question="What are the current salary trends for backend developers in India in 2024?",
        expected_route="web",
        category="salary_trends",
        expected_sources=[],
        required_keywords=["LPA", "CTC", "2024", "backend", "experience"],
        forbidden_keywords=[],
    ),

    EvalQuestion(
        id="web_003",
        question="What new features were announced in React 19?",
        expected_route="web",
        category="current_version",
        expected_sources=[],
        required_keywords=["React 19", "compiler", "actions", "hooks", "2024"],
        forbidden_keywords=[],
    ),

    EvalQuestion(
        id="web_004",
        question="Which companies are hiring for AI/ML roles in 2025?",
        expected_route="web",
        category="hiring_trends",
        expected_sources=[],
        required_keywords=["hiring", "AI", "ML", "2025", "openings"],
        forbidden_keywords=[],
    ),

    EvalQuestion(
        id="web_005",
        question="What is the current market rate for a senior backend engineer in Bangalore?",
        expected_route="web",
        category="salary_trends",
        expected_sources=[],
        required_keywords=["Bangalore", "senior", "backend", "LPA", "market"],
        forbidden_keywords=[],
    ),

    EvalQuestion(
        id="web_006",
        question="What are the latest AWS service announcements from re:Invent 2024?",
        expected_route="web",
        category="current_info",
        expected_sources=[],
        required_keywords=["AWS", "re:Invent", "2024", "announced", "service"],
        forbidden_keywords=[],
    ),

    # ===== DIRECT ROUTE =====

    EvalQuestion(
        id="direct_001",
        question="Hello, how are you?",
        expected_route="direct",
        category="greeting",
        expected_sources=[],
        required_keywords=["hello", "help", "assist"],
        forbidden_keywords=[],
    ),

    EvalQuestion(
        id="direct_002",
        question="What can you help me with?",
        expected_route="direct",
        category="meta",
        expected_sources=[],
        required_keywords=["help", "question", "learn", "prepare", "roadmap", "resume", "interview"],
        forbidden_keywords=[],
    ),

    EvalQuestion(
        id="direct_003",
        question="Thank you for your help!",
        expected_route="direct",
        category="gratitude",
        expected_sources=[],
        required_keywords=["welcome", "happy", "help"],
        forbidden_keywords=[],
    ),

    # ===== INSUFFICIENT EVIDENCE / EDGE CASES =====

    EvalQuestion(
        id="edge_001",
        question="What is the meaning of life according to the knowledge base?",
        expected_route="knowledge_base",
        category="insufficient_evidence",
        expected_sources=[],
        required_keywords=["insufficient", "evidence", "rephrase", "specific"],
        forbidden_keywords=["42", "philosophy", "existential"],
        expects_insufficient_evidence=True,
    ),

    EvalQuestion(
        id="edge_002",
        question="Explain quantum computing algorithms for cryptography breaking.",
        expected_route="knowledge_base",
        category="insufficient_evidence",
        expected_sources=[],
        required_keywords=["insufficient", "evidence", "quantum", "cryptography"],
        forbidden_keywords=[],
        expects_insufficient_evidence=True,
    ),

    EvalQuestion(
        id="edge_003",
        question="How to build a time machine using Python?",
        expected_route="knowledge_base",
        category="impossible_question",
        expected_sources=[],
        required_keywords=["insufficient", "evidence", "not possible", "physics"],
        forbidden_keywords=["time machine", "code", "tutorial"],
        expects_insufficient_evidence=True,
    ),
]


# --- Helper Functions ---

def get_questions_by_route(route: str) -> List[EvalQuestion]:
    """Filter questions by expected route."""
    return [q for q in EVAL_QUESTIONS if q.expected_route == route]


def get_questions_by_category(category: str) -> List[EvalQuestion]:
    """Filter questions by category."""
    return [q for q in EVAL_QUESTIONS if q.category == category]


def get_all_questions() -> List[EvalQuestion]:
    """Get all evaluation questions."""
    return EVAL_QUESTIONS


def get_routing_test_set() -> List[Dict[str, Any]]:
    """Get questions formatted for routing accuracy testing."""
    return [
        {
            "id": q.id,
            "question": q.question,
            "expected_route": q.expected_route,
            "category": q.category,
        }
        for q in EVAL_QUESTIONS
    ]


def get_rag_test_set() -> List[Dict[str, Any]]:
    """Get questions formatted for RAG quality testing (KB route only)."""
    return [
        {
            "id": q.id,
            "question": q.question,
            "expected_sources": q.expected_sources,
            "required_keywords": q.required_keywords,
            "forbidden_keywords": q.forbidden_keywords,
            "min_citations": q.min_citations,
            "expects_insufficient_evidence": q.expects_insufficient_evidence,
        }
        for q in EVAL_QUESTIONS if q.expected_route == "knowledge_base"
    ]


if __name__ == "__main__":
    print(f"Total evaluation questions: {len(EVAL_QUESTIONS)}")
    print(f"Knowledge base: {len(get_questions_by_route('knowledge_base'))}")
    print(f"Web search: {len(get_questions_by_route('web'))}")
    print(f"Direct: {len(get_questions_by_route('direct'))}")

    print("\nBy category:")
    cats = {}
    for q in EVAL_QUESTIONS:
        cats[q.category] = cats.get(q.category, 0) + 1
    for cat, count in sorted(cats.items()):
        print(f"  {cat}: {count}")