"""
Run tracing and observability - records every Agent decision, LLM call, and tool call.

Inspired by SDYJ_Multi_Agents tracing. Supports:
- Structured event timeline for debugging
- LLM call recording with latency and token usage
- Tool call recording with results
- Decision recording for DAG routing
- Trace persistence and replay
"""

from __future__ import annotations

import copy
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, Optional
from uuid import uuid4

from ..llm.base import BaseLLM


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def create_run_trace(
    query: str,
    provider: str,
    model: str | None,
    mode: str = "competitive_analysis",
    scenario_id: str | None = None,
) -> Dict[str, Any]:
    """Create a new trace object for a competitive analysis run."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_id = f"{timestamp}_{uuid4().hex[:8]}"
    return {
        "schema_version": "2.0",
        "run_id": run_id,
        "mode": mode,
        "scenario_id": scenario_id,
        "created_at": utc_now_iso(),
        "completed_at": None,
        "query": query,
        "provider": provider,
        "model": model,
        "config": {},
        "nodes": [],
        "llm_calls": [],
        "tool_calls": [],
        "events": [],
        "qa_feedback_loops": [],    # QA feedback loop records
        "replay_cache": {"llm_calls": [], "tool_calls": []},
        "artifacts": {},
        "report": {},
        "metrics": {},
        "errors": [],
    }


SENSITIVE_KEYS = ("api_key", "apikey", "authorization", "password", "secret", "token")


def _safe_text(text: str, limit: int = 1000) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}...<truncated {len(text) - limit} chars>"


def safe_snapshot(value: Any, max_depth: int = 3, max_items: int = 20) -> Any:
    """Create a JSON-safe, redacted snapshot for trace events."""
    if max_depth < 0:
        return "<max-depth>"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _safe_text(value)
    if isinstance(value, dict):
        out = {}
        for i, (k, v) in enumerate(value.items()):
            if i >= max_items:
                out["<truncated>"] = f"{len(value) - max_items} more"
                break
            if any(s in str(k).lower() for s in SENSITIVE_KEYS):
                out[str(k)] = "[REDACTED]"
            elif str(k) == "trace":
                out[str(k)] = {"run_id": v.get("run_id") if isinstance(v, dict) else None}
            else:
                out[str(k)] = safe_snapshot(v, max_depth - 1, max_items)
        return out
    if isinstance(value, (list, tuple)):
        items = list(value)
        out = [safe_snapshot(x, max_depth - 1, max_items) for x in items[:max_items]]
        if len(items) > max_items:
            out.append(f"<truncated {len(items) - max_items} items>")
        return out
    return _safe_text(str(value))


def record_trace_event(
    trace: Optional[Dict[str, Any]], event_type: str, name: str,
    node: str | None = None, status: str = "ok", latency_ms: int | None = None,
    input_snapshot: Any = None, output_snapshot: Any = None,
    metadata: Optional[Dict[str, Any]] = None, error: str | None = None,
) -> Optional[str]:
    """Append one structured event to the trace."""
    if not trace:
        return None
    seq = len(trace.setdefault("events", [])) + 1
    event = {
        "event_id": f"evt_{seq:06d}", "seq": seq,
        "event_type": event_type, "name": name, "node": node,
        "status": status, "timestamp": utc_now_iso(), "latency_ms": latency_ms,
        "input_snapshot": safe_snapshot(input_snapshot) if input_snapshot else None,
        "output_snapshot": safe_snapshot(output_snapshot) if output_snapshot else None,
        "metadata": safe_snapshot(metadata or {}), "error": error,
    }
    trace["events"].append(event)
    if error:
        trace.setdefault("errors", []).append({"where": f"event:{name}", "error": error})
    return event["event_id"]


def record_decision(
    trace: Optional[Dict[str, Any]], node: str, decision: str,
    reason: str | None = None, metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Record a routing/control-flow decision for observability."""
    record_trace_event(
        trace, event_type="decision", name=decision, node=node,
        output_snapshot={"decision": decision, "reason": reason}, metadata=metadata,
    )


def record_node_event(
    trace: Optional[Dict[str, Any]], node: str, latency_ms: int,
    status: str = "ok", metadata: Optional[Dict[str, Any]] = None, error: str | None = None,
) -> None:
    """Record a workflow node execution."""
    if not trace:
        return
    trace.setdefault("nodes", []).append({
        "node": node, "latency_ms": latency_ms, "status": status,
        "metadata": metadata or {}, "timestamp": utc_now_iso(), "error": error,
    })
    record_trace_event(
        trace, "node_end", node, node=node, status=status,
        latency_ms=latency_ms, metadata=metadata, error=error,
    )


def record_tool_call(
    trace: Optional[Dict[str, Any]], source: str, query: str,
    latency_ms: int, result_count: int, task_id: int | None = None,
    error: str | None = None, result: Optional[Dict[str, Any]] = None,
) -> None:
    """Record one retrieval/tool call."""
    if not trace:
        return
    tool_id = f"T{len(trace.get('tool_calls', [])) + 1}"
    trace.setdefault("tool_calls", []).append({
        "tool_call_id": tool_id, "source": source, "query": query,
        "task_id": task_id, "latency_ms": latency_ms,
        "result_count": result_count, "error": error, "timestamp": utc_now_iso(),
    })
    if result is not None:
        trace.setdefault("replay_cache", {}).setdefault("tool_calls", []).append({
            "tool_call_id": tool_id, "source": source, "query": query, "result": copy.deepcopy(result),
        })


