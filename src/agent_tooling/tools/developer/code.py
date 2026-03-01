"""
Code Execution Tools - Execute Python and shell commands.

Note: These tools execute arbitrary code and should be used with caution.
Consider sandboxing in production environments.
"""

import contextlib
import subprocess
import signal
import sys
from typing import Optional
from io import StringIO
import traceback

from agent_tooling.tools.decorator import tool
from agent_tooling.tools.base import ToolError

SAMPLES = {
    "execute_python": [
        {
            "name": "sum_range",
            "description": "Compute sum of 1 to 100",
            "input": {"code": "result = sum(range(1, 101))"},
        },
        {
            "name": "list_comprehension",
            "description": "Generate squares with a list comprehension",
            "input": {"code": "result = [x**2 for x in range(10)]"},
        },
    ],
    "execute_shell": [
        {
            "name": "echo_hello",
            "description": "Echo a message",
            "input": {"command": "echo 'Hello from agent-tooling'"},
            "requires": "destructive",
        },
    ],
}


@tool(name="execute_python", category="developer", mcp_enabled=True)
def execute_python(code: str, timeout: int = 30) -> dict:
    """Execute Python code and return the result.

    Args:
        code: Python code to execute
        timeout: Maximum execution time in seconds (default: 30)

    Returns:
        Dictionary with stdout, stderr, and return value
    """
    stdout_buf = StringIO()
    stderr_buf = StringIO()

    result = {
        "success": False,
        "stdout": "",
        "stderr": "",
        "return_value": None,
        "error": None,
    }

    def _timeout_handler(signum, frame):
        raise TimeoutError(f"Code execution timed out after {timeout} seconds")

    try:
        # Set timeout via signal (Unix only; ignored on Windows)
        old_handler = None
        if hasattr(signal, "SIGALRM"):
            old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(timeout)

        # Capture stdout/stderr with context managers (safer than replacing globals)
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
            namespace = {"__builtins__": __builtins__}
            exec(code, namespace)

        if "result" in namespace:
            result["return_value"] = namespace["result"]

        result["success"] = True

    except TimeoutError as e:
        result["error"] = str(e)
    except Exception as e:
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()

    finally:
        # Cancel alarm and restore handler
        if hasattr(signal, "SIGALRM"):
            signal.alarm(0)
            if old_handler is not None:
                signal.signal(signal.SIGALRM, old_handler)
        result["stdout"] = stdout_buf.getvalue()
        result["stderr"] = stderr_buf.getvalue()

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
