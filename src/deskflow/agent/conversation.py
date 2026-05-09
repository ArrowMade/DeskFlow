"""Conversation history management."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Conversation:
    messages: list[dict[str, Any]] = field(default_factory=list)
    _token_estimate: int = 0

    def add_user_message(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})
        self._token_estimate += len(text) // 4

    def add_assistant_message(self, content: list[dict]) -> None:
        """Add assistant message with content blocks."""
        self.messages.append({"role": "assistant", "content": content})
        self._token_estimate += sum(
            len(str(b)) // 4 for b in content
        )

    def add_tool_result(self, tool_use_id: str, result_content: list[dict]) -> None:
        """Add a tool result message."""
        self.messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result_content,
                }
            ],
        })
        self._token_estimate += sum(len(str(b)) // 4 for b in result_content)

    def get_messages(self) -> list[dict]:
        return self.messages

    def token_estimate(self) -> int:
        return self._token_estimate

    def compact(self, keep_last: int = 6) -> None:
        """Simple compaction: keep system context and last N messages."""
        if len(self.messages) > keep_last:
            # Keep a summary marker + recent messages
            removed = self.messages[:-keep_last]
            summary = f"[Earlier conversation with {len(removed)} messages was compacted]"
            self.messages = [
                {"role": "user", "content": summary},
                {"role": "assistant", "content": "Understood, continuing from recent context."},
            ] + self.messages[-keep_last:]
            self._token_estimate = sum(
                len(str(m)) // 4 for m in self.messages
            )

    def clear(self) -> None:
        self.messages.clear()
        self._token_estimate = 0
