"""Tool registry — collects tools, generates API schemas, dispatches calls."""

from __future__ import annotations

from .base import BaseTool, ToolResult


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def get_api_schemas(self) -> list[dict]:
        return [t.to_api_schema() for t in self._tools.values()]

    async def call(self, name: str, inputs: dict) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(output=f"Unknown tool: {name}", success=False)
        try:
            return await tool.execute(**inputs)
        except Exception as e:
            return ToolResult(output=f"Tool error: {e}", success=False)

    def list_tools(self) -> list[BaseTool]:
        return list(self._tools.values())


def build_default_registry(enabled_tools: list[str] | None = None, client=None) -> ToolRegistry:
    """Build a registry with all available tools, filtered by enabled list."""
    from .shell import ShellTool
    from .applescript import AppleScriptTool
    from .filesystem import (
        ReadFileTool, WriteFileTool, ListDirectoryTool,
        SearchFilesTool, MoveFileTool, DeleteFileTool,
    )
    from .apps import OpenAppTool, CloseAppTool, ListRunningAppsTool
    from .screenshot import ScreenshotTool
    from .clipboard import GetClipboardTool, SetClipboardTool
    from .notifications import SendNotificationTool
    from .browser import BrowserOpenURLTool, BrowserGetPageContentTool, BrowserTabsTool, BrowserSwitchTabTool
    from .keyboard_mouse import TypeTextTool, PressKeyTool, ClickAtTool, ScrollTool, DragTool, MoveCursorTool
    from .system import GetSystemInfoTool, SetSystemSettingTool
    from .python_exec import RunPythonTool
    from .accessibility import GetUIElementsTool
    from .ocr import OCRScreenTool
    from .window import GetWindowsTool, MoveResizeWindowTool, FocusWindowTool
    from .text_gen import GenerateTextTool

    # GenerateTextTool needs the client for fast text generation
    gen_text_tool = GenerateTextTool(client=client)

    all_tools: list[BaseTool] = [
        # Screen understanding (agent's eyes)
        GetUIElementsTool(),
        OCRScreenTool(),
        ScreenshotTool(),
        # Window management
        GetWindowsTool(),
        MoveResizeWindowTool(),
        FocusWindowTool(),
        # Input control
        ClickAtTool(),
        TypeTextTool(),
        PressKeyTool(),
        ScrollTool(),
        DragTool(),
        MoveCursorTool(),
        # App control
        OpenAppTool(),
        CloseAppTool(),
        ListRunningAppsTool(),
        # Shell & scripting
        ShellTool(),
        AppleScriptTool(),
        RunPythonTool(),
        # File operations
        ReadFileTool(),
        WriteFileTool(),
        ListDirectoryTool(),
        SearchFilesTool(),
        MoveFileTool(),
        DeleteFileTool(),
        # Browser
        BrowserOpenURLTool(),
        BrowserGetPageContentTool(),
        BrowserTabsTool(),
        BrowserSwitchTabTool(),
        # Clipboard
        GetClipboardTool(),
        SetClipboardTool(),
        # System
        GetSystemInfoTool(),
        SetSystemSettingTool(),
        # Notifications
        SendNotificationTool(),
        # Fast text generation (uses deepseek-chat)
        gen_text_tool,
    ]

    registry = ToolRegistry()
    for tool in all_tools:
        if enabled_tools is None or tool.name in enabled_tools:
            registry.register(tool)
    return registry
