"""
citations.py — Citation building for learning assistant answers.

Builds citations from actual retrieved evidence metadata, never from LLM text.
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class Citation:
    index: int
    title: str
    url: str
    page: Optional[int] = None
    excerpt: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


def build_citations_from_kb(
    retrieved_chunks: List[Dict[str, Any]],
    max_citations: int = 5,
) -> List[Citation]:
    """
    Build citations from knowledge base retrieval results.

    Args:
        retrieved_chunks: List of chunks from vector_search()
        max_citations: Maximum number of citations to include

    Returns:
        List of Citation objects
    """
    citations = []
    seen_urls = set()

    for i, chunk in enumerate(retrieved_chunks[:max_citations]):
        doc_title = chunk.get("document_title", "Unknown Source")
        source_url = chunk.get("source_url", "")
        page = chunk.get("page")
        excerpt = chunk.get("text", "")[:300]

        # Deduplicate by URL
        if source_url and source_url in seen_urls:
            continue
        if source_url:
            seen_urls.add(source_url)

        citations.append(Citation(
            index=len(citations) + 1,
            title=doc_title,
            url=source_url or f"kb://chunk/{chunk.get('id', 'unknown')}",
            page=page,
            excerpt=excerpt,
        ))

    return citations


def build_citations_from_web(
    web_results: List[Dict[str, Any]],
    max_citations: int = 5,
) -> List[Citation]:
    """
    Build citations from web search results.

    Args:
        web_results: List of web search results with title, url, content
        max_citations: Maximum number of citations

    Returns:
        List of Citation objects
    """
    citations = []

    for i, result in enumerate(web_results[:max_citations]):
        citations.append(Citation(
            index=i + 1,
            title=result.get("title", "Web Source"),
            url=result.get("url", ""),
            page=None,
            excerpt=result.get("content", "")[:300],
        ))

    return citations


def build_citations(
    route: str,
    kb_chunks: List[Dict[str, Any]] = None,
    web_results: List[Dict[str, Any]] = None,
    max_citations: int = 5,
) -> List[Dict[str, Any]]:
    """
    Build citations based on the route taken.

    Args:
        route: "knowledge_base", "web", or "direct"
        kb_chunks: Retrieved knowledge base chunks
        web_results: Web search results
        max_citations: Maximum total citations

    Returns:
        List of citation dicts
    """
    if route == "knowledge_base" and kb_chunks:
        citations = build_citations_from_kb(kb_chunks, max_citations)
    elif route == "web" and web_results:
        citations = build_citations_from_web(web_results, max_citations)
    else:
        citations = []

    return [c.to_dict() for c in citations]


def format_citations_for_display(citations: List[Dict[str, Any]]) -> str:
    """Format citations as a readable string for display."""
    if not citations:
        return ""

    lines = ["\n**Sources:**"]
    for c in citations:
        title = c.get("title", "Unknown")
        url = c.get("url", "")
        page = c.get("page")
        excerpt = c.get("excerpt", "")

        if page:
            lines.append(f"[{c['index']}] {title} (p. {page}) - {url}")
        else:
            lines.append(f"[{c['index']}] {title} - {url}")

        if excerpt:
            lines.append(f"    _{excerpt}_")

    return "\n".join(lines)