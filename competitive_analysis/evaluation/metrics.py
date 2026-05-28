"""
Evaluation Metrics for Competitive Analysis Agent.

Provides quantitative metrics to answer: "How do you evaluate your agent?"

Dimensions:
1. Schema Compliance   - Does output conform to the CompetitorProfile schema?
2. Source Coverage      - Are claims backed by evidence?
3. Section Completeness - Are all required report sections present?
4. QA Loop Effectiveness - Did feedback loops improve the output?
5. Trace Completeness   - Is the run fully observable?
6. Overall Score        - Weighted composite score
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional


REQUIRED_SECTIONS = [
    "Executive Summary", "Methodology", "Competitor Profiles",
    "Feature Comparison", "Pricing Analysis", "SWOT Analysis",
    "Key Insights", "Sources",
]

REQUIRED_TRACE_FIELDS = [
    "run_id", "created_at", "completed_at", "query", "provider",
    "model", "nodes", "llm_calls", "tool_calls", "events", "errors",
]


def section_completeness(report: str, expected: List[str] | None = None) -> float:
    """Score: fraction of expected sections found in the report."""
    sections = expected or REQUIRED_SECTIONS
    if not sections:
        return 1.0
    found = 0
    for section in sections:
        if f"## {section}" in report or f"# {section}" in report or section.lower() in report.lower():
            found += 1
    return found / len(sections)


def source_coverage(report: str) -> float:
    """Score: fraction of bullet-point claims that have a source citation."""
    lines = [l.strip() for l in report.split("\n") if l.strip().startswith("- ")]
    if not lines:
        return 1.0
    cited = [l for l in lines if re.search(r"\[Source:|\[E\d+\]|\[http", l)]
    return len(cited) / len(lines)


def citation_density(report: str) -> float:
    """Citations per 1000 characters."""
    citations = re.findall(r"\[Source:.*?\]|\[E\d+\]|\[http[^\]]+\]", report)
    return len(citations) / max(len(report), 1) * 1000


def schema_compliance(profiles: List[Dict], required_fields: List[str] | None = None) -> float:
    """Score: fraction of required fields present in competitor profiles."""
    fields = required_fields or [
        "company_name", "product_name", "description",
        "feature_tree", "pricing", "swot", "sources",
    ]
    if not profiles:
        return 0.0
    total = len(profiles) * len(fields)
    found = 0
    for profile in profiles:
        for field in fields:
            if profile.get(field) is not None:
                found += 1
    return found / total if total > 0 else 0.0


def qa_loop_effectiveness(state: Dict[str, Any]) -> Dict[str, Any]:
    """Measure QA feedback loop effectiveness."""
    qa_iterations = state.get("qa_iteration", 0)
    qa_result = state.get("qa_result", {})
    initial_score = state.get("initial_qa_score", 0.0)
    final_score = qa_result.get("score", 0.0)

    return {
        "total_iterations": qa_iterations,
        "initial_score": initial_score,
        "final_score": final_score,
        "improvement": final_score - initial_score,
        "converged": qa_result.get("overall_quality") == "pass",
    }


def trace_completeness(trace: Dict[str, Any]) -> float:
    """Score: is the trace sufficient for debugging and replay?"""
    if not trace:
        return 0.0

    # Check top-level fields
    top_score = sum(1 for f in REQUIRED_TRACE_FIELDS if f in trace) / len(REQUIRED_TRACE_FIELDS)

    # Check node coverage
    required_nodes = {"collector", "analyst", "writer", "qa_agent"}
    observed = {n.get("node") for n in trace.get("nodes", [])}
    node_score = len(required_nodes & observed) / len(required_nodes)

    # Check events exist
    event_score = 1.0 if trace.get("events") else 0.0

    # Check QA feedback loops recorded
    qa_score = 1.0 if trace.get("qa_feedback_loops") is not None else 0.5

    return round(0.3 * top_score + 0.3 * node_score + 0.2 * event_score + 0.2 * qa_score, 4)


def evaluate_run(state: Dict[str, Any], trace: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Comprehensive evaluation of a competitive analysis run.

    This is the answer to: "How do you evaluate your agent?"
    """
    report = state.get("final_report") or state.get("report_draft") or ""
    profiles = state.get("competitor_profiles", [])

    metrics = {
        "section_completeness": section_completeness(report),
        "source_coverage": source_coverage(report),
        "citation_density_per_1k": citation_density(report),
        "schema_compliance": schema_compliance(profiles),
        "trace_completeness": trace_completeness(trace) if trace else 0.0,
        "qa_loop": qa_loop_effectiveness(state),
        "report_length_chars": len(report),
        "competitor_count": len(profiles),
    }

    # Weighted overall score
    metrics["overall_score"] = round(
        0.20 * metrics["section_completeness"]
        + 0.20 * metrics["source_coverage"]
        + 0.15 * min(metrics["citation_density_per_1k"] / 3.0, 1.0)
        + 0.15 * metrics["schema_compliance"]
        + 0.15 * metrics["trace_completeness"]
        + 0.15 * metrics["qa_loop"].get("final_score", 0.0),
        4,
    )

    return metrics
