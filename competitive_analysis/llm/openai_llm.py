"""OpenAI LLM provider - supports GPT-4o, GPT-4, GPT-3.5 series."""

from typing import Any, Dict, Iterator, List, Optional
from openai import OpenAI
from .base import BaseLLM


class OpenAILLM(BaseLLM):
    """OpenAI LLM implementation."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.client = OpenAI(api_key=api_key)

    def generate(self, prompt: str, **kwargs) -> str:
        params = {**self.config, **kwargs}
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            **params
        )
        self.last_usage = response.usage.model_dump() if response.usage else None
        return response.choices[0].message.content or ""

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        params = {**self.config, **kwargs}
        response = self.client.chat.completions.create(
            model=self.model, messages=messages, **params
        )
        self.last_usage = response.usage.model_dump() if response.usage else None
        return response.choices[0].message.content or ""

    def stream_generate(self, prompt: str, **kwargs) -> Iterator[str]:
        params = {**self.config, **kwargs}
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            stream=True, **params
        )
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
