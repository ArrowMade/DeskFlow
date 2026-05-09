"""Safety classifier — gates every tool execution."""

from __future__ import annotations

from dataclasses import dataclass

from ..tools.base import BaseTool, RiskLevel
from .rules import SafetyRules


@dataclass
class SafetyDecision:
    risk_level: RiskLevel
    requires_confirmation: bool
    reason: str


class SafetyClassifier:
    def __init__(self, rules: SafetyRules) -> None:
        self.rules = rules

    # Tools that are auto-approved (no confirmation needed) unless dangerous
    AUTO_APPROVE_TOOLS = {
        # Screen understanding (read-only, safe)
        "get_ui_elements", "ocr_screen", "screenshot",
        "get_windows", "focus_window",
        # Input
        "applescript", "open_app", "close_app", "list_running_apps",
        "browser_open_url", "browser_get_page_content",
        "browser_list_tabs", "browser_switch_tab",
        "type_text", "press_key", "click_at", "scroll",
        "get_clipboard", "set_clipboard",
        "send_notification",
        "read_file", "list_directory", "search_files",
        "get_system_info", "run_python",
    }

    def classify(self, tool: BaseTool, inputs: dict) -> SafetyDecision:
        """Classify a tool call and decide if confirmation is needed."""
        risk = tool.risk_level

        # Special handling for shell commands
        if tool.name == "shell":
            command = inputs.get("command", "")
            return self._classify_shell(command, risk)

        # Special handling for file operations
        if tool.name in ("write_file", "move_file"):
            risk = RiskLevel.RISKY
        elif tool.name == "delete_file":
            risk = RiskLevel.DANGEROUS

        # Special handling for system settings
        if tool.name == "set_system_setting":
            risk = RiskLevel.DANGEROUS

        # Auto-approve common tools to avoid confirmation spam
        if tool.name in self.AUTO_APPROVE_TOOLS and risk != RiskLevel.DANGEROUS:
            return SafetyDecision(
                risk_level=risk,
                requires_confirmation=False,
                reason=f"Auto-approved tool: {tool.name}",
            )

        return SafetyDecision(
            risk_level=risk,
            requires_confirmation=self._needs_confirmation(risk),
            reason=f"Tool '{tool.name}' has risk level: {risk.value}",
        )

    def _classify_shell(self, command: str, base_risk: RiskLevel) -> SafetyDecision:
        """Classify a shell command."""
        # Check blocklist first
        if self.rules.is_shell_blocked(command):
            return SafetyDecision(
                risk_level=RiskLevel.DANGEROUS,
                requires_confirmation=True,
                reason=f"Command matches blocklist: {command}",
            )

        # Check dangerous patterns
        if self.rules.is_dangerous_pattern(command):
            return SafetyDecision(
                risk_level=RiskLevel.DANGEROUS,
                requires_confirmation=True,
                reason=f"Command matches dangerous pattern: {command}",
            )

        # Check allowlist
        if self.rules.is_shell_allowed(command):
            return SafetyDecision(
                risk_level=RiskLevel.SAFE,
                requires_confirmation=False,
                reason="Command is in allowlist",
            )

        # Default: use base risk
        return SafetyDecision(
            risk_level=base_risk,
            requires_confirmation=self._needs_confirmation(base_risk),
            reason=f"Shell command with risk level: {base_risk.value}",
        )

    def _needs_confirmation(self, risk: RiskLevel) -> bool:
        """Determine if a risk level needs confirmation based on config."""
        if risk == RiskLevel.SAFE and self.rules.auto_approve_safe:
            return False

        threshold = self.rules.require_confirmation
        if threshold == "all":
            return True
        elif threshold == "risky":
            return risk in (RiskLevel.RISKY, RiskLevel.DANGEROUS)
        elif threshold == "dangerous":
            return risk == RiskLevel.DANGEROUS
        return True
