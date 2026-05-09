"""File system tools — read, write, list, search, move, delete."""

from __future__ import annotations

import os
import glob as globmod
from pathlib import Path

from .base import BaseTool, RiskLevel, ToolResult


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read the contents of a file at the given path."
    risk_level = RiskLevel.SAFE

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file.",
                },
                "max_lines": {
                    "type": "integer",
                    "description": "Max lines to read. Defaults to 500.",
                },
            },
            "required": ["path"],
        }

    async def execute(self, path: str, max_lines: int = 500) -> ToolResult:
        path = os.path.expanduser(path)
        try:
            with open(path, "r", errors="replace") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append(f"\n... (truncated at {max_lines} lines)")
                        break
                    lines.append(line)
            return ToolResult(output="".join(lines))
        except FileNotFoundError:
            return ToolResult(output=f"File not found: {path}", success=False)
        except IsADirectoryError:
            return ToolResult(output=f"Path is a directory: {path}", success=False)
        except PermissionError:
            return ToolResult(output=f"Permission denied: {path}", success=False)


class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Write content to a file. Creates the file if it doesn't exist, overwrites if it does."
    risk_level = RiskLevel.RISKY

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to write.",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file.",
                },
                "append": {
                    "type": "boolean",
                    "description": "If true, append instead of overwrite. Defaults to false.",
                },
            },
            "required": ["path", "content"],
        }

    async def execute(self, path: str, content: str, append: bool = False) -> ToolResult:
        path = os.path.expanduser(path)
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append else "w"
            with open(path, mode) as f:
                f.write(content)
            action = "Appended to" if append else "Wrote"
            return ToolResult(output=f"{action} {path} ({len(content)} chars)")
        except PermissionError:
            return ToolResult(output=f"Permission denied: {path}", success=False)


class ListDirectoryTool(BaseTool):
    name = "list_directory"
    description = "List files and directories at the given path."
    risk_level = RiskLevel.SAFE

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path. Defaults to current directory.",
                },
                "show_hidden": {
                    "type": "boolean",
                    "description": "Show hidden files (dotfiles). Defaults to false.",
                },
            },
        }

    async def execute(self, path: str = ".", show_hidden: bool = False) -> ToolResult:
        path = os.path.expanduser(path)
        try:
            entries = sorted(os.listdir(path))
            if not show_hidden:
                entries = [e for e in entries if not e.startswith(".")]

            lines = []
            for entry in entries:
                full = os.path.join(path, entry)
                if os.path.isdir(full):
                    lines.append(f"  {entry}/")
                else:
                    size = os.path.getsize(full)
                    lines.append(f"  {entry}  ({_human_size(size)})")

            header = f"Contents of {path} ({len(entries)} items):"
            return ToolResult(output=header + "\n" + "\n".join(lines))
        except FileNotFoundError:
            return ToolResult(output=f"Directory not found: {path}", success=False)
        except PermissionError:
            return ToolResult(output=f"Permission denied: {path}", success=False)


class SearchFilesTool(BaseTool):
    name = "search_files"
    description = "Search for files matching a glob pattern or containing text."
    risk_level = RiskLevel.SAFE

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match files (e.g., '**/*.py').",
                },
                "directory": {
                    "type": "string",
                    "description": "Root directory to search in. Defaults to current directory.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return. Defaults to 50.",
                },
            },
            "required": ["pattern"],
        }

    async def execute(
        self, pattern: str, directory: str = ".", max_results: int = 50
    ) -> ToolResult:
        directory = os.path.expanduser(directory)
        full_pattern = os.path.join(directory, pattern)
        matches = globmod.glob(full_pattern, recursive=True)[:max_results]

        if not matches:
            return ToolResult(output=f"No files matching '{pattern}' in {directory}")

        lines = [f"Found {len(matches)} matches:"]
        for m in matches:
            lines.append(f"  {m}")
        return ToolResult(output="\n".join(lines))


class MoveFileTool(BaseTool):
    name = "move_file"
    description = "Move or rename a file or directory."
    risk_level = RiskLevel.RISKY

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source path."},
                "destination": {"type": "string", "description": "Destination path."},
            },
            "required": ["source", "destination"],
        }

    async def execute(self, source: str, destination: str) -> ToolResult:
        source = os.path.expanduser(source)
        destination = os.path.expanduser(destination)
        try:
            os.rename(source, destination)
            return ToolResult(output=f"Moved {source} -> {destination}")
        except FileNotFoundError:
            return ToolResult(output=f"Source not found: {source}", success=False)
        except PermissionError:
            return ToolResult(output=f"Permission denied", success=False)


class DeleteFileTool(BaseTool):
    name = "delete_file"
    description = "Delete a file. Use with caution — this is irreversible."
    risk_level = RiskLevel.DANGEROUS

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to delete."},
            },
            "required": ["path"],
        }

    async def execute(self, path: str) -> ToolResult:
        path = os.path.expanduser(path)
        try:
            if os.path.isdir(path):
                return ToolResult(
                    output=f"Cannot delete directory with this tool. Use shell 'rm -r' for directories.",
                    success=False,
                )
            os.remove(path)
            return ToolResult(output=f"Deleted {path}")
        except FileNotFoundError:
            return ToolResult(output=f"File not found: {path}", success=False)
        except PermissionError:
            return ToolResult(output=f"Permission denied: {path}", success=False)


def _human_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"
