"""Skill loader — reads and parses markdown skill files."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Skill:
    name: str
    description: str
    triggers: list[str]
    content: str  # The markdown body (instructions)
    path: str

    def matches(self, text: str) -> int:
        """Return a relevance score (0 = no match, higher = more relevant)."""
        text_lower = text.lower()
        score = 0
        for trigger in self.triggers:
            if trigger.lower() in text_lower:
                score += 1
        return score


class SkillLoader:
    """Loads skills from one or more directories. Later directories override earlier ones."""

    def __init__(self, skill_dirs: list[str]) -> None:
        self.skill_dirs = skill_dirs
        self._skills: dict[str, Skill] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Load all skill files from all directories."""
        for skill_dir in self.skill_dirs:
            expanded = os.path.expanduser(skill_dir)
            if not os.path.isdir(expanded):
                continue
            for filename in sorted(os.listdir(expanded)):
                if not filename.endswith(".md"):
                    continue
                filepath = os.path.join(expanded, filename)
                skill = self._parse_skill(filepath)
                if skill:
                    self._skills[skill.name] = skill  # Later dirs override

    def _parse_skill(self, filepath: str) -> Skill | None:
        """Parse a skill markdown file with YAML frontmatter."""
        try:
            with open(filepath) as f:
                text = f.read()
        except OSError:
            return None

        # Parse YAML frontmatter (between --- markers)
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
        if not match:
            return None

        frontmatter_text = match.group(1)
        body = match.group(2).strip()

        # Simple YAML parsing (avoid heavy dependency)
        meta: dict = {}
        current_key = ""
        current_list: list[str] = []

        for line in frontmatter_text.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("- "):
                current_list.append(line[2:].strip())
                meta[current_key] = current_list
                continue

            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()

                current_key = key
                current_list = []

                if value:
                    meta[key] = value
                else:
                    meta[key] = []

        name = meta.get("name", Path(filepath).stem)
        description = meta.get("description", "")
        triggers = meta.get("triggers", [])

        if isinstance(triggers, str):
            triggers = [triggers]

        return Skill(
            name=name,
            description=description,
            triggers=triggers,
            content=body,
            path=filepath,
        )

    def get_all_skills(self) -> list[Skill]:
        """Return all loaded skills."""
        return list(self._skills.values())

    def get_skill(self, name: str) -> Skill | None:
        """Get a skill by name."""
        return self._skills.get(name)

    def select_skills(self, user_message: str, max_skills: int = 3) -> list[Skill]:
        """Select the most relevant skills for a user message.
        Returns up to max_skills, sorted by relevance score."""
        scored = []
        for skill in self._skills.values():
            score = skill.matches(user_message)
            if score > 0:
                scored.append((score, skill))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [skill for _, skill in scored[:max_skills]]

    def reload(self) -> None:
        """Reload all skills from disk."""
        self._skills.clear()
        self._load_all()
