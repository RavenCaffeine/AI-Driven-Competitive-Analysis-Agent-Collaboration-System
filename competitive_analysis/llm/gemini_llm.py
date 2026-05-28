"""Google Gemini LLM provider."""

from typing import Dict, Iterator
from .base import BaseLLM


class GeminiLLM(BaseLLM):
    """Google Gemini LLM. Requires `google-generativeai` SDK."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash", **kwargs):
        super().__init__(api_key, model, **kwargs)
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)

    def generate(self, prompt: str, **kwargs) -> str:
        response = self._model.generate_content(prompt)
        return response.text

    def stream_generate(self, prompt: str, **kwargs) -> Iterator[str]:
        response = self._model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text
