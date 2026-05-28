"""Tests for QA Agent feedback loop logic."""

from competitive_analysis.agents.qa_agent import QAAgent
from competitive_analysis.llm.base import BaseLLM


class MockQALLM(BaseLLM):
    """Mock LLM that returns a QA review response."""
    def __init__(self, response_json: str = ""):
        super().__init__(api_key="test", model="mock")
        self._response = response_json or '{"overall_quality":"pass","score":0.85,"issues":[]}'

    def generate(self, prompt, **kwargs):
        return self._response

    def stream_generate(self, prompt, **kwargs):
        yield self._response


def test_qa_pass():
    llm = MockQALLM('{"overall_quality":"pass","score":0.9,"issues":[]}')
    qa = QAAgent(llm, max_retries=2)
    state = {"report_draft": "## Executive Summary\nGood report.", "query": "test",
             "evidence_items": [], "qa_iteration": 0}
    result = qa.review(state)
    assert result["qa_action"] == "accept"


def test_qa_fail_triggers_retry():
    fail_json = json.dumps({
        "overall_quality": "needs_revision", "score": 0.4,
        "issues": [{"severity": "critical", "description": "missing sources", "section": "all"}],
        "feedback_for_collector": "Need more data sources",
        "feedback_for_analyst": "",
        "feedback_for_writer": "Add source citations",
    })
    llm = MockQALLM(fail_json)
    qa = QAAgent(llm, max_retries=2)
    state = {"report_draft": "Bad report", "query": "test",
             "evidence_items": [], "qa_iteration": 0}
    result = qa.review(state)
    assert result["qa_action"].startswith("retry_")
    assert result["qa_iteration"] == 1


def test_qa_max_retries_accept():
    fail_json = '{"overall_quality":"needs_revision","score":0.3,"issues":[{"severity":"major","description":"incomplete"}]}'
    llm = MockQALLM(fail_json)
    qa = QAAgent(llm, max_retries=2)
    state = {"report_draft": "Bad report", "query": "test",
             "evidence_items": [], "qa_iteration": 2}  # already at max
    result = qa.review(state)
    assert result["qa_action"] == "accept"  # forced accept


import json  # needed for fail_json above
