"""
Competitive Analysis Workflow State

Defines the state structure that flows through the LangGraph DAG.
All agents read from and write to this shared state.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, List, Optional, TypedDict


class CompetitiveAnalysisState(TypedDict):
    """
    Shared state for the competitive analysis workflow.

    This state is passed through every node in the LangGraph DAG.
    """
    # Input
    query: str                              # Original user query
    competitors: List[str]                  # List of competitor names to analyze

    # Collection phase
    collection_plan: Optional[Dict[str, Any]]       # Collector's search plan
    raw_search_results: List[Dict[str, Any]]        # Raw search results from tools
    collected_data: Optional[Dict[str, Any]]        # Structured collected data
    evidence_items: List[Dict[str, Any]]            # Deduplicated evidence for traceability

    # Analysis phase
    analysis_result: Optional[Dict[str, Any]]       # Analyst's structured output
    competitor_profiles: List[Dict[str, Any]]       # Schema-conforming profiles

    # Report phase
    report_draft: Optional[str]                     # Current report draft
    report_version: int                             # Report revision counter
    report_metrics: Optional[Dict[str, Any]]        # Report quality metrics

    # QA phase (feedback loop)
    qa_result: Optional[Dict[str, Any]]             # QA review result
    qa_action: Optional[str]                        # "accept" | "retry_collector" | "retry_analyst" | "retry_writer"
    qa_feedback: Optional[str]                      # Feedback text for the target agent
    qa_iteration: int                               # Feedback loop counter

    # Workflow control
    current_step: str                               # Current workflow step name
    max_qa_retries: int                             # Max QA retry rounds
    output_format: str                              # "markdown" | "html"

    # Observability
    trace: Optional[Dict[str, Any]]                 # Full run trace
