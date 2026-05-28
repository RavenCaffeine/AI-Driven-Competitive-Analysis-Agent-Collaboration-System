"""
Workflow Nodes - Functions that execute within the LangGraph DAG.

Each node wraps one Agent's action and records observability data.
The QA node implements the feedback loop via conditional routing.
"""

from __future__ import annotations

import time
import json
import logging
from typing import Any, Dict

from ..agents.collector import CollectorAgent
from ..agents.analyst import AnalystAgent
from ..agents.writer import WriterAgent
from ..agents.qa_agent import QAAgent
from ..utils.tracing import record_decision, record_node_event, record_trace_event

logger = logging.getLogger("competitive_analysis.workflow")


class WorkflowNodes:
    """Container for all workflow node functions."""

    def __init__(
        self,
        collector: CollectorAgent,
        analyst: AnalystAgent,
        writer: WriterAgent,
        qa_agent: QAAgent,
    ):
        self.collector = collector
        self.analyst = analyst
        self.writer = writer
        self.qa_agent = qa_agent

    # ==================== Node Functions ====================

    def collector_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collector node - plans and executes data collection.

        1. Plans search queries per competitor
        2. Executes searches via tools
        3. Extracts structured data from results
        """
        started = time.perf_counter()
        record_trace_event(state.get("trace"), "node_start", "collector", node="collector")
        try:
            state["current_step"] = "collecting"

            # Step 1: Plan collection
            plan = self.collector.plan_collection(
                state["query"], state["competitors"]
            )
            state["collection_plan"] = plan

            # Step 2: Execute collection tasks
            tasks = plan.get("collection_tasks", [])
            state = self.collector.collect_data(state, tasks)

            # Step 3: Organize collected data by competitor
            collected = {"competitors": state["competitors"]}
            for comp in state["competitors"]:
                comp_results = [
                    r for r in state.get("raw_search_results", [])
                    if r.get("competitor") == comp
                ]
                if comp_results:
                    for aspect in ["features", "pricing", "user_reviews", "market_position"]:
                        aspect_results = [r for r in comp_results if r.get("aspect") == aspect]
                        if aspect_results:
                            extracted = self.collector.extract_structured_data(
                                state, comp, aspect, aspect_results
                            )
                            collected.setdefault(comp, {})[aspect] = extracted

            state["collected_data"] = collected
            return state
        finally:
            latency = int(round((time.perf_counter() - started) * 1000))
            record_node_event(state.get("trace"), "collector", latency)

    def analyst_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyst node - performs comparative analysis on collected data."""
        started = time.perf_counter()
        record_trace_event(state.get("trace"), "node_start", "analyst", node="analyst")
        try:
            state["current_step"] = "analyzing"
            state = self.analyst.analyze(state)
            return state
        finally:
            latency = int(round((time.perf_counter() - started) * 1000))
            record_node_event(state.get("trace"), "analyst", latency)

    def writer_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Writer node - generates the report from analysis results."""
        started = time.perf_counter()
        record_trace_event(state.get("trace"), "node_start", "writer", node="writer")
        try:
            state["current_step"] = "writing"

            # Check if this is a revision based on QA feedback
            if state.get("qa_action") == "retry_writer" and state.get("qa_feedback"):
                state = self.writer.revise_report(state, state["qa_feedback"])
                state["qa_action"] = None
                state["qa_feedback"] = None
            else:
                state = self.writer.generate_report(state)

            return state
        finally:
            latency = int(round((time.perf_counter() - started) * 1000))
            record_node_event(
                state.get("trace"), "writer", latency,
                metadata=state.get("report_metrics"),
            )

    def qa_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        QA node - reviews the report and decides: accept or send back.

        This is the key node for the feedback loop mechanism.
        """
        started = time.perf_counter()
        record_trace_event(state.get("trace"), "node_start", "qa_agent", node="qa_agent")
        try:
            state["current_step"] = "quality_checking"
            state = self.qa_agent.review(state)
            return state
        finally:
            latency = int(round((time.perf_counter() - started) * 1000))
            record_node_event(
                state.get("trace"), "qa_agent", latency,
                metadata={
                    "quality": state.get("qa_result", {}).get("overall_quality"),
                    "score": state.get("qa_result", {}).get("score"),
                    "action": state.get("qa_action"),
                    "iteration": state.get("qa_iteration", 0),
                },
            )

    def finalize_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize node - marks workflow as complete and prepares output."""
        state["current_step"] = "completed"
        state["final_report"] = state.get("report_draft", "")

        # Generate HTML version of the report
        if state.get("report_draft"):
            try:
                from ..report.html_template import render_html_report
                state["html_report"] = render_html_report(
                    markdown_report=state.get("report_draft", ""),
                    query=state.get("query", ""),
                    competitors=state.get("competitors", []),
                    metadata={
                        "provider": state.get("trace", {}).get("provider", ""),
                        "model": state.get("trace", {}).get("model", ""),
                        "run_id": state.get("trace", {}).get("run_id", ""),
                    },
                )
            except Exception as e:
                logger.warning("HTML report generation failed: %s", e)

        return state

    # ==================== Routing Functions ====================

    def qa_route(self, state: Dict[str, Any]) -> str:
        """
        QA routing decision - the heart of the feedback loop.

        Returns:
            "accept"    -> finalize (report is good)
            "collector" -> re-collect (missing data)
            "analyst"   -> re-analyze (analysis issues)
            "writer"    -> re-write (writing issues)
        """
        action = state.get("qa_action", "accept")

        if action == "accept":
            record_decision(state.get("trace"), "qa_agent", "accept_report",
                          reason="QA passed or max retries reached")
            return "accept"
        elif action == "retry_collector":
            record_decision(state.get("trace"), "qa_agent", "retry_collector",
                          reason="Missing data or sources")
            return "collector"
        elif action == "retry_analyst":
            record_decision(state.get("trace"), "qa_agent", "retry_analyst",
                          reason="Analysis quality issues")
            return "analyst"
        elif action == "retry_writer":
            record_decision(state.get("trace"), "qa_agent", "retry_writer",
                          reason="Report writing issues")
            return "writer"
        else:
            record_decision(state.get("trace"), "qa_agent", "accept_report",
                          reason="Unknown action, defaulting to accept")
            return "accept"
