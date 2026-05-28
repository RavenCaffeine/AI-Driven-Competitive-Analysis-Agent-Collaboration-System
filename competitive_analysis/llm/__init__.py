"""LLM abstraction layer - supports multiple providers via factory pattern."""

from .base import BaseLLM
from .factory import LLMFactory

__all__ = ["BaseLLM", "LLMFactory"]
