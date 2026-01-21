"""
Tool Tracer - Step-by-step visualization of tool execution.

Provides detailed traces showing:
- Input parameters
- Execution flow
- Intermediate states
- Output results
- Timing breakdown
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from rich.console import Console
from rich.tree import Tree
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
import json


console = Console()


@dataclass
class TraceStep:
    """A single step in an execution trace."""
    name: str
    step_type: str  # "input", "process", "output", "error"
    data: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Trace:
    """Complete execution trace for a tool call."""
    tool_name: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    steps: List[TraceStep] = field(default_factory=list)
    success: bool = False
    result: Any = None
    error: Optional[str] = None

    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return 0.0

    def add_step(
        self,
        name: str,
        step_type: str,
        data: Any = None,
        **metadata,
    ) -> TraceStep:
        """Add a step to the trace."""
        step = TraceStep(
            name=name,
            step_type=step_type,
            data=data,
            metadata=metadata,
        )
        self.steps.append(step)
        return step

    def complete(self, success: bool, result: Any = None, error: str = None) -> None:
        """Mark the trace as complete."""
        self.end_time = datetime.now()
        self.success = success
        self.result = result
        self.error = error


class ToolTracer:
    """
    Traces tool execution with detailed step-by-step visualization.

    Example:
        tracer = ToolTracer()

        with tracer.trace("my_tool") as trace:
            trace.add_step("parse_input", "input", {"query": "test"})
            trace.add_step("call_api", "process", {"url": "..."})
            trace.add_step("format_output", "output", {"result": "..."})

        tracer.display()
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.traces: List[Trace] = []
        self._current_trace: Optional[Trace] = None

    def trace(self, tool_name: str) -> "TraceContext":
        """
        Start a new trace context.

        Args:
            tool_name: Name of the tool being traced

        Returns:
            TraceContext for use in a with statement
        """
        return TraceContext(self, tool_name)

    def start_trace(self, tool_name: str) -> Trace:
        """Start a new trace."""
        trace = Trace(tool_name=tool_name)
        self._current_trace = trace
        self.traces.append(trace)
        return trace

    def end_trace(self, success: bool, result: Any = None, error: str = None) -> None:
        """End the current trace."""
        if self._current_trace:
            self._current_trace.complete(success, result, error)
            if self.verbose:
                self.display_trace(self._current_trace)
            self._current_trace = None

    def add_step(
        self,
        name: str,
        step_type: str,
        data: Any = None,
        **metadata,
    ) -> Optional[TraceStep]:
        """Add a step to the current trace."""
        if self._current_trace:
            return self._current_trace.add_step(name, step_type, data, **metadata)
        return None

    def display_trace(self, trace: Trace) -> None:
        """Display a single trace."""
        status_color = "green" if trace.success else "red"
        status_text = "SUCCESS" if trace.success else "FAILED"

        # Build tree
        tree = Tree(
            f"[bold cyan]{trace.tool_name}[/bold cyan] "
            f"[{status_color}]({status_text})[/{status_color}] "
            f"[dim]{trace.duration_ms:.2f}ms[/dim]"
        )

        for step in trace.steps:
            step_color = {
                "input": "blue",
                "process": "yellow",
                "output": "green",
                "error": "red",
            }.get(step.step_type, "white")

            step_node = tree.add(
                f"[{step_color}]{step.step_type.upper()}[/{step_color}]: {step.name}"
            )

            if step.data is not None:
                data_str = self._format_data(step.data)
                step_node.add(f"[dim]{data_str}[/dim]")

        # Add result or error
        if trace.success and trace.result is not None:
            result_str = self._format_data(trace.result)
            tree.add(f"[green]Result:[/green] {result_str[:100]}")
        elif trace.error:
            tree.add(f"[red]Error:[/red] {trace.error}")

        console.print(Panel(tree, title="[yellow]Execution Trace[/yellow]", border_style="cyan"))

    def _format_data(self, data: Any) -> str:
        """Format data for display."""
        if isinstance(data, str):
            return data[:200]
        try:
            return json.dumps(data, indent=2, default=str)[:200]
        except:
            return str(data)[:200]

    def display_all(self) -> None:
        """Display all traces."""
        for trace in self.traces:
            self.display_trace(trace)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics for all traces."""
        if not self.traces:
            return {"total": 0}

        successful = [t for t in self.traces if t.success]
        return {
            "total": len(self.traces),
            "successful": len(successful),
            "failed": len(self.traces) - len(successful),
            "success_rate": len(successful) / len(self.traces),
            "avg_duration_ms": sum(t.duration_ms for t in self.traces) / len(self.traces),
            "total_steps": sum(len(t.steps) for t in self.traces),
        }

    def clear(self) -> None:
        """Clear all traces."""
        self.traces.clear()
        self._current_trace = None


class TraceContext:
    """Context manager for tracing."""

    def __init__(self, tracer: ToolTracer, tool_name: str):
        self.tracer = tracer
        self.tool_name = tool_name
        self.trace: Optional[Trace] = None

    def __enter__(self) -> Trace:
        self.trace = self.tracer.start_trace(self.tool_name)
        return self.trace

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.tracer.end_trace(False, error=str(exc_val))
        else:
            self.tracer.end_trace(True, result=self.trace.result if self.trace else None)
        return False


# Global tracer instance
_tracer: Optional[ToolTracer] = None


def get_tracer() -> ToolTracer:
    """Get or create the global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = ToolTracer()
    return _tracer
