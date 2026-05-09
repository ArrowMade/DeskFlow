"""Build memory context for injection into the system prompt."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .store import MemoryStore
    from .structured import StructuredMemory


def build_memory_context(
    structured: StructuredMemory | None = None,
    store: MemoryStore | None = None,
    max_facts: int = 20,
) -> str:
    """Build a memory section for the system prompt.

    Combines structured memory (SOUL.md, MEMORY.md, HEARTBEAT.md) with
    SQLite-backed interaction history.
    """
    parts = []

    # Structured memory takes priority (filesystem-based)
    if structured:
        ctx = structured.build_context(max_memory_lines=max_facts)
        if ctx:
            parts.append(ctx)

    # SQLite facts (legacy, still useful for auto-saved interactions)
    if store:
        facts = store.get_recent_facts(max_facts)
        if facts:
            parts.append("## Remembered Facts")
            for f in facts:
                parts.append(f"- {f}")

        interactions = store.get_recent_interactions(5)
        if interactions:
            parts.append("\n## Recent Interactions")
            for i in interactions:
                parts.append(f"- [{i['timestamp'][:16]}] {i['user_message'][:100]}")

    return "\n".join(parts) if parts else ""
