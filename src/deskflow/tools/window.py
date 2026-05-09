"""Window management tool — get/set window positions, sizes, focus."""

from __future__ import annotations

import asyncio
import json

from .base import BaseTool, RiskLevel, ToolResult


class GetWindowsTool(BaseTool):
    name = "get_windows"
    description = (
        "List all visible windows with their app name, title, position, and size. "
        "Use this to understand what's open on screen and where windows are located."
    )
    risk_level = RiskLevel.SAFE

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
        }

    async def execute(self) -> ToolResult:
        python_script = '''
import json, sys
try:
    import Quartz
except ImportError:
    print(json.dumps({"error": "PyObjC not installed"}))
    sys.exit(0)

windows = Quartz.CGWindowListCopyWindowInfo(
    Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
    Quartz.kCGNullWindowID,
)

results = []
for win in windows:
    owner = win.get("kCGWindowOwnerName", "")
    name = win.get("kCGWindowName", "")
    layer = win.get("kCGWindowLayer", 0)
    bounds = win.get("kCGWindowBounds", {})

    # Skip menu bar, dock, and system UI
    if layer != 0:
        continue
    if not owner or owner in ("Window Server", "Dock"):
        continue

    results.append({
        "app": owner,
        "title": name or "(untitled)",
        "x": int(bounds.get("X", 0)),
        "y": int(bounds.get("Y", 0)),
        "width": int(bounds.get("Width", 0)),
        "height": int(bounds.get("Height", 0)),
        "id": win.get("kCGWindowNumber", 0),
    })

print(json.dumps(results, indent=2))
'''
        proc = await asyncio.create_subprocess_exec(
            "python3", "-c", python_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)

        output = stdout.decode(errors="replace").strip()
        if not output:
            return ToolResult(output=f"Failed: {stderr.decode()[:500]}", success=False)
        return ToolResult(output=output)


class MoveResizeWindowTool(BaseTool):
    name = "move_resize_window"
    description = (
        "Move and/or resize a window by app name. Can set position and size. "
        "Useful for arranging windows on screen."
    )
    risk_level = RiskLevel.RISKY

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Name of the application (e.g., 'Safari', 'Finder').",
                },
                "x": {"type": "integer", "description": "New X position."},
                "y": {"type": "integer", "description": "New Y position."},
                "width": {"type": "integer", "description": "New width."},
                "height": {"type": "integer", "description": "New height."},
            },
            "required": ["app_name"],
        }

    async def execute(
        self,
        app_name: str,
        x: int | None = None,
        y: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> ToolResult:
        parts = []
        if x is not None and y is not None:
            parts.append(f'set position of window 1 to {{{x}, {y}}}')
        if width is not None and height is not None:
            parts.append(f'set size of window 1 to {{{width}, {height}}}')

        if not parts:
            return ToolResult(output="No position or size specified.", success=False)

        commands = "\n                ".join(parts)
        script = f'''
            tell application "{app_name}"
                activate
                {commands}
            end tell
        '''

        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            return ToolResult(
                output=f"Failed: {stderr.decode(errors='replace')}", success=False
            )

        changes = []
        if x is not None:
            changes.append(f"pos=({x},{y})")
        if width is not None:
            changes.append(f"size=({width}x{height})")
        return ToolResult(output=f"Window '{app_name}' updated: {', '.join(changes)}")


class FocusWindowTool(BaseTool):
    name = "focus_window"
    description = "Bring an application's window to the front and focus it."
    risk_level = RiskLevel.SAFE

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Name of the application to focus.",
                },
            },
            "required": ["app_name"],
        }

    async def execute(self, app_name: str) -> ToolResult:
        script = f'''
            tell application "{app_name}"
                activate
            end tell
        '''
        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            return ToolResult(
                output=f"Failed to focus: {stderr.decode(errors='replace')}",
                success=False,
            )
        return ToolResult(output=f"Focused '{app_name}'")
