"""
Configuration management - loads from .env and config files.

Supports runtime LLM provider switching and per-agent model assignment.
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    provider: str = "deepseek"
    model: Optional[str] = None
    api_key: str = ""
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096


@dataclass
class ToolConfig:
    """External tool configuration."""
    tavily_api_key: str = ""
    serper_api_key: str = ""
    jina_api_key: str = ""


@dataclass
class MemoryConfig:
    """Memory system configuration (inspired by deerflow)."""
    enabled: bool = True
    storage_path: str = ""
    max_facts: int = 100
    fact_confidence_threshold: float = 0.7
    debounce_seconds: int = 30


@dataclass
class AppConfig:
    """Top-level application configuration."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    tools: ToolConfig = field(default_factory=ToolConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    output_dir: str = "./outputs"
    max_iterations: int = 5
    max_qa_retries: int = 2
    auto_approve: bool = True
    log_level: str = "INFO"

    # Per-agent LLM overrides: {"collector": LLMConfig(...), "analyst": LLMConfig(...)}
    agent_llm_overrides: Dict[str, LLMConfig] = field(default_factory=dict)


def load_config(env_path: Optional[str] = None) -> AppConfig:
    """
    Load configuration from environment variables.

    Priority: explicit env_path > .env in CWD > system environment.
    """
    if env_path:
        load_dotenv(env_path)
    else:
        load_dotenv()

    llm_config = LLMConfig(
        provider=os.getenv("LLM_PROVIDER", "deepseek"),
        model=os.getenv("LLM_MODEL", None),
        api_key=os.getenv("LLM_API_KEY", os.getenv("DEEPSEEK_API_KEY", "")),
        base_url=os.getenv("LLM_BASE_URL", None),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
    )

    tool_config = ToolConfig(
        tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
        serper_api_key=os.getenv("SERPER_API_KEY", ""),
        jina_api_key=os.getenv("JINA_API_KEY", ""),
    )

    memory_config = MemoryConfig(
        enabled=os.getenv("MEMORY_ENABLED", "true").lower() == "true",
        storage_path=os.getenv("MEMORY_STORAGE_PATH", ""),
        max_facts=int(os.getenv("MEMORY_MAX_FACTS", "100")),
    )

    return AppConfig(
        llm=llm_config,
        tools=tool_config,
        memory=memory_config,
        output_dir=os.getenv("OUTPUT_DIR", "./outputs"),
        max_iterations=int(os.getenv("MAX_ITERATIONS", "5")),
        max_qa_retries=int(os.getenv("MAX_QA_RETRIES", "2")),
        auto_approve=os.getenv("AUTO_APPROVE", "true").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
