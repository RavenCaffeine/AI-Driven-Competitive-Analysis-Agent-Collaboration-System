"""Claude (Anthropic) LLM provider."""

from typing import Dict, Iterator, List
from .base import BaseLLM


class ClaudeLLM(BaseLLM):
    """Anthropic Claude LLM. Requires `anthropic` SDK."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514", **kwargs):
        super().__init__(api_key, model, **kwargs)
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)

    def generate(self, prompt: str, **kwargs) -> str:
        params = {**self.config, **kwargs}
        max_tokens = params.pop("max_tokens", 4096)
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            **params
        )
        self.last_usage = {"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens}
        return resp.content[0].text

    def stream_generate(self, prompt: str, **kwargs) -> Iterator[str]:
        params = {**self.config, **kwargs}
        max_tokens = params.pop("max_tokens", 4096)
        with self.client.messages.stream(
            model=self.model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}], **params
        ) as stream:
            for text in stream.text_stream:
                yield text
