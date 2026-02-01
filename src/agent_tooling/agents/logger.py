"""
Session Logger - Logs all agent interactions for traceability.

Provides both JSONL file logging and Rich terminal display.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table


class SessionLogger:
    """
    Logs agent sessions to JSONL files and displays in terminal.

    All messages, tool calls, and tool results are logged with timestamps
    for complete session traceability.
    """

    def __init__(
        self,
        log_dir: Optional[str] = None,
        console: Optional[Console] = None,
        verbose: bool = True,
    ):
        """
        Initialize the session logger.

        Args:
            log_dir: Directory for log files (default: ~/.agent-tooling/logs/)
            console: Rich console for terminal output (creates one if not provided)
            verbose: Whether to display tool calls/results in terminal
        """
        self.console = console or Console()
        self.verbose = verbose

        # Set up log directory
        if log_dir is None:
            log_dir = os.path.expanduser("~/.agent-tooling/logs")
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create session log file
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = self.log_dir / f"session_{timestamp}.jsonl"
        self.session_start = datetime.now()

    def _write_log(self, entry: Dict[str, Any]) -> None:
        """Write a log entry to the JSONL file."""
        entry["timestamp"] = datetime.now().isoformat()
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def log_user_message(self, content: str) -> None:
        """Log a user message."""
        self._write_log({
            "type": "user_message",
            "content": content,
        })

    def log_assistant_message(
        self,
        content: str,
        tool_calls: Optional[List[Dict]] = None,
    ) -> None:
        """Log an assistant message."""
        entry = {
            "type": "assistant_message",
            "content": content,
        }
        if tool_calls:
            entry["tool_calls"] = tool_calls
        self._write_log(entry)

    def log_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> None:
        """Log a tool call."""
        self._write_log({
            "type": "tool_call",
            "tool": tool_name,
            "input": tool_input,
        })

        if self.verbose:
            self._display_tool_call(tool_name, tool_input)

    def log_tool_result(
        self,
        tool_name: str,
        success: bool,
        data: Any,
        execution_time_ms: float,
        error: Optional[str] = None,
    ) -> None:
        """Log a tool result."""
        entry = {
            "type": "tool_result",
            "tool": tool_name,
            "success": success,
            "execution_time_ms": execution_time_ms,
        }
        if success:
            entry["data"] = data
        else:
            entry["error"] = error
        self._write_log(entry)

        if self.verbose:
            self._display_tool_result(tool_name, success, data, execution_time_ms, error)

    def log_error(self, error: str, context: Optional[Dict] = None) -> None:
        """Log an error."""
        entry = {
            "type": "error",
            "error": error,
        }
        if context:
            entry["context"] = context
        self._write_log(entry)

    def _display_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> None:
        """Display a tool call in the terminal."""
        # Format input as JSON
        input_str = json.dumps(tool_input, indent=2, default=str)

        # Truncate long inputs
        if len(input_str) > 500:
            input_str = input_str[:500] + "\n... (truncated)"

        self.console.print(
            Panel(
                input_str,
                title=f"[bold cyan]Tool Call: {tool_name}[/bold cyan]",
                border_style="cyan",
            )
        )

    def _display_tool_result(
        self,
        tool_name: str,
        success: bool,
        data: Any,
        execution_time_ms: float,
        error: Optional[str] = None,
    ) -> None:
        """Display a tool result in the terminal."""
        if success:
            status = f"[bold green]Success[/bold green] ({execution_time_ms:.1f}ms)"
            border_style = "green"

            # Format data
            if isinstance(data, str):
                content = data
            else:
                content = json.dumps(data, indent=2, default=str)

            # Truncate long outputs
            if len(content) > 500:
                content = content[:500] + "\n... (truncated)"
        else:
            status = f"[bold red]Failed[/bold red] ({execution_time_ms:.1f}ms)"
            border_style = "red"
            content = f"Error: {error}"

        self.console.print(
            Panel(
                f"{status}\n{content}",
                title=f"[bold]Tool Result: {tool_name}[/bold]",
                border_style=border_style,
            )
        )

    def display_session_info(
        self,
        model: str,
        base_url: str,
        tool_count: int,
    ) -> None:
        """Display session information banner."""
        self.console.print(
            Panel(
                f"[bold]Model:[/bold] {model} @ {base_url}\n"
                f"[bold]Tools:[/bold] {tool_count} loaded\n"
                f"[bold]Logging:[/bold] {self.log_file}",
                title="[bold blue]Agent Tooling - Ollama Chat[/bold blue]",
                border_style="blue",
            )
        )
        self.console.print(
            "[dim]Type 'exit' to quit, 'clear' to reset conversation[/dim]\n"
        )

    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the current session."""
        # Read log file and count entries
        entries = {"user_message": 0, "assistant_message": 0, "tool_call": 0, "tool_result": 0}

        if self.log_file.exists():
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        entry_type = entry.get("type", "unknown")
                        if entry_type in entries:
                            entries[entry_type] += 1
                    except json.JSONDecodeError:
                        continue

        duration = datetime.now() - self.session_start

        return {
            "log_file": str(self.log_file),
            "duration_seconds": duration.total_seconds(),
            "message_count": entries["user_message"] + entries["assistant_message"],
            "tool_calls": entries["tool_call"],
            **entries,
        }
