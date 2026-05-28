"""
Writer Agent (报告撰写 Agent)

Responsible for:
- Generating structured Markdown/HTML competitive analysis reports
- Ensuring every claim has source citations
- Following the report template with all required sections
- Producing professional, actionable output
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from ..llm.base import BaseLLM
from ..prompts.loader import PromptLoader

logger = logging.getLogger("competitive_analysis.writer")


class WriterAgent:
    """Report generation agent - produces the final competitive analysis document."""

    def __init__(self, llm: BaseLLM):
        self.llm = llm
        self.prompt_loader = PromptLoader()

    def generate_report(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate the full competitive analysis report.

        Reads from state['analysis_result'] and state['competitor_profiles'].
        Writes to state['report_draft'].
        """
        query = state.get("query", "")
        analysis = state.get("analysis_result", {})
        profiles = state.get("competitor_profiles", [])

        prompt = self.prompt_loader.load(
            "writer_generate_report",
            query=query,
            analysis_data=json.dumps(analysis, ensure_ascii=False, default=str)[:6000],
            competitor_profiles=json.dumps(profiles, ensure_ascii=False, default=str)[:6000],
        )
        report = self.llm.generate(prompt, temperature=0.5, max_tokens=8192)

        state["report_draft"] = report
        state["report_version"] = state.get("report_version", 0) + 1

        # Calculate basic report metrics
        state["report_metrics"] = self._calculate_metrics(report)

        return state

    def revise_report(self, state: Dict[str, Any], feedback: str) -> Dict[str, Any]:
        """Revise the report based on QA feedback."""
        current_report = state.get("report_draft", "")
        prompt = f"""You are revising a competitive analysis report based on QA feedback.

**Current Report:**
{current_report[:5000]}

**QA Feedback:**
{feedback}

Please revise the report addressing ALL the feedback points.
Maintain all source citations and add any missing ones.
Return the complete revised report in Markdown format.
"""
        revised = self.llm.generate(prompt, temperature=0.4, max_tokens=8192)
        state["report_draft"] = revised
        state["report_version"] = state.get("report_version", 0) + 1
        state["report_metrics"] = self._calculate_metrics(revised)
        return state

    def _calculate_metrics(self, report: str) -> Dict[str, Any]:
        """Calculate report quality metrics."""
        import re
        lines = report.split("\n")
        sections = [l for l in lines if l.startswith("## ")]
        citations = re.findall(r"\[Source:.*?\]|\[E\d+\]|\[http[^\]]+\]", report)
        return {
            "total_chars": len(report),
            "total_lines": len(lines),
            "section_count": len(sections),
            "citation_count": len(citations),
            "sections_found": [s.strip("# ").strip() for s in sections],
        }
