"""Configuration loading from YAML + environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class SafetyConfig:
    auto_approve_safe: bool = True
    require_confirmation: str = "risky"
    shell_allowlist: list[str] = field(default_factory=list)
    shell_blocklist: list[str] = field(default_factory=list)


@dataclass
class MemoryConfig:
    enabled: bool = True
    db_path: str = "~/.deskflow/memory.db"
    max_context_facts: int = 20


@dataclass
class Config:
    api_key: str = ""
    model: str = "deepseek-v4-pro"
    max_context_tokens: int = 1000000
    max_output_tokens: int = 8192
    workspace_dir: str = "~/.deskflow/workspace"
    skills_dirs: list[str] = field(default_factory=lambda: [])
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    enabled_tools: list[str] | None = None


def load_config(config_path: str | None = None) -> Config:
    """Load config from YAML file, with env var overrides."""
    # Find config file
    paths_to_try = []
    if config_path:
        paths_to_try.append(Path(config_path))
    paths_to_try.extend([
        Path.home() / ".deskflow" / "config.yaml",
        Path(__file__).parent.parent.parent / "config.default.yaml",
    ])

    raw: dict = {}
    config_file_dir = Path(__file__).parent.parent.parent
    for p in paths_to_try:
        if p.exists():
            with open(p) as f:
                raw = yaml.safe_load(f) or {}
            config_file_dir = p.parent
            break

    # Build config
    api_key = os.environ.get("DEEPSEEK_API_KEY", raw.get("api_key")) or ""

    safety_raw = raw.get("safety", {})
    safety = SafetyConfig(
        auto_approve_safe=safety_raw.get("auto_approve_safe", True),
        require_confirmation=safety_raw.get("require_confirmation", "risky"),
        shell_allowlist=safety_raw.get("shell_allowlist", []),
        shell_blocklist=safety_raw.get("shell_blocklist", []),
    )

    mem_raw = raw.get("memory", {})
    memory = MemoryConfig(
        enabled=mem_raw.get("enabled", True),
        db_path=mem_raw.get("db_path", "~/.deskflow/memory.db"),
        max_context_facts=mem_raw.get("max_context_facts", 20),
    )

    tools_raw = raw.get("tools", {})
    enabled_tools = tools_raw.get("enabled")

    # Skills directories: bundled skills + user skills
    bundled_skills = str(config_file_dir / "skills")
    user_skills = os.path.expanduser(
        raw.get("skills_dir", "~/.deskflow/skills")
    )
    skills_dirs = [bundled_skills, user_skills]

    return Config(
        api_key=api_key,
        model=raw.get("model", "deepseek-v4-pro"),
        max_context_tokens=raw.get("max_context_tokens", 1000000),
        max_output_tokens=raw.get("max_output_tokens", 8192),
        workspace_dir=raw.get("workspace_dir", "~/.deskflow/workspace"),
        skills_dirs=skills_dirs,
        safety=safety,
        memory=memory,
        enabled_tools=enabled_tools,
    )
