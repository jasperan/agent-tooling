"""
File System Tools - Read, write, and navigate the file system.
"""

import os
from pathlib import Path
from typing import List, Optional

from agent_tooling.tools.decorator import tool
from agent_tooling.tools.base import ToolResult, ToolError


@tool(name="read_file", category="developer", mcp_enabled=True)
def read_file(path: str, encoding: str = "utf-8") -> str:
    """Read the contents of a file.

    Args:
        path: Path to the file to read
        encoding: File encoding (default: utf-8)

    Returns:
        The contents of the file as a string
    """
    try:
        file_path = Path(path).expanduser().resolve()

        if not file_path.exists():
            raise ToolError(f"File not found: {path}", tool_name="read_file")

        if not file_path.is_file():
            raise ToolError(f"Not a file: {path}", tool_name="read_file")

        with open(file_path, "r", encoding=encoding) as f:
            return f.read()

    except ToolError:
        raise
    except Exception as e:
        raise ToolError(str(e), tool_name="read_file")


@tool(name="write_file", category="developer", mcp_enabled=True)
def write_file(path: str, content: str, encoding: str = "utf-8") -> dict:
    """Write content to a file.

    Args:
        path: Path to the file to write
        content: Content to write to the file
        encoding: File encoding (default: utf-8)

    Returns:
        Dictionary with file path and bytes written
    """
    try:
        file_path = Path(path).expanduser().resolve()

        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding=encoding) as f:
            bytes_written = f.write(content)

        return {
            "path": str(file_path),
            "bytes_written": bytes_written,
            "success": True,
        }

    except Exception as e:
        raise ToolError(str(e), tool_name="write_file")


@tool(name="list_directory", category="developer", mcp_enabled=True)
def list_directory(
    path: str = ".",
    pattern: str = "*",
    recursive: bool = False,
) -> List[dict]:
    """List files and directories in a path.

    Args:
        path: Directory path to list (default: current directory)
        pattern: Glob pattern to filter files (default: *)
        recursive: Whether to search recursively (default: false)

    Returns:
        List of file/directory information dictionaries
    """
    try:
        dir_path = Path(path).expanduser().resolve()

        if not dir_path.exists():
            raise ToolError(f"Directory not found: {path}", tool_name="list_directory")

        if not dir_path.is_dir():
            raise ToolError(f"Not a directory: {path}", tool_name="list_directory")

        if recursive:
            items = list(dir_path.rglob(pattern))
        else:
            items = list(dir_path.glob(pattern))

        results = []
        for item in sorted(items):
            try:
                stat = item.stat()
                results.append({
                    "name": item.name,
                    "path": str(item),
                    "is_file": item.is_file(),
                    "is_dir": item.is_dir(),
                    "size": stat.st_size if item.is_file() else None,
                    "modified": stat.st_mtime,
                })
            except (PermissionError, OSError):
                results.append({
                    "name": item.name,
                    "path": str(item),
                    "error": "Permission denied",
                })

        return results

    except ToolError:
        raise
    except Exception as e:
        raise ToolError(str(e), tool_name="list_directory")


@tool(name="file_exists", category="developer", mcp_enabled=True)
def file_exists(path: str) -> dict:
    """Check if a file or directory exists.

    Args:
        path: Path to check

    Returns:
        Dictionary with existence and type information
    """
    try:
        file_path = Path(path).expanduser().resolve()

        return {
            "path": str(file_path),
            "exists": file_path.exists(),
            "is_file": file_path.is_file() if file_path.exists() else False,
            "is_dir": file_path.is_dir() if file_path.exists() else False,
        }

    except Exception as e:
        raise ToolError(str(e), tool_name="file_exists")
