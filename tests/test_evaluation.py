"""Tests for evaluation metrics."""

import pytest
from competitive_analysis.evaluation.metrics import (
    section_completeness, source_coverage, citation_density,
    schema_compliance, trace_completeness, qa_loop_effectiveness,
    evaluate_run,
)


SAMPLE_REPORT = """
# Competitive Analysis Report

## Executive Summary
Notion leads in features. [Source: https://notion.so]

## Methodology
Data collected via Tavily API.

## Competitor Profiles
- Notion: All-in-one workspace [Source: https://notion.so]
- Obsidian: Local-first markdown [Source: https://obsidian.md]

## Feature Comparison
| Feature | Notion | Obsidian |
|---------|--------|----------|
| Offline | No | Yes |

## Pricing Analysis
Notion: $8/mo, Obsidian: Free core [Source: https://obsidian.md/pricing]

## SWOT Analysis
Notion strengths: All-in-one [Source: https://notion.so]

## Key Insights
- Obsidian excels at offline use [Source: https://obsidian.md]

## Sources
- https://notion.so
- https://obsidian.md
"""


def test_section_completeness_full():
    score = section_completeness(SAMPLE_REPORT)
    assert score >= 0.8  # Most sections present


def test_section_completeness_empty():
    assert section_completeness("No sections here") == 0.0


def test_source_coverage():
    score = source_coverage(SAMPLE_REPORT)
    assert score > 0.5  # Most bullet points have sources


def test_citation_density():
    density = citation_density(SAMPLE_REPORT)
    assert density > 0  # Has citations


def test_schema_compliance():
    profiles = [
        {"company_name": "Notion", "product_name": "Notion",
         "description": "Workspace", "feature_tree": {}, "pricing": {},
         "swot": {}, "sources": [{"url": "https://notion.so"}]},
    ]
    score = schema_compliance(profiles)
    assert score == 1.0


def test_schema_compliance_partial():
    profiles = [{"company_name": "Notion", "product_name": "Notion"}]
    score = schema_compliance(profiles)
    assert 0 < score < 1.0


def test_trace_completeness_none():
    assert trace_completeness(None) == 0.0


def test_trace_completeness_full():
    trace = {
        "run_id": "test", "created_at": "now", "completed_at": "now",
        "query": "test", "provider": "mock", "model": "mock",
        "nodes": [
            {"node": "collector"}, {"node": "analyst"},
            {"node": "writer"}, {"node": "qa_agent"},
        ],
        "llm_calls": [], "tool_calls": [], "events": [{"type": "test"}],
        "qa_feedback_loops": [], "errors": [],
    }
    score = trace_completeness(trace)
    assert score >= 0.8


def test_qa_loop_effectiveness():
    state = {"qa_iteration": 2, "qa_result": {"score": 0.85, "overall_quality": "pass"},
             "initial_qa_score": 0.5}
    result = qa_loop_effectiveness(state)
    assert result["total_iterations"] == 2
    assert result["improvement"] == pytest.approx(0.35)
    assert result["converged"] is True


def test_evaluate_run():
    state = {
        "final_report": SAMPLE_REPORT,
        "competitor_profiles": [
            {"company_name": "Notion", "product_name": "Notion",
             "description": "test", "feature_tree": {}, "pricing": {},
             "swot": {}, "sources": []}
        ],
        "qa_iteration": 1,
        "qa_result": {"score": 0.8, "overall_quality": "pass"},
    }
    trace = {
        "run_id": "t1", "created_at": "now", "completed_at": "now",
        "query": "test", "provider": "mock", "model": "mock",
        "nodes": [{"node": "collector"}, {"node": "analyst"},
                  {"node": "writer"}, {"node": "qa_agent"}],
        "llm_calls": [], "tool_calls": [], "events": [{"e": 1}],
        "qa_feedback_loops": [], "errors": [],
    }
    metrics = evaluate_run(state, trace)
    assert "overall_score" in metrics
    assert 0 <= metrics["overall_score"] <= 1.0
    assert metrics["competitor_count"] == 1
