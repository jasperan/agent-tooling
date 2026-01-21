"""
Code Execution Tools - Execute Python and shell commands.

Note: These tools execute arbitrary code and should be used with caution.
Consider sandboxing in production environments.
"""

import subprocess
import sys
from typing import Optional
from io import StringIO
import traceback

from agent_tooling.tools.decorator import tool
from agent_tooling.tools.base import ToolError


@tool(name="execute_python", category="developer", mcp_enabled=True)
def execute_python(code: str, timeout: int = 30) -> dict:
    """Execute Python code and return the result.

    Args:
        code: Python code to execute
        timeout: Maximum execution time in seconds (default: 30)

    Returns:
        Dictionary with stdout, stderr, and return value
    """
    # Capture stdout and stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = StringIO()
    sys.stderr = StringIO()

    result = {
        "success": False,
        "stdout": "",
        "stderr": "",
        "return_value": None,
        "error": None,
    }

    try:
        # Create a namespace for execution
        namespace = {"__builtins__": __builtins__}

        # Execute the code
        exec(code, namespace)

        # Check for a 'result' variable
        if "result" in namespace:
            result["return_value"] = namespace["result"]

        result["success"] = True

    except Exception as e:
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()

    finally:
        result["stdout"] = sys.stdout.getvalue()
        result["stderr"] = sys.stderr.getvalue()
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return result


@tool(name="execute_shell", category="developer", mcp_enabled=True)
def execute_shell(
    command: str,
    timeout: int = 60,
    cwd: Optional[str] = None,
) -> dict:
    """Execute a shell command and return the result.

    Args:
        command: Shell command to execute
        timeout: Maximum execution time in seconds (default: 60)
        cwd: Working directory for the command (optional)

    Returns:
        Dictionary with stdout, stderr, and return code
    """
    try:
        process = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )

        return {
            "success": process.returncode == 0,
            "stdout": process.stdout,
            "stderr": process.stderr,
            "return_code": process.returncode,
        }

    except subprocess.TimeoutExpired:
        raise ToolError(
            f"Command timed out after {timeout} seconds",
            tool_name="execute_shell"
        )
    except Exception as e:
        raise ToolError(str(e), tool_name="execute_shell")
