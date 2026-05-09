"""Keyboard and mouse simulation tools."""

from __future__ import annotations

import asyncio
import time

import Quartz

from .base import BaseTool, RiskLevel, ToolResult


# ─── Quartz helpers (no subprocess, no osascript) ───

def _post(event):
    """Post a Quartz CG event to the HID event tap."""
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)


def _mouse_event(event_type, point, button=Quartz.kCGMouseButtonLeft):
    return Quartz.CGEventCreateMouseEvent(None, event_type, point, button)


def _move_to(x: float, y: float):
    """Instantly move the cursor to (x, y)."""
    point = Quartz.CGPointMake(x, y)
    _post(_mouse_event(Quartz.kCGEventMouseMoved, point))


def _smooth_move(x: float, y: float, duration: float = 0.3, steps: int = 0):
    """Smoothly move cursor from current position to (x, y)."""
    # Get current cursor position
    event = Quartz.CGEventCreate(None)
    current = Quartz.CGEventGetLocation(event)
    sx, sy = current.x, current.y

    if steps <= 0:
        steps = max(10, int(duration * 120))  # ~120 fps worth of points
    dt = duration / steps

    for i in range(1, steps + 1):
        t = i / steps
        # Ease-in-out cubic for smooth feel
        t = t * t * (3 - 2 * t)
        nx = sx + (x - sx) * t
        ny = sy + (y - sy) * t
        _move_to(nx, ny)
        time.sleep(dt)


class MoveCursorTool(BaseTool):
    name = "move_cursor"
    description = (
        "Move the mouse cursor to specific screen coordinates. "
        "Optionally move smoothly with animation for a natural feel."
    )
    risk_level = RiskLevel.SAFE

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "Target X coordinate."},
                "y": {"type": "integer", "description": "Target Y coordinate."},
                "smooth": {
                    "type": "boolean",
                    "description": "Smooth animated movement (default true).",
                },
                "duration": {
                    "type": "number",
                    "description": "Duration of smooth move in seconds (default 0.25).",
                },
            },
            "required": ["x", "y"],
        }

    async def execute(
        self, x: int, y: int, smooth: bool = True, duration: float = 0.25
    ) -> ToolResult:
        if smooth:
            await asyncio.to_thread(_smooth_move, x, y, duration)
        else:
            _move_to(x, y)
        return ToolResult(output=f"Moved cursor to ({x}, {y})")


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
        def _do():
            if x is not None and y is not None:
                _move_to(x, y)
                time.sleep(0.02)
            scroll_event = Quartz.CGEventCreateScrollWheelEvent(
                None, Quartz.kCGScrollEventUnitLine, 2, -amount, horizontal
            )
            _post(scroll_event)

        await asyncio.to_thread(_do)

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
                    "description": "Duration of drag in seconds. Defaults to 0.4.",
                },
            },
            "required": ["from_x", "from_y", "to_x", "to_y"],
        }

    async def execute(
        self, from_x: int, from_y: int, to_x: int, to_y: int, duration: float = 0.4
    ) -> ToolResult:
        def _do():
            steps = max(15, int(duration * 120))
            start = Quartz.CGPointMake(from_x, from_y)
            end = Quartz.CGPointMake(to_x, to_y)

            # Move to start
            _post(_mouse_event(Quartz.kCGEventMouseMoved, start))
            time.sleep(0.02)

            # Mouse down
            _post(_mouse_event(Quartz.kCGEventLeftMouseDown, start))
            time.sleep(0.02)

            # Smooth drag
            dt = duration / steps
            for i in range(1, steps + 1):
                t = i / steps
                t = t * t * (3 - 2 * t)  # ease-in-out
                x = from_x + (to_x - from_x) * t
                y = from_y + (to_y - from_y) * t
                point = Quartz.CGPointMake(x, y)
                _post(_mouse_event(Quartz.kCGEventLeftMouseDragged, point))
                time.sleep(dt)

            # Mouse up
            _post(_mouse_event(Quartz.kCGEventLeftMouseUp, end))

        await asyncio.to_thread(_do)
        return ToolResult(output=f"Dragged from ({from_x},{from_y}) to ({to_x},{to_y})")


