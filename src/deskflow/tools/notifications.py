"""macOS notification tool."""

from __future__ import annotations

import asyncio

from .base import BaseTool, RiskLevel, ToolResult


class SendNotificationTool(BaseTool):
    name = "send_notification"
    description = "Send a macOS notification with a title and message."
    risk_level = RiskLevel.SAFE

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Notification title.",
                },
                "message": {
                    "type": "string",
                    "description": "Notification message body.",
                },
                "sound": {
                    "type": "boolean",
                    "description": "Play a sound. Defaults to true.",
                },
            },
            "required": ["title", "message"],
        }

    async def execute(
        self, title: str, message: str, sound: bool = True
    ) -> ToolResult:
        # Escape quotes for AppleScript
        title_esc = title.replace('"', '\\"')
        message_esc = message.replace('"', '\\"')

        sound_part = ' sound name "default"' if sound else ""
        script = f'display notification "{message_esc}" with title "{title_esc}"{sound_part}'

        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            return ToolResult(
                output=f"Notification error: {stderr.decode(errors='replace')}",
                success=False,
            )
        return ToolResult(output=f"Notification sent: {title}")
