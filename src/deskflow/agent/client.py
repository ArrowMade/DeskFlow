"""DeepSeek API client wrapper (OpenAI-compatible)."""

from __future__ import annotations

from openai import OpenAI


class DeepSeekClient:
    def __init__(self, api_key: str, model: str = "deepseek-v4-pro") -> None:
        self._client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )
        self.model = model

    def create_message(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict],
        max_tokens: int = 4096,
    ):
        """Create a chat completion with tool support."""
        full_messages = [{"role": "system", "content": system}] + messages

        kwargs = dict(
            model=self.model,
            messages=full_messages,
            max_tokens=max_tokens,
        )
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        return self._client.chat.completions.create(**kwargs)
