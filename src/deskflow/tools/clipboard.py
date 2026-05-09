"""Clipboard tools — get and set clipboard content."""

from __future__ import annotations

import asyncio

from .base import BaseTool, RiskLevel, ToolResult


class GetClipboardTool(BaseTool):
    name = "get_clipboard"
    description = "Get the current contents of the macOS clipboard (pasteboard)."
    risk_level = RiskLevel.SAFE

    def get_input_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self) -> ToolResult:
        proc = await asyncio.create_subprocess_exec(
            "pbpaste",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        content = stdout.decode(errors="replace")
        if not content:
            return ToolResult(output="(clipboard is empty)")
        if len(content) > 5000:
            content = content[:5000] + f"\n... (truncated, {len(content)} chars total)"
        return ToolResult(output=content)


class SetClipboardTool(BaseTool):
    name = "set_clipboard"
    description = "Set the macOS clipboard content to the given text."
    risk_level = RiskLevel.RISKY

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to copy to the clipboard.",
                },
            },
            "required": ["text"],
        }

    async def execute(self, text: str) -> ToolResult:
        proc = await asyncio.create_subprocess_exec(
            "pbcopy",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate(input=text.encode())
        return ToolResult(output=f"Copied {len(text)} chars to clipboard")
