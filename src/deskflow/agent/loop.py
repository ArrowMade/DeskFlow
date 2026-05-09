"""Core agentic loop — the brain of DeskFlow.

Implements the ReAct (Reason + Act) pattern:
1. Normalize — standardize input
2. Context Assembly — build prompt from skills + memory + history
3. Infer — call the LLM
4. Act — execute tool calls
5. Observe — verify results
6. Persist — save to memory + heartbeat
"""

from __future__ import annotations

import json
import os
import platform
from datetime import datetime
from typing import TYPE_CHECKING, Callable

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from .client import DeepSeekClient
from .conversation import Conversation
from ..tools.base import ToolResult

if TYPE_CHECKING:
    from ..config import Config
    from ..tools.registry import ToolRegistry
    from ..safety.classifier import SafetyClassifier
    from ..memory.store import MemoryStore
    from ..memory.structured import StructuredMemory
    from ..skills.loader import SkillLoader


BASE_SYSTEM_PROMPT = """\
You are DeskFlow, a powerful AI desktop agent that can fully control this Mac. \
You are like a human sitting at the computer — you can see the screen, click, \
type, drag, scroll, open apps, run commands, browse the web, and manage files.

## How You Work (Observe → Think → Act → Verify)
1. **Observe**: Use `get_ui_elements` or `ocr_screen` to understand what's on screen. \
Use `get_windows` to see what's open. These are your EYES.
2. **Think**: Plan what to do. Break complex tasks into small steps.
3. **Act**: Use tools to execute — click buttons, type text, run commands, etc.
4. **Verify**: After acting, observe again to confirm it worked. \
Use `ocr_screen` or `get_ui_elements` to check.

## Tool Selection Guide
- **See the screen**: `ocr_screen` (read text), `get_ui_elements` (see UI controls + positions)
- **Find where to click**: `get_ui_elements` → find the element → click at its center (x + w/2, y + h/2)
- **Click/type/scroll**: `click_at`, `type_text`, `press_key`, `scroll`, `drag`
- **App control**: `open_app`, `close_app`, `focus_window`, `get_windows`
- **Window layout**: `get_windows`, `move_resize_window`
- **Files**: `read_file`, `write_file`, `list_directory`, `search_files`, `move_file`, `delete_file`
- **System**: `shell`, `run_python`, `applescript`, `get_system_info`
- **Browser**: `browser_open_url`, `browser_get_page_content`
- **Clipboard**: `get_clipboard`, `set_clipboard`
- **Memory**: You can save things you learn about the user by telling them you'll remember it.

## Important Rules
- ALWAYS focus/activate the target window BEFORE doing any operation on it. \
Use `focus_window` or `open_app` to bring the app to front first.
- When the user mentions a specific browser (Chrome, Safari, Firefox, etc.), ALWAYS pass \
the `browser` parameter to browser tools. Do NOT omit it or the wrong browser may open.
- Only omit the `browser` parameter when the user doesn't care which browser to use.
- Use `browser_list_tabs` to see all open tabs, `browser_switch_tab` to switch tabs.
- ALWAYS observe before clicking. Never guess coordinates — use `get_ui_elements` first.
- When clicking a UI element, calculate center: x + width/2, y + height/2.
- If an action fails, observe the screen again, diagnose, and try a different approach.
- For destructive actions (delete, overwrite), warn the user first.
- Be concise. Don't over-explain — just do the task.
- Chain multiple actions when the task is clear (don't ask for confirmation on every step).
- If you need to wait for something (loading, download), use small delays then re-observe."""


