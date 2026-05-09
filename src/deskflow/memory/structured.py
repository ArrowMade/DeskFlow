"""Structured filesystem memory — SOUL.md, MEMORY.md, HEARTBEAT.md.

Inspired by OpenClaw's workspace memory pattern:
- SOUL.md: Agent personality, role, and behavior customization
- MEMORY.md: Long-term facts about user, preferences, learned context
- HEARTBEAT.md: Daily activity log, task tracking, session summaries
"""

from __future__ import annotations

import os
from datetime import datetime, date
from pathlib import Path


class StructuredMemory:
    """Manages filesystem-based memory files in the workspace directory."""

    def __init__(self, workspace_dir: str = "~/.deskflow/workspace") -> None:
        self.workspace_dir = os.path.expanduser(workspace_dir)
        Path(self.workspace_dir).mkdir(parents=True, exist_ok=True)

        self.soul_path = os.path.join(self.workspace_dir, "SOUL.md")
        self.memory_path = os.path.join(self.workspace_dir, "MEMORY.md")
        self.heartbeat_path = os.path.join(self.workspace_dir, "HEARTBEAT.md")

        # Create defaults if they don't exist
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        """Create default memory files if they don't exist."""
        if not os.path.exists(self.soul_path):
            self._write(self.soul_path, DEFAULT_SOUL)
        if not os.path.exists(self.memory_path):
            self._write(self.memory_path, DEFAULT_MEMORY)
        if not os.path.exists(self.heartbeat_path):
            self._write(self.heartbeat_path, DEFAULT_HEARTBEAT)

    def _read(self, path: str) -> str:
        """Read a file, return empty string if it doesn't exist."""
        try:
            with open(path) as f:
                return f.read()
        except OSError:
            return ""

    def _write(self, path: str, content: str) -> None:
        """Write content to a file."""
        with open(path, "w") as f:
            f.write(content)

    def _append(self, path: str, content: str) -> None:
        """Append content to a file."""
        with open(path, "a") as f:
            f.write(content)

    # --- SOUL ---

    def get_soul(self) -> str:
        """Get the agent personality/soul."""
        return self._read(self.soul_path)

    def set_soul(self, content: str) -> None:
        """Replace the soul content entirely."""
        self._write(self.soul_path, content)

    # --- MEMORY ---

    def get_memory(self) -> str:
        """Get all long-term memory facts."""
        return self._read(self.memory_path)

    def add_memory(self, fact: str, category: str = "General") -> None:
        """Add a fact to long-term memory."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n- [{timestamp}] **{category}**: {fact}"

        content = self._read(self.memory_path)
        # Find the section or append at end
        if f"## {category}" in content:
            # Append under existing section
            lines = content.split("\n")
            new_lines = []
            inserted = False
            for i, line in enumerate(lines):
                new_lines.append(line)
                if not inserted and line.strip() == f"## {category}":
                    new_lines.append(f"- [{timestamp}] {fact}")
                    inserted = True
            self._write(self.memory_path, "\n".join(new_lines))
        else:
            # Add new section
            self._append(self.memory_path, f"\n\n## {category}\n- [{timestamp}] {fact}\n")

    def search_memory(self, query: str) -> list[str]:
        """Search memory for lines containing query."""
        content = self._read(self.memory_path)
        query_lower = query.lower()
        return [
            line.strip()
            for line in content.split("\n")
            if query_lower in line.lower() and line.strip().startswith("-")
        ]

    # --- HEARTBEAT ---

    def get_heartbeat(self) -> str:
        """Get the heartbeat/daily log."""
        return self._read(self.heartbeat_path)

    def log_heartbeat(self, entry: str, entry_type: str = "action") -> None:
        """Add an entry to today's heartbeat log."""
        today = date.today().isoformat()
        timestamp = datetime.now().strftime("%H:%M:%S")
        content = self._read(self.heartbeat_path)

        today_header = f"## {today}"
        icon = {"action": "🔧", "task": "📋", "error": "❌", "success": "✅", "note": "📝"}.get(entry_type, "•")
        log_line = f"- `{timestamp}` {icon} {entry}"

        if today_header in content:
            # Append under today's section
            lines = content.split("\n")
            new_lines = []
            for i, line in enumerate(lines):
                new_lines.append(line)
                if line.strip() == today_header:
                    new_lines.append(log_line)
            self._write(self.heartbeat_path, "\n".join(new_lines))
        else:
            # Start new day
            self._append(self.heartbeat_path, f"\n{today_header}\n{log_line}\n")

    def get_today_log(self) -> str:
        """Get just today's heartbeat entries."""
        today = date.today().isoformat()
        content = self._read(self.heartbeat_path)
        today_header = f"## {today}"

        if today_header not in content:
            return ""

        # Extract today's section
        lines = content.split("\n")
        today_lines = []
        in_today = False
        for line in lines:
            if line.strip() == today_header:
                in_today = True
                today_lines.append(line)
                continue
            if in_today:
                if line.startswith("## ") and line.strip() != today_header:
                    break
                today_lines.append(line)

        return "\n".join(today_lines)

    # --- CONTEXT BUILDING ---

    def build_context(self, max_memory_lines: int = 30) -> str:
        """Build the full memory context for injection into system prompt."""
        parts = []

        # Soul (personality)
        soul = self.get_soul()
        if soul.strip():
            parts.append(soul.strip())

        # Memory (facts) — truncate if too long
        memory = self.get_memory()
        if memory.strip():
            mem_lines = memory.strip().split("\n")
            if len(mem_lines) > max_memory_lines:
                mem_lines = mem_lines[:max_memory_lines]
                mem_lines.append("... (more memories stored)")
            parts.append("\n".join(mem_lines))

        # Today's heartbeat
        today_log = self.get_today_log()
        if today_log.strip():
            parts.append(f"## Today's Activity\n{today_log.strip()}")

        return "\n\n".join(parts) if parts else ""


# --- DEFAULTS ---

DEFAULT_SOUL = """# DeskFlow — Soul

You are DeskFlow, a capable and efficient macOS desktop automation agent.

## Personality
- You are helpful, proactive, and concise.
- You prefer action over explanation — do things, don't just talk about them.
- You confirm before destructive actions but otherwise move quickly.
- You learn from the user's preferences and adapt your behavior.

## Behavior
- When given a task, execute it immediately rather than asking clarifying questions \
(unless the task is genuinely ambiguous).
- Chain multiple actions together when the goal is clear.
- After completing a task, briefly confirm what was done.
- If something fails, try an alternative approach before asking for help.
"""

DEFAULT_MEMORY = """# DeskFlow — Memory

Long-term facts about the user, their preferences, and learned context.

## User Preferences
"""

DEFAULT_HEARTBEAT = """# DeskFlow — Heartbeat

Daily activity log and task tracking.
"""
