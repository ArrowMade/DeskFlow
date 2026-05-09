"""Rich CLI interface — REPL, streaming, confirmations."""

from __future__ import annotations

import asyncio
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import load_config
from .agent.client import DeepSeekClient
from .agent.loop import AgentLoop
from .tools.registry import build_default_registry


console = Console()


def print_banner() -> None:
    console.print(Panel(
        "[bold white]DeskFlow[/bold white] — macOS AI Desktop Agent\n"
        "[dim]Powered by DeepSeek V4 Pro | Skills + Memory + ReAct Loop[/dim]\n"
        "[dim]Type your request. Use /help for commands, /quit to exit.[/dim]",
        border_style="bright_blue",
        padding=(1, 2),
    ))


def print_help() -> None:
    table = Table(title="Commands", border_style="dim")
    table.add_column("Command", style="cyan")
    table.add_column("Description")
    table.add_row("/help", "Show this help message")
    table.add_row("/tools", "List available tools")
    table.add_row("/skills", "List loaded skills")
    table.add_row("/soul", "Show agent personality (SOUL.md)")
    table.add_row("/memory", "Show stored memories")
    table.add_row("/heartbeat", "Show today's activity log")
    table.add_row("/clear", "Clear conversation history")
    table.add_row("/reload", "Reload skills from disk")
    table.add_row("/quit", "Exit DeskFlow")
    console.print(table)


def print_tools(registry) -> None:
    table = Table(title="Available Tools", border_style="dim")
    table.add_column("Tool", style="cyan")
    table.add_column("Risk", style="yellow")
    table.add_column("Description")
    for tool in registry.list_tools():
        table.add_row(tool.name, tool.risk_level.value, tool.description[:60] + "...")
    console.print(table)


def print_skills(skill_loader) -> None:
    if not skill_loader:
        console.print("[dim]Skills not loaded.[/dim]")
        return
    skills = skill_loader.get_all_skills()
    if not skills:
        console.print("[dim]No skills found.[/dim]")
        return
    table = Table(title="Loaded Skills", border_style="dim")
    table.add_column("Skill", style="cyan")
    table.add_column("Triggers", style="yellow")
    table.add_column("Description")
    for skill in skills:
        triggers = ", ".join(skill.triggers[:5])
        if len(skill.triggers) > 5:
            triggers += f" (+{len(skill.triggers) - 5})"
        table.add_row(skill.name, triggers, skill.description[:50])
    console.print(table)