class TypeTextTool(BaseTool):
    name = "type_text"
    description = (
        "Type text into the focused application. For multi-line or formatted text, "
        "uses clipboard+paste to preserve line breaks and formatting. "
        "For short single-line text, uses keyboard simulation. "
        "Supports newlines (\\n) in the text for multi-line content."
    )
    risk_level = RiskLevel.RISKY

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": (
                        "Text to type. Use \\n for line breaks. "
                        "Example: 'Line 1\\nLine 2\\nLine 3'"
                    ),
                },
                "method": {
                    "type": "string",
                    "enum": ["auto", "paste", "keystroke"],
                    "description": (
                        "Typing method. 'auto' (default) picks the best method: "
                        "paste for multi-line/long text, keystroke for short text. "
                        "'paste' always uses clipboard+paste. "
                        "'keystroke' always uses key-by-key simulation."
                    ),
                },
            },
            "required": ["text"],
        }

    async def execute(self, text: str, method: str = "auto") -> ToolResult:
        has_newlines = "\n" in text
        is_long = len(text) > 50

        if method == "auto":
            use_paste = has_newlines or is_long
        elif method == "paste":
            use_paste = True
        else:
            use_paste = False

        if use_paste:
            return await self._paste_text(text)
        else:
            return await self._keystroke_text(text)

    async def _paste_text(self, text: str) -> ToolResult:
        """Use clipboard + Cmd+V to paste formatted text with line breaks."""
        # Save current clipboard
        save_proc = await asyncio.create_subprocess_exec(
            "pbpaste",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        old_clipboard, _ = await save_proc.communicate()

        # Set new clipboard content
        set_proc = await asyncio.create_subprocess_exec(
            "pbcopy",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await set_proc.communicate(input=text.encode("utf-8"))

        await asyncio.sleep(0.05)

        # Paste with Cmd+V using Quartz key event
        def _paste():
            # 'v' key code = 9
            v_down = Quartz.CGEventCreateKeyboardEvent(None, 9, True)
            v_up = Quartz.CGEventCreateKeyboardEvent(None, 9, False)
            Quartz.CGEventSetFlags(v_down, Quartz.kCGEventFlagMaskCommand)
            Quartz.CGEventSetFlags(v_up, Quartz.kCGEventFlagMaskCommand)
            _post(v_down)
            time.sleep(0.02)
            _post(v_up)

        await asyncio.to_thread(_paste)
        await asyncio.sleep(0.15)

        # Restore old clipboard
        restore_proc = await asyncio.create_subprocess_exec(
            "pbcopy",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await restore_proc.communicate(input=old_clipboard)

        line_count = text.count("\n") + 1
        return ToolResult(
            output=f"Pasted {len(text)} characters ({line_count} lines)"
        )

    async def _keystroke_text(self, text: str) -> ToolResult:
        """Use AppleScript keystroke for short, single-line text."""
        text_esc = text.replace("\\", "\\\\").replace('"', '\\"')

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
        # Common character keys for Quartz-native key press
        "a": 0, "b": 11, "c": 8, "d": 2, "e": 14, "f": 3, "g": 5,
        "h": 4, "i": 34, "j": 38, "k": 40, "l": 37, "m": 46,
        "n": 45, "o": 31, "p": 35, "q": 12, "r": 15, "s": 1,
        "t": 17, "u": 32, "v": 9, "w": 13, "x": 7, "y": 16, "z": 6,
        "0": 29, "1": 18, "2": 19, "3": 20, "4": 21,
        "5": 23, "6": 22, "7": 26, "8": 28, "9": 25,
    }

    MODIFIER_FLAGS = {
        "command": Quartz.kCGEventFlagMaskCommand,
        "cmd": Quartz.kCGEventFlagMaskCommand,
        "control": Quartz.kCGEventFlagMaskControl,
        "ctrl": Quartz.kCGEventFlagMaskControl,
        "option": Quartz.kCGEventFlagMaskAlternate,
        "alt": Quartz.kCGEventFlagMaskAlternate,
        "shift": Quartz.kCGEventFlagMaskShift,
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
        main_key = parts[-1]
        modifier_parts = parts[:-1]

        # Check if we can do it natively via Quartz
        if main_key in self.KEY_CODES:
            return await self._press_quartz(main_key, modifier_parts)

        # Fallback to AppleScript for unknown keys
        return await self._press_applescript(main_key, modifier_parts)

    async def _press_quartz(self, main_key: str, modifiers: list[str]) -> ToolResult:
        """Press key using Quartz — fast, no subprocess."""
        code = self.KEY_CODES[main_key]

        # Combine modifier flags
        flags = 0
        for mod in modifiers:
            flag = self.MODIFIER_FLAGS.get(mod, 0)
            flags |= flag

        def _do():
            down = Quartz.CGEventCreateKeyboardEvent(None, code, True)
            up = Quartz.CGEventCreateKeyboardEvent(None, code, False)
            if flags:
                Quartz.CGEventSetFlags(down, flags)
                Quartz.CGEventSetFlags(up, flags)
            _post(down)
            time.sleep(0.01)
            _post(up)

        await asyncio.to_thread(_do)
        key_str = "+".join(modifiers + [main_key]) if modifiers else main_key
        return ToolResult(output=f"Pressed {key_str}")

    async def _press_applescript(self, main_key: str, modifiers: list[str]) -> ToolResult:
        """Fallback for keys not in our code map."""
        modifier_strs = []
        for p in modifiers:
            if p in ("command", "cmd"):
                modifier_strs.append("command down")
            elif p in ("control", "ctrl"):
                modifier_strs.append("control down")
            elif p in ("option", "alt"):
                modifier_strs.append("option down")
            elif p == "shift":
                modifier_strs.append("shift down")

        modifier_str = ", ".join(modifier_strs)

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
        key_str = "+".join(modifiers + [main_key]) if modifiers else main_key
        return ToolResult(output=f"Pressed {key_str}")


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
        click_count = 2 if double_click else 1

        def _do():
            point = Quartz.CGPointMake(x, y)

            if button == "right":
                down_type = Quartz.kCGEventRightMouseDown
                up_type = Quartz.kCGEventRightMouseUp
                btn = Quartz.kCGMouseButtonRight
            else:
                down_type = Quartz.kCGEventLeftMouseDown
                up_type = Quartz.kCGEventLeftMouseUp
                btn = Quartz.kCGMouseButtonLeft

            # Move to position
            _post(_mouse_event(Quartz.kCGEventMouseMoved, point))
            time.sleep(0.02)

            # Click(s)
            for i in range(click_count):
                down_event = _mouse_event(down_type, point, btn)
                up_event = _mouse_event(up_type, point, btn)
                # Set click count for double-click detection
                if double_click:
                    Quartz.CGEventSetIntegerValueField(
                        down_event, Quartz.kCGMouseEventClickState, i + 1
                    )
                    Quartz.CGEventSetIntegerValueField(
                        up_event, Quartz.kCGMouseEventClickState, i + 1
                    )
                _post(down_event)
                time.sleep(0.01)
                _post(up_event)
                if i < click_count - 1:
                    time.sleep(0.02)

        await asyncio.to_thread(_do)

        action = "Double-clicked" if double_click else "Clicked"
        return ToolResult(output=f"{action} at ({x}, {y})")
