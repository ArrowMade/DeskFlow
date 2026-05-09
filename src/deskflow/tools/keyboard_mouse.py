"""Keyboard and mouse simulation tools."""

from __future__ import annotations

import asyncio

from .base import BaseTool, RiskLevel, ToolResult


class ScrollTool(BaseTool):
    name = "scroll"
    description = (
        "Scroll the mouse wheel at a specific position or the current position. "
        "Use positive amount to scroll down, negative to scroll up."
    )
    risk_level = RiskLevel.SAFE

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "integer",
                    "description": "Scroll amount. Positive = down, negative = up. Typical: 3-5 lines.",
                },
                "x": {"type": "integer", "description": "X coordinate to scroll at. Optional."},
                "y": {"type": "integer", "description": "Y coordinate to scroll at. Optional."},
                "horizontal": {
                    "type": "integer",
                    "description": "Horizontal scroll. Positive = right, negative = left. Optional.",
                },
            },
            "required": ["amount"],
        }

    async def execute(
        self, amount: int, x: int | None = None, y: int | None = None, horizontal: int = 0
    ) -> ToolResult:
        move_cmd = ""
        if x is not None and y is not None:
            move_cmd = f"""
point = Quartz.CGPointMake({x}, {y})
Quartz.CGEventPost(Quartz.kCGHIDEventTap, Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventMouseMoved, point, Quartz.kCGMouseButtonLeft))
import time; time.sleep(0.05)
"""

        script = f'''
do shell script "python3 -c \\"
import Quartz
{move_cmd}
scroll_event = Quartz.CGEventCreateScrollWheelEvent(None, Quartz.kCGScrollEventUnitLine, 2, {-amount}, {horizontal})
Quartz.CGEventPost(Quartz.kCGHIDEventTap, scroll_event)
\\""
'''
        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            return ToolResult(
                output=f"Scroll failed: {stderr.decode(errors='replace')}", success=False
            )

        direction = "down" if amount > 0 else "up"
        pos = f" at ({x},{y})" if x is not None else ""
        return ToolResult(output=f"Scrolled {direction} {abs(amount)} lines{pos}")


class DragTool(BaseTool):
    name = "drag"
    description = (
        "Drag from one screen coordinate to another. Useful for moving files, "
        "resizing windows, selecting text, drag-and-drop operations."
    )
    risk_level = RiskLevel.RISKY

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "from_x": {"type": "integer", "description": "Start X coordinate."},
                "from_y": {"type": "integer", "description": "Start Y coordinate."},
                "to_x": {"type": "integer", "description": "End X coordinate."},
                "to_y": {"type": "integer", "description": "End Y coordinate."},
                "duration": {
                    "type": "number",
                    "description": "Duration of drag in seconds. Defaults to 0.5.",
                },
            },
            "required": ["from_x", "from_y", "to_x", "to_y"],
        }

    async def execute(
        self, from_x: int, from_y: int, to_x: int, to_y: int, duration: float = 0.5
    ) -> ToolResult:
        steps = max(10, int(duration * 60))
        script = f'''
do shell script "python3 -c \\"
import Quartz, time

start = Quartz.CGPointMake({from_x}, {from_y})
end = Quartz.CGPointMake({to_x}, {to_y})
steps = {steps}

# Move to start
Quartz.CGEventPost(Quartz.kCGHIDEventTap, Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventMouseMoved, start, Quartz.kCGMouseButtonLeft))
time.sleep(0.05)

# Mouse down
Quartz.CGEventPost(Quartz.kCGHIDEventTap, Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventLeftMouseDown, start, Quartz.kCGMouseButtonLeft))
time.sleep(0.05)

# Drag
for i in range(1, steps + 1):
    t = i / steps
    x = {from_x} + ({to_x} - {from_x}) * t
    y = {from_y} + ({to_y} - {from_y}) * t
    point = Quartz.CGPointMake(x, y)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventLeftMouseDragged, point, Quartz.kCGMouseButtonLeft))
    time.sleep({duration} / steps)

# Mouse up
Quartz.CGEventPost(Quartz.kCGHIDEventTap, Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventLeftMouseUp, end, Quartz.kCGMouseButtonLeft))
\\""
'''
        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            return ToolResult(
                output=f"Drag failed: {stderr.decode(errors='replace')}", success=False
            )
        return ToolResult(output=f"Dragged from ({from_x},{from_y}) to ({to_x},{to_y})")


