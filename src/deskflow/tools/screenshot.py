"""Screenshot tool — capture screen for visual context."""

from __future__ import annotations

import asyncio
import base64
import os
import tempfile
import time

from .base import BaseTool, RiskLevel, ToolResult


class ScreenshotTool(BaseTool):
    name = "screenshot"
    description = (
        "Take a screenshot of the screen. Returns the image so you can visually "
        "analyze what's on screen. Useful for understanding UI state, reading text "
        "from windows, or verifying that actions worked."
    )
    risk_level = RiskLevel.SAFE

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "enum": ["full", "window"],
                    "description": "What to capture. 'full' = entire screen, 'window' = frontmost window. Defaults to 'full'.",
                },
                "delay": {
                    "type": "integer",
                    "description": "Delay in seconds before capturing. Defaults to 1.",
                },
            },
        }

    async def execute(self, region: str = "full", delay: int = 1) -> ToolResult:
        # Small delay to let UI settle
        if delay > 0:
            await asyncio.sleep(delay)

        fd, filepath = tempfile.mkstemp(suffix=".png")
        os.close(fd)

        try:
            # -x = no sound, -C = capture cursor
            if region == "window":
                # -w captures the frontmost window (non-interactive with -l)
                # Use -w with a slight workaround
                cmd = ["screencapture", "-x", "-w", filepath]
            else:
                cmd = ["screencapture", "-x", filepath]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)

            if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
                # Fallback: try without -w flag
                cmd_fallback = ["screencapture", "-x", filepath]
                proc2 = await asyncio.create_subprocess_exec(
                    *cmd_fallback,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await asyncio.wait_for(proc2.communicate(), timeout=10)

            if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
                return ToolResult(
                    output=(
                        "Screenshot failed. You may need to grant screen recording "
                        "permission: System Settings > Privacy & Security > Screen Recording > "
                        "allow your terminal app."
                    ),
                    success=False,
                )

            with open(filepath, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()

            size_kb = os.path.getsize(filepath) / 1024
            return ToolResult(
                output=f"Screenshot captured ({region}, {size_kb:.0f} KB)",
                image_base64=image_data,
            )
        except asyncio.TimeoutError:
            return ToolResult(output="Screenshot timed out", success=False)
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)