async def repl(agent: AgentLoop, registry, skill_loader) -> None:
    """Main REPL loop."""
    print_banner()

    while True:
        try:
            console.print()
            user_input = console.input("[bold cyan]>>> [/bold cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not user_input:
            continue

        if user_input in ("/quit", "/exit", "/q"):
            console.print("[dim]Goodbye![/dim]")
            break
        elif user_input == "/help":
            print_help()
            continue
        elif user_input == "/tools":
            print_tools(registry)
            continue
        elif user_input == "/skills":
            print_skills(skill_loader)
            continue
        elif user_input == "/soul":
            if agent.structured_memory:
                soul = agent.structured_memory.get_soul()
                console.print(Panel(soul, title="[bold]SOUL.md[/bold]", border_style="magenta"))
            else:
                console.print("[dim]Structured memory not enabled.[/dim]")
            continue
        elif user_input == "/memory":
            if agent.structured_memory:
                mem = agent.structured_memory.get_memory()
                console.print(Panel(mem, title="[bold]MEMORY.md[/bold]", border_style="green"))
            elif agent.memory:
                facts = agent.memory.get_recent_facts(20)
                if facts:
                    for f in facts:
                        console.print(f"  [dim]•[/dim] {f}")
                else:
                    console.print("[dim]No memories stored yet.[/dim]")
            else:
                console.print("[dim]Memory is disabled.[/dim]")
            continue
        elif user_input == "/heartbeat":
            if agent.structured_memory:
                log = agent.structured_memory.get_today_log()
                if log:
                    console.print(Panel(log, title="[bold]Today's Heartbeat[/bold]", border_style="yellow"))
                else:
                    console.print("[dim]No activity logged today.[/dim]")
            else:
                console.print("[dim]Structured memory not enabled.[/dim]")
            continue
        elif user_input == "/clear":
            agent.conversation.clear()
            console.print("[dim]Conversation cleared.[/dim]")
            continue
        elif user_input == "/reload":
            if skill_loader:
                skill_loader.reload()
                console.print(f"[dim]Reloaded {len(skill_loader.get_all_skills())} skills.[/dim]")
            else:
                console.print("[dim]Skills not loaded.[/dim]")
            continue

        try:
            await agent.run(user_input)
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted.[/yellow]")
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")


def main() -> None:
    """Entry point."""
    config = load_config()

    if not config.api_key:
        console.print(Panel(
            "[bold]Welcome to DeskFlow![/bold]\n\n"
            "To get started, you need a DeepSeek API key.\n"
            "Get one at: [cyan]https://platform.deepseek.com/api_keys[/cyan]",
            border_style="bright_blue",
        ))
        try:
            api_key = console.input("\n[bold cyan]Enter your DeepSeek API key: [/bold cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            sys.exit(0)

        if not api_key:
            console.print("[bold red]No API key provided. Exiting.[/bold red]")
            sys.exit(1)

        config.api_key = api_key

        # Save to ~/.deskflow/config.yaml so they don't have to enter it again
        from pathlib import Path
        config_dir = Path.home() / ".deskflow"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.yaml"

        if config_file.exists():
            import yaml
            with open(config_file) as f:
                existing = yaml.safe_load(f) or {}
            existing["api_key"] = api_key
            with open(config_file, "w") as f:
                yaml.dump(existing, f, default_flow_style=False)
        else:
            with open(config_file, "w") as f:
                f.write(f"api_key: {api_key}\n")

        console.print(f"[green]API key saved to {config_file}[/green]\n")

    client = DeepSeekClient(api_key=config.api_key, model=config.model)
    registry = build_default_registry(config.enabled_tools)

    # Safety
    safety = None
    try:
        from .safety.classifier import SafetyClassifier
        from .safety.rules import SafetyRules
        rules = SafetyRules(
            shell_allowlist=config.safety.shell_allowlist,
            shell_blocklist=config.safety.shell_blocklist,
            require_confirmation=config.safety.require_confirmation,
            auto_approve_safe=config.safety.auto_approve_safe,
        )
        safety = SafetyClassifier(rules)
    except Exception:
        pass

    # Memory (SQLite)
    memory = None
    if config.memory.enabled:
        try:
            from .memory.store import MemoryStore
            memory = MemoryStore(config.memory.db_path)
        except Exception:
            pass

    # Structured Memory (SOUL.md + MEMORY.md + HEARTBEAT.md)
    structured_memory = None
    try:
        from .memory.structured import StructuredMemory
        structured_memory = StructuredMemory(config.workspace_dir)
    except Exception:
        pass

    # Skills
    skill_loader = None
    try:
        from .skills.loader import SkillLoader
        skill_loader = SkillLoader(config.skills_dirs)
        skill_count = len(skill_loader.get_all_skills())
        if skill_count > 0:
            console.print(f"[dim]Loaded {skill_count} skills[/dim]")
    except Exception:
        pass

    agent = AgentLoop(
        client=client,
        registry=registry,
        config=config,
        console=console,
        safety=safety,
        memory=memory,
        structured_memory=structured_memory,
        skill_loader=skill_loader,
    )

    # Print tool count
    console.print(f"[dim]{len(registry.list_tools())} tools ready[/dim]")

    asyncio.run(repl(agent, registry, skill_loader))


if __name__ == "__main__":
    main()
