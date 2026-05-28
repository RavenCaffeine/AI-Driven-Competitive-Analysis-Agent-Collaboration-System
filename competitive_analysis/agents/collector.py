"""
Collector Agent (信息采集 Agent)

Responsible for:
- Planning data collection tasks per competitor
- Executing web searches via tools (Tavily, etc.)
- Extracting structured data from search results
- Maintaining source traceability for every data point

Outputs structured data conforming to CompetitorProfile schema.
"""

from __future__ import annotations

import json
import time
import logging
from typing import Any, Dict, List, Optional

from ..llm.base import BaseLLM
from ..prompts.loader import PromptLoader
from ..schemas.competitive import SourceReference
from ..utils.tracing import record_tool_call, record_trace_event

logger = logging.getLogger("competitive_analysis.collector")


class CollectorAgent:
    """Information collection agent - gathers competitive intelligence from public sources."""

    def __init__(self, llm: BaseLLM, tools: Dict[str, Any] | None = None):
        self.llm = llm
        self.tools = tools or {}
        self.prompt_loader = PromptLoader()

    def plan_collection(self, query: str, competitors: List[str]) -> Dict[str, Any]:
        """Generate a collection plan with search queries per competitor."""
        prompt = self.prompt_loader.load(
            "collector_plan_queries",
            query=query,
            competitors=", ".join(competitors),
        )
        response = self.llm.generate(prompt, temperature=0.3)
        try:
            # Try to extract JSON from response
            return self._parse_json(response)
        except Exception as e:
            logger.warning("Failed to parse collection plan: %s", e)
            return self._fallback_plan(competitors)

    def collect_data(
        self, state: Dict[str, Any], tasks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute collection tasks and aggregate results."""
        all_results = []
        evidence_items = state.get("evidence_items", [])

        for task in tasks:
            for search_query in task.get("search_queries", []):
                for source_name in task.get("sources", ["tavily"]):
                    started = time.perf_counter()
                    result = self._search(search_query, source_name)
                    latency_ms = int(round((time.perf_counter() - started) * 1000))

                    if result:
                        result["task_id"] = task.get("task_id")
                        result["competitor"] = task.get("competitor", "")
                        result["aspect"] = task.get("aspect", "")
                        all_results.append(result)
                        record_tool_call(
                            state.get("trace"), source=source_name,
                            query=search_query, latency_ms=latency_ms,
                            result_count=len(result.get("results", [])),
                            task_id=task.get("task_id"), result=result,
                        )
                    else:
                        record_tool_call(
                            state.get("trace"), source=source_name,
                            query=search_query, latency_ms=latency_ms,
                            result_count=0, error="no results",
                        )

        state["raw_search_results"] = state.get("raw_search_results", []) + all_results
        return state

    def extract_structured_data(
        self, state: Dict[str, Any], competitor: str, aspect: str, results: List[Dict]
    ) -> Dict[str, Any]:
        """Use LLM to extract structured data from raw search results."""
        formatted = self._format_results(results)
        prompt = self.prompt_loader.load(
            "collector_extract_data",
            competitor=competitor,
            aspect=aspect,
            search_results=formatted,
        )
        response = self.llm.generate(prompt, temperature=0.2)
        try:
            return self._parse_json(response)
        except Exception:
            return {"raw_text": response}

    def _search(self, query: str, source: str) -> Optional[Dict[str, Any]]:
        """Execute a search using available tools."""
        source = source.lower().strip()
        tool = self.tools.get(source)
        if not tool:
            logger.warning("Tool '%s' not available", source)
            return None
        try:
            return tool.search(query)
        except Exception as e:
            logger.error("Search error [%s]: %s", source, e)
            return {"query": query, "source": source, "results": [], "error": str(e)}

    def _format_results(self, results: List[Dict]) -> str:
        lines = []
        for i, r in enumerate(results, 1):
            for item in r.get("results", [])[:5]:
                lines.append(f"{i}. [{r.get('source', '?')}] {item.get('title', 'N/A')}")
                lines.append(f"   URL: {item.get('url', 'N/A')}")
                lines.append(f"   {str(item.get('snippet', ''))[:300]}")
        return "\n".join(lines)

    def _parse_json(self, text: str) -> Dict:
        """Extract JSON from LLM response (handles markdown code blocks)."""
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())

    def _fallback_plan(self, competitors: List[str]) -> Dict:
        tasks = []
        tid = 1
        for comp in competitors:
            for aspect in ["features", "pricing", "user_reviews", "market_position"]:
                tasks.append({
                    "task_id": tid, "competitor": comp, "aspect": aspect,
                    "search_queries": [f"{comp} {aspect} 2024 2025"],
                    "sources": ["tavily"], "priority": 1,
                })
                tid += 1
        return {"competitors": competitors, "collection_tasks": tasks}
