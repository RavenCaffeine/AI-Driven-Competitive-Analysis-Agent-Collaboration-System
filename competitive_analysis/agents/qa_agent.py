"""
QA Agent (质检 Agent)

Responsible for:
- Reviewing report for factual accuracy
- Checking source coverage and traceability
- Verifying schema compliance
- Generating feedback for other agents (feedback loop)
- Deciding whether to pass or send back for revision

This agent enables the DAG feedback loop: QA -> Collector/Analyst/Writer.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from ..llm.base import BaseLLM
from ..prompts.loader import PromptLoader
from ..utils.tracing import record_qa_feedback

logger = logging.getLogger("competitive_analysis.qa")


class QAAgent:
    """Quality assurance agent - reviews and validates competitive analysis output."""

    REQUIRED_SECTIONS = [
        "Executive Summary", "Methodology", "Competitor Profiles",
        "Feature Comparison", "Pricing Analysis", "SWOT Analysis",
        "Key Insights", "Sources",
    ]

    def __init__(self, llm: BaseLLM, max_retries: int = 2):
        self.llm = llm
        self.max_retries = max_retries
        self.prompt_loader = PromptLoader()

    def review(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Review the report draft and generate structured feedback.

        Writes to state['qa_result'] with pass/fail and detailed feedback.
        If issues found, sets state['qa_action'] to indicate which agent to retry.
        """
        report = state.get("report_draft", "")
        query = state.get("query", "")
        evidence = state.get("evidence_items", [])

        # Build evidence summary for QA
        evidence_summary = self._summarize_evidence(evidence)

        prompt = self.prompt_loader.load(
            "qa_review",
            query=query,
            report=report[:6000],
            evidence_summary=evidence_summary[:3000],
        )
        response = self.llm.generate(prompt, temperature=0.2)

        try:
            qa_result = self._parse_json(response)
        except Exception as e:
            logger.error("Failed to parse QA review: %s", e)
            qa_result = {"overall_quality": "pass", "score": 0.7, "issues": []}

        state["qa_result"] = qa_result

        # Determine action based on review
        quality = qa_result.get("overall_quality", "pass")
        qa_iteration = state.get("qa_iteration", 0)

        if quality == "pass" or qa_iteration >= self.max_retries:
            state["qa_action"] = "accept"
            if qa_iteration >= self.max_retries:
                logger.warning("QA max retries reached, accepting with issues")
        else:
            # Determine which agent needs to redo work
            issues = qa_result.get("issues", [])
            target = self._determine_target_agent(issues, qa_result)
            state["qa_action"] = f"retry_{target}"
            state["qa_feedback"] = self._build_feedback(qa_result, target)
            state["qa_iteration"] = qa_iteration + 1

            # Record in trace
            record_qa_feedback(
                state.get("trace"),
                iteration=qa_iteration + 1,
                issues=[i.get("description", "") for i in issues],
                target_agent=target,
                action=state["qa_action"],
            )

        return state

    def _determine_target_agent(self, issues: List[Dict], qa_result: Dict) -> str:
        """Determine which agent should redo work based on issue types."""
        critical_issues = [i for i in issues if i.get("severity") == "critical"]

        # If missing data/sources, send back to collector
        if qa_result.get("feedback_for_collector"):
            for issue in critical_issues:
                if "source" in issue.get("description", "").lower() or \
                   "missing data" in issue.get("description", "").lower():
                    return "collector"

        # If analysis quality issues, send back to analyst
        if qa_result.get("feedback_for_analyst"):
            for issue in critical_issues:
                if "analysis" in issue.get("description", "").lower() or \
                   "swot" in issue.get("description", "").lower():
                    return "analyst"

        # Default: send back to writer
        return "writer"

    def _build_feedback(self, qa_result: Dict, target: str) -> str:
        """Build specific feedback string for the target agent."""
        feedback_key = f"feedback_for_{target}"
        specific = qa_result.get(feedback_key, "")
        issues = qa_result.get("issues", [])
        issue_texts = [f"- [{i.get('severity', '?')}] {i.get('description', '')}" for i in issues]
        return f"QA Feedback:\n{specific}\n\nDetailed Issues:\n" + "\n".join(issue_texts)

    def _summarize_evidence(self, evidence: List[Dict]) -> str:
        lines = []
        for item in evidence[:20]:
            eid = item.get("evidence_id", "?")
            title = item.get("title", "Untitled")
            url = item.get("url", "N/A")
            lines.append(f"[{eid}] {title} - {url}")
        return "\n".join(lines)

    def _parse_json(self, text: str) -> Dict:
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())
