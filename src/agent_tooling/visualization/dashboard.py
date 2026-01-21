"""
Tool Dashboard - Real-time monitoring of tool activity.

Provides a live terminal dashboard showing:
- Active tool calls
- Recent execution history
- Success/failure rates
- Performance metrics
"""

from typing import Any, Dict, List, Optional
from collections import deque
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
import threading
import time


console = Console()


class ToolDashboard:
    """
    Live dashboard for monitoring tool activity.

    Displays real-time information about tool executions,
    including success rates, timing, and recent activity.

    Example:
        dashboard = ToolDashboard()
        dashboard.start()

        # Tool executions will automatically show up
        result = my_tool.run(query="test")

        dashboard.stop()
    """

    def __init__(self, max_history: int = 20):
        self.max_history = max_history
        self.history: deque = deque(maxlen=max_history)
        self.stats: Dict[str, Dict[str, Any]] = {}
        self._running = False
        self._lock = threading.Lock()
        self._live: Optional[Live] = None

    def record(
        self,
        tool_name: str,
        success: bool,
        execution_time_ms: float,
        data: Any = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Record a tool execution.

        Args:
            tool_name: Name of the tool
            success: Whether execution succeeded
            execution_time_ms: Execution time in milliseconds
            data: Result data (optional)
            error: Error message if failed (optional)
        """
        with self._lock:
            # Add to history
            self.history.append({
                "timestamp": datetime.now(),
                "tool": tool_name,
                "success": success,
                "time_ms": execution_time_ms,
                "data": str(data)[:100] if data else None,
                "error": error,
            })

            # Update stats
            if tool_name not in self.stats:
                self.stats[tool_name] = {
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "total_time_ms": 0,
                }

            self.stats[tool_name]["total"] += 1
            self.stats[tool_name]["total_time_ms"] += execution_time_ms

            if success:
                self.stats[tool_name]["success"] += 1
            else:
                self.stats[tool_name]["failed"] += 1

    def _generate_layout(self) -> Layout:
        """Generate the dashboard layout."""
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3),
        )

        layout["main"].split_row(
            Layout(name="stats", ratio=1),
            Layout(name="history", ratio=2),
        )

        return layout

    def _render_header(self) -> Panel:
        """Render the header panel."""
        total_calls = sum(s["total"] for s in self.stats.values())
        total_success = sum(s["success"] for s in self.stats.values())
        success_rate = (total_success / total_calls * 100) if total_calls > 0 else 0

        text = Text()
        text.append("AGENT TOOLING DASHBOARD", style="bold cyan")
        text.append(f"  |  Total Calls: {total_calls}", style="white")
        text.append(f"  |  Success Rate: {success_rate:.1f}%", style="green" if success_rate > 90 else "yellow")

        return Panel(text, border_style="cyan")

    def _render_stats(self) -> Panel:
        """Render the statistics panel."""
        table = Table(show_header=True, header_style="bold")
        table.add_column("Tool", style="cyan")
        table.add_column("Calls", justify="right")
        table.add_column("Success", justify="right")
        table.add_column("Avg Time", justify="right")

        with self._lock:
            for tool, s in sorted(self.stats.items()):
                avg_time = s["total_time_ms"] / s["total"] if s["total"] > 0 else 0
                success_rate = s["success"] / s["total"] * 100 if s["total"] > 0 else 0

                rate_style = "green" if success_rate > 90 else "yellow" if success_rate > 70 else "red"

                table.add_row(
                    tool,
                    str(s["total"]),
                    f"[{rate_style}]{success_rate:.0f}%[/{rate_style}]",
                    f"{avg_time:.1f}ms",
                )

        return Panel(table, title="Tool Statistics", border_style="blue")

    def _render_history(self) -> Panel:
        """Render the history panel."""
        table = Table(show_header=True, header_style="bold")
        table.add_column("Time", style="dim")
        table.add_column("Tool", style="cyan")
        table.add_column("Status")
        table.add_column("Duration")
        table.add_column("Output", max_width=30)

        with self._lock:
            for entry in reversed(list(self.history)):
                time_str = entry["timestamp"].strftime("%H:%M:%S")
                status = "[green]OK[/green]" if entry["success"] else "[red]FAIL[/red]"
                duration = f"{entry['time_ms']:.1f}ms"
                output = entry["data"] or entry["error"] or "-"
                if len(output) > 27:
                    output = output[:27] + "..."

                table.add_row(time_str, entry["tool"], status, duration, output)

        return Panel(table, title="Recent Activity", border_style="green")

    def _render_footer(self) -> Panel:
        """Render the footer panel."""
        return Panel(
            "[dim]Press Ctrl+C to exit | Dashboard auto-refreshes every second[/dim]",
            border_style="dim",
        )

    def _render(self) -> Layout:
        """Render the complete dashboard."""
        layout = self._generate_layout()
        layout["header"].update(self._render_header())
        layout["stats"].update(self._render_stats())
        layout["history"].update(self._render_history())
        layout["footer"].update(self._render_footer())
        return layout

    def start(self) -> None:
        """Start the live dashboard."""
        self._running = True

        with Live(self._render(), refresh_per_second=1, console=console) as live:
            self._live = live
            try:
                while self._running:
                    live.update(self._render())
                    time.sleep(1)
            except KeyboardInterrupt:
                pass

        self._live = None

    def stop(self) -> None:
        """Stop the dashboard."""
        self._running = False

    def display_once(self) -> None:
        """Display the dashboard once (non-live)."""
        console.print(self._render())

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all statistics."""
        with self._lock:
            return {
                "tools": dict(self.stats),
                "total_calls": sum(s["total"] for s in self.stats.values()),
                "total_success": sum(s["success"] for s in self.stats.values()),
                "total_failed": sum(s["failed"] for s in self.stats.values()),
            }


# Global dashboard instance
_dashboard: Optional[ToolDashboard] = None


def get_dashboard() -> ToolDashboard:
    """Get or create the global dashboard instance."""
    global _dashboard
    if _dashboard is None:
        _dashboard = ToolDashboard()
    return _dashboard