class AgentLoop:
    """The main agent loop with ReAct pattern, skills, and structured memory."""

    def __init__(
        self,
        client: DeepSeekClient,
        registry: ToolRegistry,
        config: Config,
        console: Console,
        safety: SafetyClassifier | None = None,
        memory: MemoryStore | None = None,
        structured_memory: StructuredMemory | None = None,
        skill_loader: SkillLoader | None = None,
    ) -> None:
        self.client = client
        self.registry = registry
        self.config = config
        self.console = console
        self.safety = safety
        self.memory = memory
        self.structured_memory = structured_memory
        self.skill_loader = skill_loader
        self.conversation = Conversation()

        # Hooks: before/after tool execution
        self._before_tool_hooks: list[Callable] = []
        self._after_tool_hooks: list[Callable] = []

    def add_before_tool_hook(self, hook: Callable) -> None:
        """Register a hook called before every tool execution.
        Signature: hook(tool_name: str, tool_input: dict) -> dict | None
        Return modified input, or None to block execution."""
        self._before_tool_hooks.append(hook)

    def add_after_tool_hook(self, hook: Callable) -> None:
        """Register a hook called after every tool execution.
        Signature: hook(tool_name: str, tool_input: dict, result: ToolResult) -> None"""
        self._after_tool_hooks.append(hook)

    # ─── Stage 1: Normalize ───

    def _normalize_message(self, user_message: str) -> str:
        """Normalize the user message (clean whitespace, etc.)."""
        return user_message.strip()

    # ─── Stage 2: Context Assembly ───

    def _assemble_context(self, user_message: str) -> str:
        """Build the full system prompt from base + soul + skills + memory + environment."""
        parts = [BASE_SYSTEM_PROMPT]

        # Environment
        parts.append(f"""
## Current Environment
- macOS {platform.mac_ver()[0] or 'unknown'}
- User: {os.getenv('USER', 'unknown')}
- CWD: {os.getcwd()}
- Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}""")

        # Soul (from structured memory)
        if self.structured_memory:
            soul = self.structured_memory.get_soul()
            if soul.strip():
                parts.append(f"\n{soul.strip()}")

        # Skills (selected based on user message)
        if self.skill_loader:
            skills = self.skill_loader.select_skills(user_message, max_skills=3)
            if skills:
                skill_text = []
                skill_text.append("\n## Active Skills")
                for skill in skills:
                    skill_text.append(f"\n### Skill: {skill.name}")
                    skill_text.append(skill.content)
                parts.append("\n".join(skill_text))

        # Memory context (structured + SQLite)
        memory_section = ""
        if self.structured_memory:
            from ..memory.context import build_memory_context
            memory_section = build_memory_context(
                structured=self.structured_memory,
                store=self.memory,
                max_facts=self.config.memory.max_context_facts,
            )
        elif self.memory:
            from ..memory.context import build_memory_context
            memory_section = build_memory_context(
                store=self.memory,
                max_facts=self.config.memory.max_context_facts,
            )

        if memory_section:
            parts.append(f"\n{memory_section}")

        return "\n".join(parts)

    # ─── Stage 3-5: Infer → Act → Observe Loop ───

    async def run(self, user_message: str) -> None:
        """Run the full ReAct loop for a single user message.

        1. Normalize
        2. Context Assembly
        3. Infer (LLM call)
        4. Act (execute tools)
        5. Observe (verify results)
        6. Persist (save to memory)
        """
        # Stage 1: Normalize
        user_message = self._normalize_message(user_message)
        self.conversation.add_user_message(user_message)

        # Stage 2: Context Assembly
        system_prompt = self._assemble_context(user_message)
        tools = self._build_openai_tools()

        # Log to heartbeat
        if self.structured_memory:
            self.structured_memory.log_heartbeat(
                f"User request: {user_message[:100]}", "task"
            )

        max_iterations = 25
        tools_used = []

        # Stage 3-5: ReAct loop
        for iteration in range(max_iterations):
            # Check context window
            if self.conversation.token_estimate() > self.config.max_context_tokens * 0.8:
                self.conversation.compact()

            # Stage 3: Infer
            response = self.client.create_message(
                system=system_prompt,
                messages=self.conversation.get_messages(),
                tools=tools,
                max_tokens=self.config.max_output_tokens,
            )

            choice = response.choices[0]
            message = choice.message

            # Build assistant message for history
            assistant_msg: dict = {"role": "assistant"}

            # Handle DeepSeek V4 Pro reasoning_content
            reasoning = getattr(message, "reasoning_content", None)
            if not reasoning and hasattr(message, "model_extra"):
                reasoning = (message.model_extra or {}).get("reasoning_content")
            if reasoning:
                assistant_msg["reasoning_content"] = reasoning

            if message.content:
                assistant_msg["content"] = message.content
                self.console.print(Markdown(message.content))
            else:
                assistant_msg["content"] = ""

            if message.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ]

            self.conversation.messages.append(assistant_msg)

            # If no tool calls, we're done
            if choice.finish_reason == "stop" or not message.tool_calls:
                break

            # Stage 4: Act — execute tool calls
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    tool_input = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    tool_input = {}

                tool = self.registry.get_tool(tool_name)

                # Safety check
                approved = True
                if self.safety and tool:
                    decision = self.safety.classify(tool, tool_input)
                    if decision.requires_confirmation:
                        self.console.print(Panel(
                            f"[bold yellow]Tool:[/bold yellow] {tool_name}\n"
                            f"[bold yellow]Risk:[/bold yellow] {decision.risk_level.value}\n"
                            f"[bold yellow]Reason:[/bold yellow] {decision.reason}\n"
                            f"[bold yellow]Input:[/bold yellow] {tool_input}",
                            title="[bold red]Confirmation Required[/bold red]",
                            border_style="red",
                        ))
                        from rich.prompt import Confirm
                        approved = Confirm.ask("Allow this action?")

                if not approved:
                    result = ToolResult(output="User denied this action.", success=False)
                    if self.structured_memory:
                        self.structured_memory.log_heartbeat(
                            f"User denied: {tool_name}", "note"
                        )
                else:
                    # Before-tool hooks
                    for hook in self._before_tool_hooks:
                        modified = hook(tool_name, tool_input)
                        if modified is None:
                            approved = False
                            break
                        tool_input = modified

                    if not approved:
                        result = ToolResult(output="Blocked by hook.", success=False)
                    else:
                        # Display tool call
                        self.console.print(Panel(
                            f"[dim]{tool_input}[/dim]",
                            title=f"[bold cyan]{tool_name}[/bold cyan]",
                            border_style="cyan",
                            padding=(0, 1),
                        ))

                        # Execute
                        result = await self.registry.call(tool_name, tool_input)
                        tools_used.append(tool_name)

                        # After-tool hooks
                        for hook in self._after_tool_hooks:
                            hook(tool_name, tool_input, result)

                # Display result
                style = "green" if result.success else "red"
                output_display = result.output
                if len(output_display) > 2000:
                    output_display = output_display[:2000] + "\n... (truncated)"
                self.console.print(Panel(
                    output_display,
                    title=f"[bold {style}]Result[/bold {style}]",
                    border_style=style,
                    padding=(0, 1),
                ))

                # Log to heartbeat
                if self.structured_memory:
                    status = "success" if result.success else "error"
                    self.structured_memory.log_heartbeat(
                        f"`{tool_name}` → {'OK' if result.success else 'FAIL'}",
                        status,
                    )

                # Add tool result to conversation
                self.conversation.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result.output,
                })

        # Stage 6: Persist
        if self.memory:
            self.memory.save_interaction(user_message)

        if self.structured_memory and tools_used:
            self.structured_memory.log_heartbeat(
                f"Completed: {user_message[:80]} (tools: {', '.join(set(tools_used))})",
                "success",
            )

    def _build_openai_tools(self) -> list[dict]:
        """Convert our tool schemas to OpenAI function-calling format."""
        tools = []
        for schema in self.registry.get_api_schemas():
            tools.append({
                "type": "function",
                "function": {
                    "name": schema["name"],
                    "description": schema["description"],
                    "parameters": schema["input_schema"],
                },
            })
        return tools
