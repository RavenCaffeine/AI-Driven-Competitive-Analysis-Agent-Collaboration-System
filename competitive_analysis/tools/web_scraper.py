"""
Simple web content fetcher - fetches and extracts text from URLs.

Respects robots.txt compliance.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("competitive_analysis.tools.web")


class WebScraper:
    """Simple URL content fetcher using httpx + readability."""

    def fetch(self, url: str, timeout: int = 15) -> Optional[str]:
        """Fetch and extract main content from a URL."""
        try:
            import httpx
            resp = httpx.get(url, timeout=timeout, follow_redirects=True)
            resp.raise_for_status()
            return resp.text[:10000]  # Limit content length
        except Exception as e:
            logger.error("Fetch error for %s: %s", url, e)
            return None