def record_qa_feedback(
    trace: Optional[Dict[str, Any]], iteration: int,
    issues: list[str], target_agent: str, action: str,
) -> None:
    """Record a QA feedback loop event - unique to competitive analysis."""
    if not trace:
        return
    trace.setdefault("qa_feedback_loops", []).append({
        "iteration": iteration, "issues": issues,
        "target_agent": target_agent, "action": action,
        "timestamp": utc_now_iso(),
    })
    record_trace_event(
        trace, "qa_feedback", "qa_review", node="qa_agent",
        output_snapshot={"issues": issues, "target": target_agent, "action": action},
        metadata={"iteration": iteration},
    )


def finalize_trace(trace: Optional[Dict[str, Any]], metrics: Optional[Dict[str, Any]] = None) -> None:
    """Mark trace as complete."""
    if not trace:
        return
    trace["completed_at"] = utc_now_iso()
    if metrics:
        trace.setdefault("metrics", {}).update(metrics)


def save_trace(
    trace: Optional[Dict[str, Any]], output_dir: str | Path,
    report: str | None = None, report_ext: str = "md",
) -> Optional[Path]:
    """Persist trace and report to disk."""
    if not trace:
        return None
    finalize_trace(trace)
    run_id = trace["run_id"]
    run_dir = Path(output_dir) / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Save trace JSON
    trace_path = run_dir / "trace.json"
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2, ensure_ascii=False, default=str)

    # Save events as JSONL
    events_path = run_dir / "events.jsonl"
    with open(events_path, "w", encoding="utf-8") as f:
        for event in trace.get("events", []):
            f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")

    # Save report
    if report:
        report_path = run_dir / f"report.{report_ext}"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

    return trace_path


class InstrumentedLLM(BaseLLM):
    """Wrapper that records every LLM call to the trace for full observability."""

    def __init__(self, inner: BaseLLM, trace: Optional[Dict[str, Any]]):
        super().__init__(api_key=getattr(inner, "api_key", ""), model=getattr(inner, "model", "unknown"))
        self.inner = inner
        self.trace = trace

    def generate(self, prompt: str, **kwargs) -> str:
        started = time.perf_counter()
        try:
            response = self.inner.generate(prompt, **kwargs)
            latency_ms = int(round((time.perf_counter() - started) * 1000))
            self._record(prompt, response, kwargs, latency_ms, None)
            return response
        except Exception as e:
            latency_ms = int(round((time.perf_counter() - started) * 1000))
            self._record(prompt, "", kwargs, latency_ms, str(e))
            raise

    def chat(self, messages: list[Dict[str, str]], **kwargs) -> str:
        prompt_text = json.dumps(messages, ensure_ascii=False)
        started = time.perf_counter()
        try:
            response = self.inner.chat(messages, **kwargs)
            latency_ms = int(round((time.perf_counter() - started) * 1000))
            self._record(prompt_text, response, kwargs, latency_ms, None)
            return response
        except Exception as e:
            latency_ms = int(round((time.perf_counter() - started) * 1000))
            self._record(prompt_text, "", kwargs, latency_ms, str(e))
            raise

    def stream_generate(self, prompt: str, **kwargs) -> Iterator[str]:
        started = time.perf_counter()
        chunks = []
        try:
            for chunk in self.inner.stream_generate(prompt, **kwargs):
                chunks.append(chunk)
                yield chunk
            latency_ms = int(round((time.perf_counter() - started) * 1000))
            self._record(prompt, "".join(chunks), kwargs, latency_ms, None)
        except Exception as e:
            latency_ms = int(round((time.perf_counter() - started) * 1000))
            self._record(prompt, "".join(chunks), kwargs, latency_ms, str(e))
            raise

    def _record(self, prompt: str, response: str, kwargs: dict, latency_ms: int, error: str | None):
        if not self.trace:
            return
        call_id = f"L{len(self.trace.get('llm_calls', [])) + 1}"
        self.trace.setdefault("llm_calls", []).append({
            "call_id": call_id, "model": self.model, "latency_ms": latency_ms,
            "prompt_chars": len(prompt), "response_chars": len(response),
            "prompt_preview": prompt[:160].replace("\n", " "),
            "response_preview": response[:240].replace("\n", " "),
            "usage": getattr(self.inner, "last_usage", None),
            "error": error, "timestamp": utc_now_iso(),
        })
        record_trace_event(
            self.trace, "llm_call", call_id, status="error" if error else "ok",
            latency_ms=latency_ms,
            input_snapshot={"model": self.model, "prompt_preview": prompt[:160]},
            output_snapshot={"response_preview": response[:240], "usage": getattr(self.inner, "last_usage", None)},
            error=error,
        )
