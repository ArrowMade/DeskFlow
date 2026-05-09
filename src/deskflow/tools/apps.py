"""Application control tools — open, close, list running apps."""

from __future__ import annotations

import asyncio

from .base import BaseTool, RiskLevel, ToolResult


class OpenAppTool(BaseTool):
    name = "open_app"
    description = "Open (launch) a macOS application by name."
    risk_level = RiskLevel.SAFE

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Name of the app to open (e.g., 'Safari', 'Finder', 'Terminal').",
                },
            },
            "required": ["app_name"],
        }

    async def execute(self, app_name: str) -> ToolResult:
        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", f'tell application "{app_name}" to activate',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            return ToolResult(
                output=f"Failed to open {app_name}: {stderr.decode(errors='replace')}",
                success=False,
            )
        return ToolResult(output=f"Opened {app_name}")


class CloseAppTool(BaseTool):
    name = "close_app"
    description = "Close (quit) a macOS application by name."
    risk_level = RiskLevel.RISKY

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Name of the app to close.",
                },
            },
            "required": ["app_name"],
        }

    async def execute(self, app_name: str) -> ToolResult:
        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", f'tell application "{app_name}" to quit',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            return ToolResult(
                output=f"Failed to close {app_name}: {stderr.decode(errors='replace')}",
                success=False,
            )
        return ToolResult(output=f"Closed {app_name}")


class ListRunningAppsTool(BaseTool):
    name = "list_running_apps"
    description = "List all currently running macOS applications."
    risk_level = RiskLevel.SAFE

    def get_input_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self) -> ToolResult:
        script = '''
            tell application "System Events"
                set appList to name of every application process whose visible is true
            end tell
            set text item delimiters to linefeed
            return appList as text
        '''
        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            return ToolResult(
                output=f"Error: {stderr.decode(errors='replace')}",
                success=False,
            )
        apps = stdout.decode(errors="replace").strip()
        return ToolResult(output=f"Running applications:\n{apps}")
