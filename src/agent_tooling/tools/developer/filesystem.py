"""
File System Tools - Read, write, and navigate the file system.
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from agent_tooling.tools.decorator import tool
from agent_tooling.tools.base import ToolResult, ToolError

SAMPLES = {
    "read_file": [
        {
            "name": "read_self",
            "description": "Read this tool's own source file",
            "input": {"path": __file__},
        },
    ],
    "list_directory": [
        {
            "name": "list_cwd",
            "description": "List files in the current directory",
            "input": {"path": ".", "pattern": "*.py"},
        },
    ],
    "file_exists": [
        {
            "name": "check_readme",
            "description": "Check if README.md exists",
            "input": {"path": "README.md"},
        },
    ],
    "write_file": [
        {
            "name": "write_temp",
            "description": "Write a temporary file",
            "input": {"path": "/tmp/agent_tooling_demo.txt", "content": "Hello from agent-tooling!"},
            "requires": "destructive",
        },
    ],
    "edit_file": [
        {
            "name": "edit_example",
            "description": "Example text replacement",
            "input": {"path": "/tmp/agent_tooling_demo.txt", "edits": [{"old_text": "Hello", "new_text": "Hi"}]},
            "requires": "destructive",
        },
    ],
    "search_files": [
        {
            "name": "search_imports",
            "description": "Search for import statements in current directory",
            "input": {"pattern": "from agent_tooling", "path": ".", "include_glob": "*.py", "max_results": 5},
        },
    ],
    "create_directory": [
        {
            "name": "create_temp_dir",
            "description": "Create a temporary directory",
            "input": {"path": "/tmp/agent_tooling_demo_dir"},
            "requires": "destructive",
        },
    ],
    "delete_path": [
        {
            "name": "delete_temp",
            "description": "Delete a temporary file",
            "input": {"path": "/tmp/agent_tooling_demo.txt"},
            "requires": "destructive",
        },
    ],
    "move_path": [
        {
            "name": "move_example",
            "description": "Move/rename a file",
            "input": {"source": "/tmp/agent_tooling_demo.txt", "destination": "/tmp/agent_tooling_demo_moved.txt"},
            "requires": "destructive",
        },
    ],
    "copy_path": [
        {
            "name": "copy_example",
            "description": "Copy a file",
            "input": {"source": "/tmp/agent_tooling_demo.txt", "destination": "/tmp/agent_tooling_demo_copy.txt"},
            "requires": "destructive",
        },
    ],
    "get_file_info": [
        {
            "name": "info_self",
            "description": "Get info about this tool's source file",
            "input": {"path": __file__},
        },
    ],
}


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


@tool(name="edit_file", category="developer", mcp_enabled=True)
def edit_file(path: str, edits: List[dict]) -> dict:
    """Apply text replacements to a file.

    Each edit specifies text to find and text to replace it with.
    All edits are applied in order.

    Args:
        path: Path to the file to edit
        edits: List of edits, each with 'old_text' and 'new_text' keys

    Returns:
        Dictionary with edit results
    """
    try:
        file_path = Path(path).expanduser().resolve()

        if not file_path.exists():
            raise ToolError(f"File not found: {path}", tool_name="edit_file")

        if not file_path.is_file():
            raise ToolError(f"Not a file: {path}", tool_name="edit_file")

        # Read current content
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content
        edits_applied = []

        for i, edit in enumerate(edits):
            if "old_text" not in edit or "new_text" not in edit:
                raise ToolError(
                    f"Edit {i} missing 'old_text' or 'new_text'",
                    tool_name="edit_file"
                )

            old_text = edit["old_text"]
            new_text = edit["new_text"]

            if old_text not in content:
                edits_applied.append({
                    "index": i,
                    "success": False,
                    "reason": "old_text not found in file",
                })
                continue

            content = content.replace(old_text, new_text, 1)
            edits_applied.append({
                "index": i,
                "success": True,
                "old_text_preview": old_text[:50] + "..." if len(old_text) > 50 else old_text,
            })

        # Write updated content
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "path": str(file_path),
            "edits_applied": edits_applied,
            "total_edits": len(edits),
            "successful_edits": sum(1 for e in edits_applied if e["success"]),
        }

    except ToolError:
        raise
    except Exception as e:
        raise ToolError(str(e), tool_name="edit_file")


@tool(name="search_files", category="developer", mcp_enabled=True)
def search_files(
    pattern: str,
    path: str = ".",
    regex: bool = False,
    include_glob: str = "*",
    max_results: int = 100,
) -> List[dict]:
    """Search for a pattern in files.

    Args:
        pattern: Text or regex pattern to search for
        path: Directory to search in (default: current directory)
        regex: Whether to treat pattern as regex (default: false)
        include_glob: Glob pattern to filter files (default: *)
        max_results: Maximum number of results to return (default: 100)

    Returns:
        List of matches with file path, line number, and content
    """
    try:
        search_path = Path(path).expanduser().resolve()

        if not search_path.exists():
            raise ToolError(f"Path not found: {path}", tool_name="search_files")

        if regex:
            try:
                compiled_pattern = re.compile(pattern)
            except re.error as e:
                raise ToolError(f"Invalid regex: {e}", tool_name="search_files")
        else:
            compiled_pattern = None

        results = []

        # Get files to search
        if search_path.is_file():
            files = [search_path]
        else:
            files = list(search_path.rglob(include_glob))

        for file_path in files:
            if not file_path.is_file():
                continue

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        match_found = False

                        if regex:
                            if compiled_pattern.search(line):
                                match_found = True
                        else:
                            if pattern in line:
                                match_found = True

                        if match_found:
                            results.append({
                                "file": str(file_path),
                                "line": line_num,
                                "content": line.rstrip(),
                            })

                            if len(results) >= max_results:
                                return results

            except (PermissionError, OSError):
                continue

        return results

    except ToolError:
        raise
    except Exception as e:
        raise ToolError(str(e), tool_name="search_files")


@tool(name="create_directory", category="developer", mcp_enabled=True)
def create_directory(path: str) -> dict:
    """Create a directory and any necessary parent directories.

    Args:
        path: Path of the directory to create

    Returns:
        Dictionary with creation result
    """
    try:
        dir_path = Path(path).expanduser().resolve()

        if dir_path.exists():
            return {
                "path": str(dir_path),
                "created": False,
                "reason": "already exists",
                "is_dir": dir_path.is_dir(),
            }

        dir_path.mkdir(parents=True, exist_ok=True)

        return {
            "path": str(dir_path),
            "created": True,
        }

    except Exception as e:
        raise ToolError(str(e), tool_name="create_directory")


@tool(name="delete_path", category="developer", mcp_enabled=True)
def delete_path(path: str, recursive: bool = False) -> dict:
    """Delete a file or directory.

    Args:
        path: Path to delete
        recursive: If true, delete directories and their contents (default: false)

    Returns:
        Dictionary with deletion result
    """
    try:
        target_path = Path(path).expanduser().resolve()

        if not target_path.exists():
            raise ToolError(f"Path not found: {path}", tool_name="delete_path")

        if target_path.is_file():
            target_path.unlink()
            return {
                "path": str(target_path),
                "deleted": True,
                "type": "file",
            }

        if target_path.is_dir():
            if recursive:
                shutil.rmtree(target_path)
                return {
                    "path": str(target_path),
                    "deleted": True,
                    "type": "directory",
                    "recursive": True,
                }
            else:
                # Try to remove empty directory
                try:
                    target_path.rmdir()
                    return {
                        "path": str(target_path),
                        "deleted": True,
                        "type": "directory",
                    }
                except OSError:
                    raise ToolError(
                        f"Directory not empty. Use recursive=true to delete: {path}",
                        tool_name="delete_path"
                    )

        raise ToolError(f"Unknown path type: {path}", tool_name="delete_path")

    except ToolError:
        raise
    except Exception as e:
        raise ToolError(str(e), tool_name="delete_path")


@tool(name="move_path", category="developer", mcp_enabled=True)
def move_path(source: str, destination: str) -> dict:
    """Move or rename a file or directory.

    Args:
        source: Source path to move
        destination: Destination path

    Returns:
        Dictionary with move result
    """
    try:
        src_path = Path(source).expanduser().resolve()
        dst_path = Path(destination).expanduser().resolve()

        if not src_path.exists():
            raise ToolError(f"Source not found: {source}", tool_name="move_path")

        # Create parent directories if needed
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(src_path), str(dst_path))

        return {
            "source": str(src_path),
            "destination": str(dst_path),
            "success": True,
        }

    except ToolError:
        raise
    except Exception as e:
        raise ToolError(str(e), tool_name="move_path")


@tool(name="copy_path", category="developer", mcp_enabled=True)
def copy_path(source: str, destination: str, recursive: bool = True) -> dict:
    """Copy a file or directory.

    Args:
        source: Source path to copy
        destination: Destination path
        recursive: If true, copy directories recursively (default: true)

    Returns:
        Dictionary with copy result
    """
    try:
        src_path = Path(source).expanduser().resolve()
        dst_path = Path(destination).expanduser().resolve()

        if not src_path.exists():
            raise ToolError(f"Source not found: {source}", tool_name="copy_path")

        # Create parent directories if needed
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        if src_path.is_file():
            shutil.copy2(str(src_path), str(dst_path))
            return {
                "source": str(src_path),
                "destination": str(dst_path),
                "type": "file",
                "success": True,
            }

        if src_path.is_dir():
            if recursive:
                shutil.copytree(str(src_path), str(dst_path))
                return {
                    "source": str(src_path),
                    "destination": str(dst_path),
                    "type": "directory",
                    "recursive": True,
                    "success": True,
                }
            else:
                raise ToolError(
                    f"Source is a directory. Use recursive=true to copy: {source}",
                    tool_name="copy_path"
                )

        raise ToolError(f"Unknown path type: {source}", tool_name="copy_path")

    except ToolError:
        raise
    except Exception as e:
        raise ToolError(str(e), tool_name="copy_path")


@tool(name="get_file_info", category="developer", mcp_enabled=True)
def get_file_info(path: str) -> dict:
    """Get detailed information about a file or directory.

    Args:
        path: Path to get information about

    Returns:
        Dictionary with file metadata
    """
    try:
        file_path = Path(path).expanduser().resolve()

        if not file_path.exists():
            raise ToolError(f"Path not found: {path}", tool_name="get_file_info")

        stat = file_path.stat()

        info = {
            "path": str(file_path),
            "name": file_path.name,
            "is_file": file_path.is_file(),
            "is_dir": file_path.is_dir(),
            "is_symlink": file_path.is_symlink(),
            "size_bytes": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
            "permissions": oct(stat.st_mode)[-3:],
        }

        if file_path.is_file():
            info["extension"] = file_path.suffix

        if file_path.is_dir():
            try:
                info["children_count"] = len(list(file_path.iterdir()))
            except PermissionError:
                info["children_count"] = None

        return info

    except ToolError:
        raise
    except Exception as e:
        raise ToolError(str(e), tool_name="get_file_info")
