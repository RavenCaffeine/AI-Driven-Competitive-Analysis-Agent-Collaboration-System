"""Tests for tracing and observability."""

import json
from competitive_analysis.utils.tracing import (
    create_run_trace, record_trace_event, record_decision,
    record_node_event, record_tool_call, record_qa_feedback,
    finalize_trace, safe_snapshot, InstrumentedLLM,
)
from competitive_analysis.llm.base import BaseLLM


class DummyLLM(BaseLLM):
    def generate(self, prompt, **kwargs):
        return "dummy response"
    def stream_generate(self, prompt, **kwargs):
        yield "chunk"


def test_create_trace():
    trace = create_run_trace("test query", "deepseek", "deepseek-chat")
    assert trace["schema_version"] == "2.0"
    assert trace["query"] == "test query"
    assert "run_id" in trace


def test_record_event():
    trace = create_run_trace("q", "p", "m")
    eid = record_trace_event(trace, "test_event", "my_event", node="collector")
    assert eid == "evt_000001"
    assert len(trace["events"]) == 1


def test_record_decision():
    trace = create_run_trace("q", "p", "m")
    record_decision(trace, "qa_agent", "accept_report", reason="passed QA")
    assert len(trace["events"]) == 1
    assert trace["events"][0]["event_type"] == "decision"


def test_record_node_event():
    trace = create_run_trace("q", "p", "m")
    record_node_event(trace, "collector", 1500, metadata={"results": 10})
    assert len(trace["nodes"]) == 1
    assert trace["nodes"][0]["latency_ms"] == 1500


def test_record_tool_call():
    trace = create_run_trace("q", "p", "m")
    record_tool_call(trace, "tavily", "notion pricing", 500, 5)
    assert len(trace["tool_calls"]) == 1
    assert trace["tool_calls"][0]["source"] == "tavily"


def test_record_qa_feedback():
    trace = create_run_trace("q", "p", "m")
    record_qa_feedback(trace, 1, ["missing sources"], "writer", "retry_writer")
    assert len(trace["qa_feedback_loops"]) == 1
    assert trace["qa_feedback_loops"][0]["target_agent"] == "writer"


def test_finalize():
    trace = create_run_trace("q", "p", "m")
    finalize_trace(trace, metrics={"overall_score": 0.85})
    assert trace["completed_at"] is not None
    assert trace["metrics"]["overall_score"] == 0.85


def test_safe_snapshot_redacts():
    data = {"name": "test", "api_key": "secret123", "nested": {"token": "abc"}}
    snap = safe_snapshot(data)
    assert snap["api_key"] == "[REDACTED]"
    assert snap["nested"]["token"] == "[REDACTED]"
    assert snap["name"] == "test"


def test_instrumented_llm():
    trace = create_run_trace("q", "p", "m")
    inner = DummyLLM(api_key="test", model="dummy")
    instrumented = InstrumentedLLM(inner, trace)
    result = instrumented.generate("hello")
    assert result == "dummy response"
    assert len(trace["llm_calls"]) == 1
    assert trace["llm_calls"][0]["model"] == "dummy"
    assert trace["llm_calls"][0]["latency_ms"] >= 0
