"""Browser automation tools — open URLs, get content, navigate tabs.
Supports Safari, Google Chrome, Firefox, Arc, Microsoft Edge."""

from __future__ import annotations

import asyncio

from .base import BaseTool, RiskLevel, ToolResult


# Helpers shared across browser tools

SUPPORTED_BROWSERS = ["Google Chrome", "Safari", "Firefox", "Arc", "Microsoft Edge"]

CHROMIUM_BROWSERS = {"Google Chrome", "Arc", "Microsoft Edge"}


async def _run_applescript(script: str) -> tuple[bool, str]:
    """Run an AppleScript and return (success, output)."""
    proc = await asyncio.create_subprocess_exec(
        "osascript", "-e", script,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        return False, stderr.decode(errors="replace").strip()
    return True, stdout.decode(errors="replace").strip()


async def _detect_browser() -> str:
    """Detect which browser is currently running. Prefers the frontmost one.
    Does NOT launch any browser — only checks what's already running."""
    # Check if the frontmost app is a browser
    ok, front = await _run_applescript(
        'tell application "System Events" to get name of first application process whose frontmost is true'
    )
    if ok and front.strip() in SUPPORTED_BROWSERS:
        return front.strip()

    # Get all running process names once, then check against our list
    ok, all_procs = await _run_applescript(
        'tell application "System Events" to get name of every application process'
    )
    if ok:
        running = {p.strip() for p in all_procs.split(",")}
        for browser in SUPPORTED_BROWSERS:
            if browser in running:
                return browser

    # Nothing running — default to Chrome (most common), agent will launch it
    return "Google Chrome"


async def _activate_browser(browser: str) -> None:
    """Bring browser window to front. Only activates the specified browser."""
    await _run_applescript(f'tell application "{browser}" to activate')
    await asyncio.sleep(0.5)


class BrowserOpenURLTool(BaseTool):
    name = "browser_open_url"
    description = (
        "Open a URL in a specific browser and bring its window to front. "
        "Supports Safari, Google Chrome, Firefox, Arc, Edge. "
        "IMPORTANT: Always pass the 'browser' parameter when the user specifies one. "
        "Only omit it to auto-detect the currently active browser."
    )
    risk_level = RiskLevel.SAFE

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to open.",
                },
                "browser": {
                    "type": "string",
                    "enum": SUPPORTED_BROWSERS,
                    "description": (
                        "Browser to use. Pass this when the user specifies a browser. "
                        "Omit only to auto-detect the active browser."
                    ),
                },
                "new_tab": {
                    "type": "boolean",
                    "description": "Open in a new tab. Defaults to true.",
                },
            },
            "required": ["url"],
        }

    async def execute(
        self, url: str, browser: str = "", new_tab: bool = True
    ) -> ToolResult:
        if not browser:
            browser = await _detect_browser()

        # Open directly in the specified browser — do NOT use `open` command
        # which would trigger the system default browser
        if browser == "Safari":
            if new_tab:
                script = f'''
                    tell application "Safari"
                        activate
                        if (count of windows) is 0 then
                            make new document with properties {{URL:"{url}"}}
                        else
                            tell window 1
                                set current tab to (make new tab with properties {{URL:"{url}"}})
                            end tell
                        end if
                    end tell
                '''
            else:
                script = f'''
                    tell application "Safari"
                        activate
                        if (count of windows) is 0 then
                            make new document with properties {{URL:"{url}"}}
                        else
                            set URL of current tab of front window to "{url}"
                        end if
                    end tell
                '''
        elif browser in CHROMIUM_BROWSERS:
            if new_tab:
                script = f'''
                    tell application "{browser}"
                        activate
                        if (count of windows) is 0 then
                            make new window
                            delay 0.5
                        end if
                        tell window 1
                            make new tab with properties {{URL:"{url}"}}
                        end tell
                    end tell
                '''
            else:
                script = f'''
                    tell application "{browser}"
                        activate
                        if (count of windows) is 0 then
                            make new window
                            delay 0.5
                        end if
                        set URL of active tab of front window to "{url}"
                    end tell
                '''
        elif browser == "Firefox":
            # Firefox: use open -a to target it specifically (not system default)
            proc = await asyncio.create_subprocess_exec(
                "open", "-a", "Firefox", url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            await asyncio.sleep(0.5)
            await _activate_browser("Firefox")
            return ToolResult(output=f"Opened {url} in Firefox (brought to front)")
        else:
            # Any other browser — use open -a to target it specifically
            proc = await asyncio.create_subprocess_exec(
                "open", "-a", browser, url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            await asyncio.sleep(0.5)
            await _activate_browser(browser)
            return ToolResult(output=f"Opened {url} in {browser} (brought to front)")

        ok, err = await _run_applescript(script)
        if not ok:
            # Fallback: use open -a to specifically target this browser
            proc = await asyncio.create_subprocess_exec(
                "open", "-a", browser, url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            await asyncio.sleep(0.3)
            await _activate_browser(browser)

        return ToolResult(output=f"Opened {url} in {browser} (brought to front)")


class BrowserGetPageContentTool(BaseTool):
    name = "browser_get_page_content"
    description = (
        "Get the text content of the current page in any browser. "
        "Brings the browser to front first. Supports Safari, Chrome, Arc, Edge. "
        "For Firefox, falls back to OCR. Auto-detects browser if not specified."
    )
    risk_level = RiskLevel.SAFE

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "browser": {
                    "type": "string",
                    "enum": SUPPORTED_BROWSERS,
                    "description": "Which browser to read from. Auto-detects if omitted.",
                },
            },
        }

    async def execute(self, browser: str = "") -> ToolResult:
        if not browser:
            browser = await _detect_browser()

        # Bring browser to front
        await _activate_browser(browser)

        if browser == "Safari":
            script = '''
                tell application "Safari"
                    set pageURL to URL of current tab of front window
                    set pageName to name of current tab of front window
                    set pageText to do JavaScript "document.body.innerText" in current tab of front window
                end tell
                return "URL: " & pageURL & linefeed & "Title: " & pageName & linefeed & linefeed & pageText
            '''
        elif browser in CHROMIUM_BROWSERS:
            script = f'''
                tell application "{browser}"
                    set pageURL to URL of active tab of front window
                    set pageTitle to title of active tab of front window
                    set pageText to execute active tab of front window javascript "document.body.innerText"
                end tell
                return "URL: " & pageURL & linefeed & "Title: " & pageTitle & linefeed & linefeed & pageText
            '''
        elif browser == "Firefox":
            return ToolResult(
                output="Firefox doesn't support JavaScript via AppleScript. "
                       "Use ocr_screen to read Firefox page content instead.",
                success=False,
            )
        else:
            return ToolResult(
                output=f"Browser '{browser}' not supported for page content. Use ocr_screen instead.",
                success=False,
            )

        ok, output = await _run_applescript(script)
        if not ok:
            return ToolResult(output=f"Failed to get page content: {output}", success=False)

        if len(output) > 10000:
            output = output[:10000] + "\n... (truncated)"
        return ToolResult(output=output)


class BrowserTabsTool(BaseTool):
    name = "browser_list_tabs"
    description = (
        "List all open tabs in a browser with their titles and URLs. "
        "Brings the browser to front. Auto-detects browser if not specified."
    )
    risk_level = RiskLevel.SAFE

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "browser": {
                    "type": "string",
                    "enum": SUPPORTED_BROWSERS,
                    "description": "Browser to list tabs from. Auto-detects if omitted.",
                },
            },
        }

    async def execute(self, browser: str = "") -> ToolResult:
        if not browser:
            browser = await _detect_browser()

        await _activate_browser(browser)

        if browser == "Safari":
            script = '''
                set output to ""
                tell application "Safari"
                    repeat with w in windows
                        repeat with t in tabs of w
                            set output to output & name of t & linefeed & URL of t & linefeed & "---" & linefeed
                        end repeat
                    end repeat
                end tell
                return output
            '''
        elif browser in CHROMIUM_BROWSERS:
            script = f'''
                set output to ""
                tell application "{browser}"
                    repeat with w in windows
                        repeat with t in tabs of w
                            set output to output & title of t & linefeed & URL of t & linefeed & "---" & linefeed
                        end repeat
                    end repeat
                end tell
                return output
            '''
        else:
            return ToolResult(
                output=f"Tab listing not supported for {browser}. Use ocr_screen instead.",
                success=False,
            )

        ok, output = await _run_applescript(script)
        if not ok:
            return ToolResult(output=f"Failed to list tabs: {output}", success=False)

        return ToolResult(output=output or "No tabs found.")


