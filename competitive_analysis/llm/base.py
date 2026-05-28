"""
LLM Base Class - Abstract interface for all LLM providers.

Inspired by SDYJ_Multi_Agents LLM abstraction layer.
Supports synchronous and streaming generation with token usage tracking.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, Optional


class BaseLLM(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, api_key: str, model: str = "default", **kwargs):
        self.api_key = api_key
        self.model = model
        self.config = kwargs
        self.last_usage: Optional[Dict[str, Any]] = None

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from a prompt. Returns full response string."""
        pass

    @abstractmethod
    def stream_generate(self, prompt: str, **kwargs) -> Iterator[str]:
        """Stream generate text chunk by chunk."""
        pass

    def chat(self, messages: list[Dict[str, str]], **kwargs) -> str:
        """Chat-style generation with message list. Default: convert to single prompt."""
        combined = "\n".join(f"[{m['role']}]: {m['content']}" for m in messages)
        return self.generate(combined, **kwargs)

    def get_usage(self) -> Optional[Dict[str, Any]]:
        """Return token usage from the last call, if available."""
        return self.last_usage

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model})"
