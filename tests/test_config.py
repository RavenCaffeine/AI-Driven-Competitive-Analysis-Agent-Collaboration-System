"""Tests for configuration management."""

import os
from competitive_analysis.utils.config import load_config, AppConfig, LLMConfig


def test_load_default_config():
    config = load_config()
    assert isinstance(config, AppConfig)
    assert config.max_iterations == 5
    assert config.max_qa_retries == 2


def test_llm_config_defaults():
    config = LLMConfig()
    assert config.provider == "deepseek"
    assert config.temperature == 0.7
    assert config.max_tokens == 4096


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("MAX_QA_RETRIES", "3")

    config = load_config()
    assert config.llm.provider == "openai"
    assert config.llm.model == "gpt-4o"
    assert config.max_qa_retries == 3
