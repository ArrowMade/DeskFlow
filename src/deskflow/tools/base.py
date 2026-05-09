"""Base tool interface and shared types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(Enum):
    SAFE = "safe"
    RISKY = "risky"
    DANGEROUS = "dangerous"


@dataclass
class ToolResult:
    output: str
    success: bool = True
    image_base64: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    name: str
    description: str
    risk_level: RiskLevel = RiskLevel.SAFE

    @abstractmethod
    def get_input_schema(self) -> dict:
        """Return JSON Schema dict for the tool's parameters."""
        ...

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Run the tool with the given inputs."""
        ...

    def to_api_schema(self) -> dict:
        """Return the Anthropic API tool schema."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.get_input_schema(),
        }
