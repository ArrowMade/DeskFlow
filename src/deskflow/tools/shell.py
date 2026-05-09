"""Shell command execution tool."""

from __future__ import annotations

import asyncio

from .base import BaseTool, RiskLevel, ToolResult


class ShellTool(BaseTool):
    name = "shell"
    description = (
        "Execute a shell command on macOS and return its output. "
        "Use this for system commands, file operations, package management, "
        "and any task that can be done via the terminal."
    )
    risk_level = RiskLevel.RISKY

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                },
                "working_directory": {
                    "type": "string",
                    "description": "Working directory for the command. Defaults to home directory.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds. Defaults to 30.",
                },
            },
            "required": ["command"],
        }

    async def execute(
        self,
        command: str,
        working_directory: str | None = None,
        timeout: int = 30,
    ) -> ToolResult:
        import os

        cwd = working_directory or os.path.expanduser("~")

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )

            output_parts = []
            if stdout:
                output_parts.append(stdout.decode(errors="replace"))
            if stderr:
                output_parts.append(f"[stderr]\n{stderr.decode(errors='replace')}")

            output = "\n".join(output_parts) if output_parts else "(no output)"

            # Truncate very long output
            if len(output) > 10000:
                output = output[:10000] + f"\n... (truncated, {len(output)} chars total)"

            return ToolResult(
                output=output,
                success=proc.returncode == 0,
                metadata={"return_code": proc.returncode},
            )
        except asyncio.TimeoutError:
            proc.kill()
            return ToolResult(
                output=f"Command timed out after {timeout}s",
                success=False,
            )
