"""Confirmation prompts for risky actions."""

from __future__ import annotations

from rich.console import Console
from rich.prompt import Confirm


def confirm_action(
    console: Console,
    tool_name: str,
    inputs: dict,
    reason: str,
) -> bool:
    """Ask the user to confirm a risky action. Returns True if approved."""
    console.print(f"\n[bold yellow]⚠ Confirmation required[/bold yellow]")
    console.print(f"  Tool: [cyan]{tool_name}[/cyan]")
    console.print(f"  Reason: {reason}")
    console.print(f"  Input: {inputs}")
    return Confirm.ask("  Allow this action?")
