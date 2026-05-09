"""AppleScript execution tool."""

from __future__ import annotations

import asyncio

from .base import BaseTool, RiskLevel, ToolResult


class AppleScriptTool(BaseTool):
    name = "applescript"
    description = (
        "Execute an AppleScript to control macOS applications and system features. "
        "Use this for automating apps like Finder, Safari, Mail, Calendar, Messages, "
        "and any other scriptable macOS application."
    )
    risk_level = RiskLevel.RISKY

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "script": {
                    "type": "string",
                    "description": "The AppleScript code to execute.",
                },
            },
            "required": ["script"],
        }

    async def execute(self, script: str) -> ToolResult:
        try:
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=30
            )

            if proc.returncode != 0:
                error = stderr.decode(errors="replace").strip()
                return ToolResult(
                    output=f"AppleScript error: {error}",
                    success=False,
                )

            output = stdout.decode(errors="replace").strip()
            return ToolResult(output=output or "(script executed successfully)")

        except asyncio.TimeoutError:
            return ToolResult(output="AppleScript timed out after 30s", success=False)
