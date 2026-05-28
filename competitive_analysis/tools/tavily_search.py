"""
Tavily Search Tool - web search for competitive intelligence gathering.

Respects rate limits and provides structured results with source URLs.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("competitive_analysis.tools.tavily")


class TavilySearch:
    """Tavily web search tool."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        try:
            from tavily import TavilyClient
            self.client = TavilyClient(api_key=api_key)
        except ImportError:
            logger.warning("tavily-python not installed. Install with: pip install tavily-python")
            self.client = None

    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Execute a web search and return structured results."""
        if not self.client:
            return {"query": query, "source": "tavily", "results": [], "error": "tavily not installed"}

        try:
            response = self.client.search(
                query=query,
                max_results=max_results,
                search_depth="advanced",
                include_answer=True,
            )
            results = []
            for item in response.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", ""),
                    "relevance_score": item.get("score"),
                    "metadata": {},
                })
            return {
                "query": query,
                "source": "tavily",
                "results": results,
                "answer": response.get("answer", ""),
            }
        except Exception as e:
            logger.error("Tavily search error: %s", e)
            return {"query": query, "source": "tavily", "results": [], "error": str(e)}
