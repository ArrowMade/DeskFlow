"""Fast text generation tool using deepseek-chat."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from .base import BaseTool, RiskLevel, ToolResult

if TYPE_CHECKING:
    from ..agent.client import DeepSeekClient


class GenerateTextTool(BaseTool):
    name = "generate_text"
    description = (
        "Generate text content using a fast LLM (deepseek-chat). "
        "Use this for writing documents, brainstorming, drafting emails, "
        "composing notes, generating code, creating lists, etc. "
        "This is MUCH faster than thinking through the text yourself. "
        "Returns the generated text — you can then use type_text to input it."
    )
    risk_level = RiskLevel.SAFE

    def __init__(self, client: "DeepSeekClient | None" = None) -> None:
        self._client = client

    def set_client(self, client: "DeepSeekClient") -> None:
        self._client = client

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "What to write. Be specific about format, length, and style. "
                        "Example: 'Write a 5-point brainstorm about SaaS ideas, "
                        "formatted with numbered list and bullet sub-points.'"
                    ),
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Max length of generated text in tokens (default 2048).",
                },
            },
            "required": ["prompt"],
        }

    async def execute(self, prompt: str, max_tokens: int = 2048) -> ToolResult:
        if self._client is None:
            return ToolResult(
                output="GenerateTextTool has no client configured.",
                success=False,
            )

        try:
            text = await asyncio.to_thread(
                self._client.generate_text, prompt, max_tokens
            )
            return ToolResult(output=text)
        except Exception as e:
            return ToolResult(output=f"Text generation failed: {e}", success=False)
