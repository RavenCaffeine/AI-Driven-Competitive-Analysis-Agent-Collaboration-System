"""
LLM Factory - Provider-agnostic LLM instantiation with lazy loading.

Supports runtime switching between DeepSeek, OpenAI, Claude, Gemini, etc.
New providers can be registered without modifying existing code.
"""

from typing import Optional
from .base import BaseLLM


class LLMFactory:
    """Factory for creating LLM instances. Supports lazy loading and runtime registration."""

    _providers: dict[str, type] = {}

    @classmethod
    def register_provider(cls, name: str, provider_class: type) -> None:
        """Register a new LLM provider class."""
        cls._providers[name.lower()] = provider_class

    @classmethod
    def create(
        cls,
        provider: str,
        api_key: str,
        model: Optional[str] = None,
        **kwargs
    ) -> BaseLLM:
        """
        Create an LLM instance by provider name.

        Args:
            provider: Provider name ('deepseek', 'openai', 'claude', 'gemini')
            api_key: API key for the provider
            model: Optional model override. Uses provider default if omitted.
            **kwargs: Extra config (temperature, max_tokens, base_url, etc.)

        Raises:
            ValueError: If provider is unknown and cannot be lazy-loaded.
        """
        provider = provider.lower()
        if provider not in cls._providers:
            cls._lazy_load(provider)
        if provider not in cls._providers:
            available = ", ".join(cls._providers.keys()) or "(none)"
            raise ValueError(f"Unknown LLM provider '{provider}'. Available: {available}")

        llm_cls = cls._providers[provider]
        if model:
            return llm_cls(api_key=api_key, model=model, **kwargs)
        return llm_cls(api_key=api_key, **kwargs)

    @classmethod
    def _lazy_load(cls, provider: str) -> None:
        """Attempt to import and register a built-in provider."""
        try:
            if provider == "deepseek":
                from .deepseek_llm import DeepSeekLLM
                cls.register_provider("deepseek", DeepSeekLLM)
            elif provider == "openai":
                from .openai_llm import OpenAILLM
                cls.register_provider("openai", OpenAILLM)
            elif provider == "claude":
                from .claude_llm import ClaudeLLM
                cls.register_provider("claude", ClaudeLLM)
            elif provider == "gemini":
                from .gemini_llm import GeminiLLM
                cls.register_provider("gemini", GeminiLLM)
        except ImportError:
            pass  # Provider SDK not installed

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names."""
        return list(cls._providers.keys())
