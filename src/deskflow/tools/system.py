"""System info and settings tools."""

from __future__ import annotations

import asyncio
import os
import platform

from .base import BaseTool, RiskLevel, ToolResult


class GetSystemInfoTool(BaseTool):
    name = "get_system_info"
    description = "Get macOS system information — version, hardware, disk, memory, etc."
    risk_level = RiskLevel.SAFE

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["all", "os", "hardware", "disk", "network", "battery"],
                    "description": "Category of info to retrieve. Defaults to 'all'.",
                },
            },
        }

    async def execute(self, category: str = "all") -> ToolResult:
        info_parts = []

        if category in ("all", "os"):
            mac_ver = platform.mac_ver()
            info_parts.append(
                f"macOS: {mac_ver[0]}\n"
                f"User: {os.getenv('USER')}\n"
                f"Home: {os.path.expanduser('~')}\n"
                f"Shell: {os.getenv('SHELL', 'unknown')}\n"
                f"Architecture: {platform.machine()}"
            )

        if category in ("all", "hardware"):
            proc = await asyncio.create_subprocess_exec(
                "sysctl", "-n", "hw.memsize", "hw.ncpu", "machdep.cpu.brand_string",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            lines = stdout.decode().strip().split("\n")
            if len(lines) >= 3:
                mem_gb = int(lines[0]) / (1024**3)
                info_parts.append(
                    f"CPU: {lines[2]}\n"
                    f"Cores: {lines[1]}\n"
                    f"Memory: {mem_gb:.0f} GB"
                )

        if category in ("all", "disk"):
            proc = await asyncio.create_subprocess_exec(
                "df", "-h", "/",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            info_parts.append(f"Disk:\n{stdout.decode().strip()}")

        if category in ("all", "battery"):
            proc = await asyncio.create_subprocess_exec(
                "pmset", "-g", "batt",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            info_parts.append(f"Battery:\n{stdout.decode().strip()}")

        if category in ("all", "network"):
            proc = await asyncio.create_subprocess_exec(
                "ifconfig", "en0",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            info_parts.append(f"Network (en0):\n{stdout.decode().strip()}")

        return ToolResult(output="\n\n".join(info_parts))


class SetSystemSettingTool(BaseTool):
    name = "set_system_setting"
    description = (
        "Modify a macOS system setting using the 'defaults' command. "
        "This changes system preferences. Use with extreme caution."
    )
    risk_level = RiskLevel.DANGEROUS

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "The defaults domain (e.g., 'com.apple.finder', 'NSGlobalDomain').",
                },
                "key": {
                    "type": "string",
                    "description": "The preference key to set.",
                },
                "value": {
                    "type": "string",
                    "description": "The value to set.",
                },
                "value_type": {
                    "type": "string",
                    "enum": ["string", "bool", "int", "float"],
                    "description": "Type of the value. Defaults to 'string'.",
                },
            },
            "required": ["domain", "key", "value"],
        }

    async def execute(
        self,
        domain: str,
        key: str,
        value: str,
        value_type: str = "string",
    ) -> ToolResult:
        type_flags = {
            "string": ["-string", value],
            "bool": ["-bool", value],
            "int": ["-int", value],
            "float": ["-float", value],
        }
        flags = type_flags.get(value_type, ["-string", value])

        proc = await asyncio.create_subprocess_exec(
            "defaults", "write", domain, key, *flags,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            return ToolResult(
                output=f"Failed: {stderr.decode(errors='replace')}",
                success=False,
            )
        return ToolResult(output=f"Set {domain} {key} = {value} ({value_type})")
