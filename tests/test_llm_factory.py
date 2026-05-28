"""Tests for LLM factory pattern."""

import pytest
from competitive_analysis.llm.base import BaseLLM
from competitive_analysis.llm.factory import LLMFactory


class MockLLM(BaseLLM):
    """Mock LLM for testing."""
    def __init__(self, api_key: str, model: str = "mock-default", **kwargs):
        super().__init__(api_key=api_key, model=model, **kwargs)

    def generate(self, prompt, **kwargs):
        return f"mock response to: {prompt[:30]}"

    def stream_generate(self, prompt, **kwargs):
        yield "mock "
        yield "stream"


def test_register_and_create():
    LLMFactory.register_provider("mock", MockLLM)
    llm = LLMFactory.create("mock", api_key="test-key", model="mock-v1")
    assert isinstance(llm, MockLLM)
    assert llm.model == "mock-v1"


def test_create_generates():
    LLMFactory.register_provider("mock", MockLLM)
    llm = LLMFactory.create("mock", api_key="test-key")
    result = llm.generate("Hello world")
    assert "mock response" in result


def test_unknown_provider():
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        LLMFactory.create("nonexistent_provider_xyz", api_key="test")


def test_stream_generate():
    LLMFactory.register_provider("mock", MockLLM)
    llm = LLMFactory.create("mock", api_key="test-key")
    chunks = list(llm.stream_generate("test"))
    assert chunks == ["mock ", "stream"]


def test_list_providers():
    LLMFactory.register_provider("mock", MockLLM)
    providers = LLMFactory.list_providers()
    assert "mock" in providers