class TypeTextTool(BaseTool):
    name = "type_text"
    description = "Type text using keyboard simulation, as if the user typed it."
    risk_level = RiskLevel.RISKY

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to type.",
                },
                "delay": {
                    "type": "number",
                    "description": "Delay between keystrokes in seconds. Defaults to 0.02.",
                },
            },
            "required": ["text"],
        }

    async def execute(self, text: str, delay: float = 0.02) -> ToolResult:
        # Escape for AppleScript
        text_esc = text.replace("\\", "\\\\").replace('"', '\\"')
        delay_ticks = int(delay * 60)  # AppleScript delay is in ticks (1/60 second)

        script = f'''
            tell application "System Events"
                keystroke "{text_esc}"
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
                output=f"Type error: {stderr.decode(errors='replace')}",
                success=False,
            )
        return ToolResult(output=f"Typed {len(text)} characters")


class PressKeyTool(BaseTool):
    name = "press_key"
    description = (
        "Press a key or key combination (e.g., 'return', 'command+s', 'command+shift+n'). "
        "Supports modifier keys: command, control, option, shift."
    )
    risk_level = RiskLevel.RISKY

    # macOS key code mappings
    KEY_CODES = {
        "return": 36, "enter": 36, "tab": 48, "space": 49,
        "delete": 51, "backspace": 51, "escape": 53, "esc": 53,
        "up": 126, "down": 125, "left": 123, "right": 124,
        "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96,
        "f6": 97, "f7": 98, "f8": 100, "f9": 101, "f10": 109,
        "f11": 103, "f12": 111,
        "home": 115, "end": 119, "pageup": 116, "pagedown": 121,
    }

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": (
                        "Key or combination to press. Examples: 'return', 'command+s', "
                        "'command+shift+n', 'option+tab'."
                    ),
                },
            },
            "required": ["key"],
        }

    async def execute(self, key: str) -> ToolResult:
        parts = [p.strip().lower() for p in key.split("+")]

        modifiers = []
        main_key = parts[-1]
        for p in parts[:-1]:
            if p in ("command", "cmd"):
                modifiers.append("command down")
            elif p in ("control", "ctrl"):
                modifiers.append("control down")
            elif p in ("option", "alt"):
                modifiers.append("option down")
            elif p in ("shift",):
                modifiers.append("shift down")

        modifier_str = ", ".join(modifiers)

        if main_key in self.KEY_CODES:
            code = self.KEY_CODES[main_key]
            if modifier_str:
                script = f'tell application "System Events" to key code {code} using {{{modifier_str}}}'
            else:
                script = f'tell application "System Events" to key code {code}'
        else:
            if modifier_str:
                script = f'tell application "System Events" to keystroke "{main_key}" using {{{modifier_str}}}'
            else:
                script = f'tell application "System Events" to keystroke "{main_key}"'

        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            return ToolResult(
                output=f"Key press error: {stderr.decode(errors='replace')}",
                success=False,
            )
        return ToolResult(output=f"Pressed {key}")


class ClickAtTool(BaseTool):
    name = "click_at"
    description = "Click the mouse at specific screen coordinates."
    risk_level = RiskLevel.RISKY

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate."},
                "y": {"type": "integer", "description": "Y coordinate."},
                "button": {
                    "type": "string",
                    "enum": ["left", "right"],
                    "description": "Mouse button. Defaults to 'left'.",
                },
                "double_click": {
                    "type": "boolean",
                    "description": "Double-click. Defaults to false.",
                },
            },
            "required": ["x", "y"],
        }

    async def execute(
        self,
        x: int,
        y: int,
        button: str = "left",
        double_click: bool = False,
    ) -> ToolResult:
        # Use AppleScript with System Events for clicking
        click_count = 2 if double_click else 1

        # Use cliclick if available, otherwise fall back to AppleScript
        # AppleScript approach:
        script = f'''
            do shell script "python3 -c \\"
import Quartz
import time

point = Quartz.CGPointMake({x}, {y})
# Move
Quartz.CGEventPost(Quartz.kCGHIDEventTap, Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventMouseMoved, point, Quartz.kCGMouseButtonLeft))
time.sleep(0.05)
# Click
for i in range({click_count}):
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventLeftMouseDown, point, Quartz.kCGMouseButtonLeft))
    time.sleep(0.05)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventLeftMouseUp, point, Quartz.kCGMouseButtonLeft))
    time.sleep(0.05)
\\""
        '''

        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            # Fallback: try cliclick
            click_cmd = "dc" if double_click else "c"
            proc2 = await asyncio.create_subprocess_exec(
                "cliclick", f"{click_cmd}:{x},{y}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr2 = await proc2.communicate()
            if proc2.returncode != 0:
                return ToolResult(
                    output=f"Click failed. Install cliclick (`brew install cliclick`) for reliable mouse control. Error: {stderr.decode(errors='replace')}",
                    success=False,
                )

        action = "Double-clicked" if double_click else "Clicked"
        return ToolResult(output=f"{action} at ({x}, {y})")
