"""Python code execution tool."""

from __future__ import annotations

import asyncio
import tempfile
import os

from .base import BaseTool, RiskLevel, ToolResult


class RunPythonTool(BaseTool):
    name = "run_python"
    description = (
        "Execute a Python code snippet and return the output. "
        "Useful for data processing, calculations, file manipulation, "
        "and any task that benefits from Python scripting."
    )
    risk_level = RiskLevel.RISKY

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds. Defaults to 30.",
                },
            },
            "required": ["code"],
        }

    async def execute(self, code: str, timeout: int = 30) -> ToolResult:
        # Write code to temp file and execute
        fd, filepath = tempfile.mkstemp(suffix=".py")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(code)

            proc = await asyncio.create_subprocess_exec(
                "python3", filepath,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
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

            if len(output) > 10000:
                output = output[:10000] + f"\n... (truncated)"

            return ToolResult(
                output=output,
                success=proc.returncode == 0,
            )
        except asyncio.TimeoutError:
            return ToolResult(output=f"Python execution timed out after {timeout}s", success=False)
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)
