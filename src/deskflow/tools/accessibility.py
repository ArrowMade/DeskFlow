"""Accessibility tool — read UI element tree from screen using macOS Accessibility APIs."""

from __future__ import annotations

import asyncio
import json

from .base import BaseTool, RiskLevel, ToolResult


class GetUIElementsTool(BaseTool):
    name = "get_ui_elements"
    description = (
        "Get the UI element tree of the frontmost application using macOS Accessibility APIs. "
        "Returns buttons, text fields, labels, menus, checkboxes, etc. with their positions, "
        "sizes, and properties. This is how you 'see' the screen without a vision model. "
        "Use this before clicking to know WHERE to click."
    )
    risk_level = RiskLevel.SAFE

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "App name to inspect. If omitted, uses the frontmost app.",
                },
                "max_depth": {
                    "type": "integer",
                    "description": "How deep to traverse the UI tree. Defaults to 5. Use lower for speed, higher for detail.",
                },
                "role_filter": {
                    "type": "string",
                    "description": "Only return elements matching this role (e.g., 'AXButton', 'AXTextField', 'AXStaticText'). Leave empty for all.",
                },
            },
        }

    async def execute(
        self, app_name: str = "", max_depth: int = 5, role_filter: str = ""
    ) -> ToolResult:
        filter_arg = f'"{role_filter}"' if role_filter else '""'
        app_arg = f'"{app_name}"' if app_name else '""'

        python_script = f'''
import json, sys, subprocess

try:
    import Quartz
    from AppKit import NSWorkspace, NSRunningApplication
    import ApplicationServices as AS
except ImportError:
    print(json.dumps({{"error": "PyObjC not installed. Run: pip install pyobjc-framework-Quartz pyobjc-framework-ApplicationServices"}}))
    sys.exit(0)

def get_frontmost_app():
    ws = NSWorkspace.sharedWorkspace()
    app = ws.frontmostApplication()
    return app.processIdentifier() if app else None

def get_app_by_name(name):
    ws = NSWorkspace.sharedWorkspace()
    for app in ws.runningApplications():
        if app.localizedName() and name.lower() in app.localizedName().lower():
            return app.processIdentifier()
    return None

def get_element_info(element, depth=0, max_depth={max_depth}, role_filter={filter_arg}):
    if depth > max_depth:
        return None
    try:
        err, role = AS.AXUIElementCopyAttributeValue(element, "AXRole", None)
        if err != 0:
            return None
        role = str(role) if role else ""

        err, title = AS.AXUIElementCopyAttributeValue(element, "AXTitle", None)
        title = str(title) if err == 0 and title else ""

        err, desc = AS.AXUIElementCopyAttributeValue(element, "AXDescription", None)
        desc = str(desc) if err == 0 and desc else ""

        err, value = AS.AXUIElementCopyAttributeValue(element, "AXValue", None)
        value_str = str(value)[:200] if err == 0 and value else ""

        err, pos = AS.AXUIElementCopyAttributeValue(element, "AXPosition", None)
        x, y = 0, 0
        if err == 0 and pos:
            p = Quartz.CGPointMake(0, 0)
            success, p = Quartz.AXValueGetValue(pos, Quartz.kAXValueTypeCGPoint, None)
            if success:
                x, y = int(p.x), int(p.y)

        err, size = AS.AXUIElementCopyAttributeValue(element, "AXSize", None)
        w, h = 0, 0
        if err == 0 and size:
            s = Quartz.CGSizeMake(0, 0)
            success, s = Quartz.AXValueGetValue(size, Quartz.kAXValueTypeCGSize, None)
            if success:
                w, h = int(s.width), int(s.height)

        err, enabled = AS.AXUIElementCopyAttributeValue(element, "AXEnabled", None)
        is_enabled = bool(enabled) if err == 0 else True

        info = {{"role": role, "title": title, "description": desc, "x": x, "y": y, "w": w, "h": h}}
        if value_str:
            info["value"] = value_str
        if not is_enabled:
            info["enabled"] = False

        # Apply role filter
        if role_filter and role != role_filter:
            pass_self = False
        else:
            pass_self = True

        # Get children
        children = []
        err, child_elements = AS.AXUIElementCopyAttributeValue(element, "AXChildren", None)
        if err == 0 and child_elements:
            for child in child_elements[:50]:  # Limit children
                child_info = get_element_info(child, depth + 1, max_depth, role_filter)
                if child_info:
                    children.append(child_info)

        if children:
            info["children"] = children

        if pass_self or children:
            return info
        return None

    except Exception as e:
        return None

app_name = {app_arg}
if app_name:
    pid = get_app_by_name(app_name)
else:
    pid = get_frontmost_app()

if pid is None:
    print(json.dumps({{"error": "Could not find app"}}))
    sys.exit(0)

app_ref = AS.AXUIElementCreateApplication(pid)
err, windows = AS.AXUIElementCopyAttributeValue(app_ref, "AXWindows", None)

results = []
if err == 0 and windows:
    for win in windows[:5]:
        win_info = get_element_info(win, 0, {max_depth}, {filter_arg})
        if win_info:
            results.append(win_info)

if not results:
    # Try the app element itself
    app_info = get_element_info(app_ref, 0, {max_depth}, {filter_arg})
    if app_info:
        results.append(app_info)

print(json.dumps(results, ensure_ascii=False, indent=2)[:15000])
'''

        proc = await asyncio.create_subprocess_exec(
            "python3", "-c", python_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)

        output = stdout.decode(errors="replace").strip()
        if not output:
            err_msg = stderr.decode(errors="replace").strip()
            if "not authorized" in err_msg.lower() or "1002" in err_msg:
                return ToolResult(
                    output=(
                        "Accessibility access not granted. Go to: System Settings > "
                        "Privacy & Security > Accessibility > Enable your terminal app."
                    ),
                    success=False,
                )
            return ToolResult(
                output=f"Failed to get UI elements. Error: {err_msg[:500]}",
                success=False,
            )

        try:
            data = json.loads(output)
            if isinstance(data, dict) and "error" in data:
                return ToolResult(output=data["error"], success=False)
        except json.JSONDecodeError:
            pass

        return ToolResult(output=output)