class BrowserSwitchTabTool(BaseTool):
    name = "browser_switch_tab"
    description = (
        "Switch to a specific tab by index (1-based) in the browser. "
        "Brings the browser to front."
    )
    risk_level = RiskLevel.SAFE

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "tab_index": {
                    "type": "integer",
                    "description": "Tab index (1-based). First tab is 1.",
                },
                "browser": {
                    "type": "string",
                    "enum": SUPPORTED_BROWSERS,
                    "description": "Browser to switch tab in. Auto-detects if omitted.",
                },
            },
            "required": ["tab_index"],
        }

    async def execute(self, tab_index: int, browser: str = "") -> ToolResult:
        if not browser:
            browser = await _detect_browser()

        await _activate_browser(browser)

        if browser == "Safari":
            script = f'''
                tell application "Safari"
                    set current tab of front window to tab {tab_index} of front window
                end tell
            '''
        elif browser in CHROMIUM_BROWSERS:
            script = f'''
                tell application "{browser}"
                    set active tab index of front window to {tab_index}
                end tell
            '''
        else:
            return ToolResult(
                output=f"Tab switching not supported for {browser}.",
                success=False,
            )

        ok, err = await _run_applescript(script)
        if not ok:
            return ToolResult(output=f"Failed to switch tab: {err}", success=False)

        return ToolResult(output=f"Switched to tab {tab_index} in {browser}")
