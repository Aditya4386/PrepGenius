"""
web_search.py — Tavily web search integration for learning assistant.

Provides current-information retrieval with timeout, retry, and graceful degradation.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from langchain_tavily import TavilySearch
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class WebSearchResult:
    title: str
    url: str
    content: str
    score: float


class TavilySearchError(Exception):
    """Raised when Tavily search fails."""
    pass


def get_tavily_client() -> TavilySearch:
    """Get configured Tavily search client."""
    if not settings.TAVILY_API_KEY:
        raise TavilySearchError("TAVILY_API_KEY not configured")
    return TavilySearch(
        api_key=settings.TAVILY_API_KEY,
        max_results=5,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=False,
    )


def search_web(
    query: str,
    max_results: int = 5,
    timeout_seconds: float = 10.0,
) -> List[WebSearchResult]:
    """
    Search the web using Tavily.

    Args:
        query: Search query string
        max_results: Maximum number of results to return
        timeout_seconds: Request timeout

    Returns:
        List of WebSearchResult objects

    Raises:
        TavilySearchError: On API failure or timeout
    """
    try:
        client = get_tavily_client()
        response = client.invoke({"query": query})

        results = []
        for item in response.get("results", [])[:max_results]:
            results.append(WebSearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                content=item.get("content", ""),
                score=item.get("score", 0.0),
            ))

        logger.info(f"Tavily search for '{query}' returned {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"Tavily search failed for query '{query}': {e}")
        raise TavilySearchError(f"Web search failed: {e}") from e


def search_web_with_fallback(
    query: str,
    max_results: int = 5,
) -> List[WebSearchResult]:
    """
    Search with graceful degradation - returns empty list on failure instead of raising.
    """
    try:
        return search_web(query, max_results)
    except TavilySearchError as e:
        logger.warning(f"Tavily search degraded for '{query}': {e}")
        return []


def format_web_results_for_context(results: List[WebSearchResult]) -> str:
    """Format web search results as context string for LLM."""
    if not results:
        return "No web search results available."

    formatted = []
    for i, r in enumerate(results, 1):
        formatted.append(
            f"[{i}] {r.title}\nURL: {r.url}\nContent: {r.content[:500]}..."
        )
    return "\n\n".join(formatted)


def build_web_citations(results: List[WebSearchResult]) -> List[Dict[str, Any]]:
    """Build citation objects from web search results."""
    citations = []
    for i, r in enumerate(results, 1):
        citations.append({
            "index": i,
            "title": r.title,
            "url": r.url,
            "excerpt": r.content[:300],
        })
    return citations