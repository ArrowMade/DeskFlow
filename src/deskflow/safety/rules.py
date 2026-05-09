"""Safety rules — allowlists, blocklists, pattern matching."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SafetyRules:
    shell_allowlist: list[str] = field(default_factory=list)
    shell_blocklist: list[str] = field(default_factory=list)
    require_confirmation: str = "risky"  # "risky", "dangerous", "all"
    auto_approve_safe: bool = True

    # Patterns that always escalate to DANGEROUS
    dangerous_patterns: list[str] = field(default_factory=lambda: [
        r"sudo\s+rm",
        r"rm\s+-rf\s+/",
        r"mkfs",
        r"dd\s+if=",
        r">\s*/dev/",
        r"chmod\s+777",
        r"curl.*\|\s*sh",
        r"wget.*\|\s*sh",
        r":\(\)\s*\{",  # fork bomb
        r"shutdown",
        r"reboot",
        r"launchctl\s+unload",
        r"defaults\s+delete",
        r"diskutil\s+erase",
        r"networksetup.*-setdnsservers",
    ])

    def is_shell_allowed(self, command: str) -> bool:
        """Check if a shell command matches the allowlist."""
        cmd_base = command.strip().split()[0] if command.strip() else ""
        return cmd_base in self.shell_allowlist

    def is_shell_blocked(self, command: str) -> bool:
        """Check if a shell command matches the blocklist."""
        for pattern in self.shell_blocklist:
            if pattern in command:
                return True
        return False

    def is_dangerous_pattern(self, command: str) -> bool:
        """Check if command matches dangerous patterns."""
        for pattern in self.dangerous_patterns:
            if re.search(pattern, command):
                return True
        return False
