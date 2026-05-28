"""
Competitive Analysis DAG Workflow

Builds the LangGraph state graph with:
- Linear pipeline: Collector -> Analyst -> Writer -> QA
- Feedback loop: QA can route back to Collector, Analyst, or Writer
- Finalization: QA accept -> Finalize -> END

This implements the DAG task flow with cross-review feedback closed loop.
"""

from __future__ import annotations

from typing import Optional

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

from .nodes import WorkflowNodes
from ..agents.collector import CollectorAgent
from ..agents.analyst import AnalystAgent
from ..agents.writer import WriterAgent
from ..agents.qa_agent import QAAgent
from ..utils.tracing import (
    create_run_trace, finalize_trace, save_trace,
    record_trace_event, InstrumentedLLM,
)
from ..utils.config import AppConfig
from ..llm.factory import LLMFactory


def build_graph(nodes: WorkflowNodes):
    """
    Build the competitive analysis LangGraph DAG.

    Topology:
        START -> collector -> analyst -> writer -> qa_agent
                    ^            ^          ^         |
                    |            |          |         v
                    +---- (feedback loop) ---+--- finalize -> END
    """
    workflow = StateGraph(dict)

    # Add nodes
    workflow.add_node("collector", nodes.collector_node)
    workflow.add_node("analyst", nodes.analyst_node)
    workflow.add_node("writer", nodes.writer_node)
    workflow.add_node("qa_agent", nodes.qa_node)
    workflow.add_node("finalize", nodes.finalize_node)

    # Linear pipeline edges
    workflow.add_edge(START, "collector")
    workflow.add_edge("collector", "analyst")
    workflow.add_edge("analyst", "writer")
    workflow.add_edge("writer", "qa_agent")

    # QA feedback loop: conditional routing
    workflow.add_conditional_edges(
        "qa_agent",
        nodes.qa_route,
        {
            "accept": "finalize",       # Report passes QA
            "collector": "collector",    # Missing data -> re-collect
            "analyst": "analyst",        # Bad analysis -> re-analyze
            "writer": "writer",          # Bad writing -> re-write
        },
    )

    # Finalize -> END
    workflow.add_edge("finalize", END)

    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


class CompetitiveAnalysisWorkflow:
    """
    High-level workflow manager for competitive analysis.

    Handles LLM creation, agent instantiation, graph building, and execution.
    """

    def __init__(self, config: AppConfig, tools: dict | None = None):
        self.config = config
        self.tools = tools or {}

        # Create LLM instances (with optional per-agent overrides)
        self.llm = LLMFactory.create(
            provider=config.llm.provider,
            api_key=config.llm.api_key,
            model=config.llm.model,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
            **({"base_url": config.llm.base_url} if config.llm.base_url else {}),
        )

        # Create agents
        self.collector = CollectorAgent(self.llm, tools=self.tools)
        self.analyst = AnalystAgent(self.llm)
        self.writer = WriterAgent(self.llm)
        self.qa_agent = QAAgent(self.llm, max_retries=config.max_qa_retries)

        # Build graph
        self.nodes = WorkflowNodes(self.collector, self.analyst, self.writer, self.qa_agent)
        self.graph = build_graph(self.nodes)

    def run(
        self,
        query: str,
        competitors: list[str],
        output_format: str = "markdown",
    ) -> dict:
        """
        Run the full competitive analysis pipeline.

        Args:
            query: Analysis request (e.g., "Compare Notion vs Obsidian vs Logseq")
            competitors: List of competitor names
            output_format: "markdown" or "html"

        Returns:
            Final workflow state with report and trace
        """
        # Create trace for observability
        trace = create_run_trace(
            query=query,
            provider=self.config.llm.provider,
            model=self.config.llm.model,
        )

        # Wrap LLM with instrumentation
        instrumented = InstrumentedLLM(self.llm, trace)
        self.collector.llm = instrumented
        self.analyst.llm = instrumented
        self.writer.llm = instrumented
        self.qa_agent.llm = instrumented

        # Initialize state
        initial_state = {
            "query": query,
            "competitors": competitors,
            "collection_plan": None,
            "raw_search_results": [],
            "collected_data": None,
            "evidence_items": [],
            "analysis_result": None,
            "competitor_profiles": [],
            "report_draft": None,
            "report_version": 0,
            "report_metrics": None,
            "qa_result": None,
            "qa_action": None,
            "qa_feedback": None,
            "qa_iteration": 0,
            "current_step": "initializing",
            "max_qa_retries": self.config.max_qa_retries,
            "output_format": output_format,
            "trace": trace,
        }

        # Run the graph
        config = {"configurable": {"thread_id": trace["run_id"]}}
        final_state = self.graph.invoke(initial_state, config=config)

        # Finalize and save trace
        finalize_trace(trace, metrics=final_state.get("report_metrics"))
        save_trace(trace, self.config.output_dir, report=final_state.get("final_report"))

        return final_state

    def get_graph_schema(self) -> dict:
        """Return the DAG topology for documentation/visualization."""
        return {
            "nodes": ["collector", "analyst", "writer", "qa_agent", "finalize"],
            "edges": [
                ("START", "collector"),
                ("collector", "analyst"),
                ("analyst", "writer"),
                ("writer", "qa_agent"),
                ("qa_agent", "finalize"),     # accept
                ("qa_agent", "collector"),     # feedback loop
                ("qa_agent", "analyst"),       # feedback loop
                ("qa_agent", "writer"),        # feedback loop
                ("finalize", "END"),
            ],
            "feedback_loops": [
                {"from": "qa_agent", "to": "collector", "condition": "missing data"},
                {"from": "qa_agent", "to": "analyst", "condition": "analysis issues"},
                {"from": "qa_agent", "to": "writer", "condition": "writing issues"},
            ],
        }

    def visualize(self) -> str:
        """Generate Mermaid diagram of the workflow."""
        try:
            return self.graph.get_graph().draw_mermaid()
        except Exception:
            return self._fallback_mermaid()

    def _fallback_mermaid(self) -> str:
        return """graph TD
    START --> collector[Collector Agent]
    collector --> analyst[Analyst Agent]
    analyst --> writer[Writer Agent]
    writer --> qa_agent[QA Agent]
    qa_agent -->|accept| finalize[Finalize]
    qa_agent -->|missing data| collector
    qa_agent -->|analysis issues| analyst
    qa_agent -->|writing issues| writer
    finalize --> END
"""
