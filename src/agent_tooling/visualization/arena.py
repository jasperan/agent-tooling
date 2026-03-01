"""
Tool Arena - Compare multiple tools side-by-side.

Similar to agent-reasoning's arena mode, this allows comparing
different tools or tool configurations on the same task.
"""

from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.live import Live
from rich.layout import Layout

from agent_tooling.tools.registry import ToolRegistry
from agent_tooling.tools.base import ToolResult


console = Console()


class ToolArena:
    """
    Arena for comparing tools side-by-side.

    Run multiple tools with the same inputs and compare their
    outputs, execution times, and success rates.

    Example:
        arena = ToolArena()
        arena.compare(
            tools=["web_search", "wikipedia_search"],
            query="What is machine learning?"
        )
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.results: List[Dict[str, Any]] = []

    def compare(
        self,
        tools: List[str],
        **kwargs,
    ) -> List[ToolResult]:
        """
        Compare multiple tools with the same inputs.

        Args:
            tools: List of tool names to compare
            **kwargs: Parameters to pass to all tools

        Returns:
            List of ToolResults from each tool
        """
        self.results = []
        results = []

        if self.verbose:
            console.print(
                Panel(
                    f"[bold cyan]Comparing {len(tools)} tools[/bold cyan]",
                    title="[yellow]TOOL ARENA[/yellow]",
                    border_style="yellow",
                )
            )
            console.print(f"[dim]Parameters: {kwargs}[/dim]\n")

        for tool_name in tools:
            tool = ToolRegistry.get(tool_name)
            if tool is None:
                result = ToolResult(
                    success=False,
                    error=f"Tool not found: {tool_name}",
                    tool_name=tool_name,
                )
            else:
                if self.verbose:
                    console.print(f"[cyan]Running {tool_name}...[/cyan]")

                result = tool.run(**kwargs)

            results.append(result)
            self.results.append({
                "tool": tool_name,
                "success": result.success,
                "time_ms": result.execution_time_ms,
                "data": result.data,
                "error": result.error,
            })

        if self.verbose:
            self._display_comparison()

        return results

    def _display_comparison(self) -> None:
        """Display comparison table."""
        console.print()

        # Summary table
        table = Table(title="Arena Results", show_header=True, header_style="bold magenta")
        table.add_column("Tool", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Time (ms)", justify="right")
        table.add_column("Output Preview", max_width=50)

        for r in self.results:
            status = "[green]SUCCESS[/green]" if r["success"] else "[red]FAILED[/red]"
            time_str = f"{r['time_ms']:.2f}"

            output = str(r["data"] if r["success"] else r["error"])
            if len(output) > 47:
                output = output[:47] + "..."

            table.add_row(r["tool"], status, time_str, output)

        console.print(table)

        # Winner announcement
        successful = [r for r in self.results if r["success"]]
        if successful:
            fastest = min(successful, key=lambda x: x["time_ms"])
            console.print(
                f"\n[bold green]Fastest:[/bold green] {fastest['tool']} "
                f"({fastest['time_ms']:.2f}ms)"
            )

    def run_benchmark(
        self,
        tools: List[str],
        test_cases: List[Dict[str, Any]],
        iterations: int = 3,
    ) -> Dict[str, Any]:
        """
        Run a full benchmark across multiple test cases.

        Args:
            tools: List of tool names
            test_cases: List of parameter dicts for each test
            iterations: Number of times to run each test

        Returns:
            Benchmark results with statistics
        """
        all_results = {tool: [] for tool in tools}

        for i, test_case in enumerate(test_cases):
            if self.verbose:
                console.print(f"\n[bold]Test Case {i + 1}/{len(test_cases)}[/bold]")

            for _ in range(iterations):
                results = self.compare(tools, **test_case)
                for tool, result in zip(tools, results):
                    all_results[tool].append({
                        "success": result.success,
                        "time_ms": result.execution_time_ms,
                    })

        # Calculate statistics
        stats = {}
        for tool, results in all_results.items():
            successes = [r for r in results if r["success"]]
            stats[tool] = {
                "total_runs": len(results),
                "successes": len(successes),
                "success_rate": len(successes) / len(results) if results else 0,
                "avg_time_ms": sum(r["time_ms"] for r in successes) / len(successes) if successes else 0,
                "min_time_ms": min(r["time_ms"] for r in successes) if successes else 0,
                "max_time_ms": max(r["time_ms"] for r in successes) if successes else 0,
            }

        if self.verbose:
            self._display_benchmark_stats(stats)

        return stats

    def _display_benchmark_stats(self, stats: Dict[str, Any]) -> None:
        """Display benchmark statistics."""
        console.print("\n")

        table = Table(title="Benchmark Statistics", show_header=True, header_style="bold magenta")
        table.add_column("Tool", style="cyan")
        table.add_column("Success Rate", justify="right")
        table.add_column("Avg Time", justify="right")
        table.add_column("Min Time", justify="right")
        table.add_column("Max Time", justify="right")

        for tool, s in stats.items():
            rate = f"{s['success_rate'] * 100:.1f}%"
            avg = f"{s['avg_time_ms']:.2f}ms"
            min_t = f"{s['min_time_ms']:.2f}ms"
            max_t = f"{s['max_time_ms']:.2f}ms"

            table.add_row(tool, rate, avg, min_t, max_t)

        console.print(table)
