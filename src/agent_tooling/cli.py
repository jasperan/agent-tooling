"""
Agent Tooling CLI - Interactive command-line interface.

Provides:
- Interactive tool exploration and execution
- Arena mode for tool comparison
- Dashboard for monitoring
- MCP server management
"""

import os
import sys
from typing import Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
import json

# Import after setting up path
try:
    import inquirer
    HAS_INQUIRER = True
except ImportError:
    HAS_INQUIRER = False

from agent_tooling.tools.registry import ToolRegistry
from agent_tooling.interceptor import ToolingInterceptor
from agent_tooling.visualization.arena import ToolArena
from agent_tooling.visualization.dashboard import ToolDashboard
from agent_tooling.visualization.traces import ToolTracer
from agent_tooling.agents.ollama import OllamaAgent


console = Console()


def _select_from_list(choices: list, message: str = "Select an option") -> Optional[str]:
    """Present a selection list using inquirer (or fallback to numbered input)."""
    if HAS_INQUIRER:
        questions = [inquirer.List("selection", message=message, choices=choices)]
        answers = inquirer.prompt(questions)
        if not answers:
            return None
        return answers["selection"]
    else:
        for i, name in enumerate(choices, 1):
            console.print(f"  {i}. {name}")
        choice = Prompt.ask("Enter number", default="1")
        try:
            return choices[int(choice) - 1]
        except (ValueError, IndexError):
            console.print("[red]Invalid selection[/red]")
            return None


def print_banner():
    """Print the CLI banner."""
    banner = """
╭────────────────────────────────────────────╮
│ AGENT TOOLING CLI                          │
│ The Tooling Layer of the AI Agent Stack    │
╰────────────────────────────────────────────╯
    """
    console.print(banner, style="cyan")


def list_tools_command():
    """List all available tools."""
    tools = ToolRegistry.list_tools()

    if not tools:
        console.print("[yellow]No tools registered yet.[/yellow]")
        console.print("[dim]Import tool modules or use @tool decorator to register tools.[/dim]")
        return

    # Group by category
    by_category = {}
    for tool in tools:
        cat = tool.get("category", "general")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(tool)

    for category, cat_tools in sorted(by_category.items()):
        table = Table(title=f"{category.upper()} Tools", show_header=True, header_style="bold magenta")
        table.add_column("Name", style="cyan")
        table.add_column("Description", max_width=50)
        table.add_column("MCP", justify="center")
        table.add_column("Params")

        for tool in cat_tools:
            mcp = "[green]✓[/green]" if tool.get("mcp_enabled") else "[dim]-[/dim]"
            params = ", ".join(p["name"] for p in tool.get("parameters", []))
            table.add_row(tool["name"], tool["description"][:50], mcp, params)

        console.print(table)
        console.print()


def run_tool_command():
    """Run a specific tool interactively."""
    tools = ToolRegistry.list_tools()

    if not tools:
        console.print("[yellow]No tools available.[/yellow]")
        return

    # Select tool
    tool_names = [t["name"] for t in tools]
    tool_name = _select_from_list(tool_names, "Select a tool to run")
    if tool_name is None:
        return

    tool = ToolRegistry.get(tool_name)
    if not tool:
        console.print(f"[red]Tool not found: {tool_name}[/red]")
        return

    # Show tool info
    console.print(Panel(
        f"[bold]{tool.name}[/bold]\n{tool.description}",
        title="Tool Info",
        border_style="cyan"
    ))

    # Get parameters
    params = {}
    for param in tool.get_parameters():
        if param.required:
            value = Prompt.ask(f"[cyan]{param.name}[/cyan] ({param.type})", default=str(param.default or ""))
        else:
            value = Prompt.ask(
                f"[cyan]{param.name}[/cyan] ({param.type}, optional)",
                default=str(param.default) if param.default else ""
            )

        if value:
            # Try to parse as JSON for complex types
            if param.type in ("array", "object"):
                try:
                    params[param.name] = json.loads(value)
                except json.JSONDecodeError:
                    params[param.name] = value
            elif param.type == "integer":
                params[param.name] = int(value)
            elif param.type == "number":
                params[param.name] = float(value)
            elif param.type == "boolean":
                params[param.name] = value.lower() in ("true", "yes", "1")
            else:
                params[param.name] = value

    # Execute
    console.print("\n[yellow]Executing...[/yellow]")
    result = tool.run(**params)

    # Display result
    if result.success:
        console.print(Panel(
            str(result.data),
            title="[green]Result[/green]",
            border_style="green"
        ))
    else:
        console.print(Panel(
            result.error or "Unknown error",
            title="[red]Error[/red]",
            border_style="red"
        ))

    console.print(f"[dim]Execution time: {result.execution_time_ms:.2f}ms[/dim]")


def arena_command():
    """Run arena mode to compare tools."""
    tools = ToolRegistry.list_tools()

    if len(tools) < 2:
        console.print("[yellow]Need at least 2 tools for arena mode.[/yellow]")
        return

    tool_names = [t["name"] for t in tools]

    if HAS_INQUIRER:
        questions = [
            inquirer.Checkbox(
                "tools",
                message="Select tools to compare (space to select, enter to confirm)",
                choices=tool_names,
            )
        ]
        answers = inquirer.prompt(questions)
        if not answers or len(answers["tools"]) < 2:
            console.print("[yellow]Select at least 2 tools.[/yellow]")
            return
        selected = answers["tools"]
    else:
        console.print("Select tools to compare (comma-separated numbers):")
        for i, name in enumerate(tool_names, 1):
            console.print(f"  {i}. {name}")
        choices = Prompt.ask("Enter tool numbers", default="1,2")
        try:
            indices = [int(x.strip()) - 1 for x in choices.split(",")]
            selected = [tool_names[i] for i in indices]
        except (ValueError, IndexError):
            console.print("[red]Invalid selection[/red]")
            return

    # Get common parameters
    console.print("\n[cyan]Enter parameters for the comparison:[/cyan]")
    params = {}

    # Use first tool's parameters as template
    first_tool = ToolRegistry.get(selected[0])
    if first_tool:
        for param in first_tool.get_parameters():
            value = Prompt.ask(f"[cyan]{param.name}[/cyan]", default="")
            if value:
                params[param.name] = value

    # Run arena
    arena = ToolArena(verbose=True)
    arena.compare(selected, **params)


def dashboard_command():
    """Show the live dashboard."""
    console.print("[cyan]Starting dashboard... (Ctrl+C to exit)[/cyan]")
    dashboard = ToolDashboard()
    dashboard.start()


def mcp_server_command():
    """Start the MCP server."""
    from agent_tooling.mcp.server import MCPServer

    console.print("[cyan]Starting MCP server in stdio mode...[/cyan]")
    console.print("[dim]Connect from your MCP client (Claude, etc.)[/dim]")

    server = MCPServer()
    server.run_stdio()


def show_schemas_command():
    """Show JSON schemas for all tools."""
    tools = ToolRegistry.list_tools()

    for tool_info in tools:
        tool = ToolRegistry.get(tool_info["name"])
        if tool:
            schema = tool.to_openai_function()
            console.print(Panel(
                json.dumps(schema, indent=2),
                title=f"[cyan]{tool.name}[/cyan] - OpenAI Function Schema",
                border_style="blue"
            ))


def chat_command(verbose: bool = True):
    """Start an interactive chat session with the Ollama agent."""
    try:
        agent = OllamaAgent(verbose=verbose)
        agent.run_interactive()
    except KeyboardInterrupt:
        console.print("\n[dim]Chat session ended.[/dim]")
    except Exception as e:
        console.print(f"[red]Error starting chat: {e}[/red]")
        console.print("[dim]Make sure Ollama is running and the model is available.[/dim]")


def _create_sample_pdf() -> str:
    """Create a small sample PDF in a temp directory for demo purposes."""
    import tempfile
    try:
        import pymupdf
    except ImportError:
        return ""

    tmp_dir = tempfile.mkdtemp(prefix="agent_tooling_demo_")
    pdf_path = os.path.join(tmp_dir, "sample.pdf")
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Agent Tooling - Sample Document", fontsize=20)
    page.insert_text((72, 120), "Introduction", fontsize=15)
    page.insert_text(
        (72, 150),
        "This is a sample PDF generated by agent-tooling for demonstration purposes. "
        "It contains headings and body text to showcase the PDF-to-markdown conversion tool.",
    )
    page.insert_text((72, 200), "Key Features", fontsize=15)
    page.insert_text((72, 230), "1. Automatic heading detection based on font size")
    page.insert_text((72, 250), "2. Page-by-page extraction with page range support")
    page.insert_text((72, 270), "3. Clean markdown output suitable for LLM consumption")
    doc.save(pdf_path)
    doc.close()
    return pdf_path


def demo_command(include_network: bool = False, include_ollama: bool = False,
                 include_destructive: bool = False, output_json: bool = False):
    """Run tool demos with sample inputs."""
    all_tools = ToolRegistry.list_tools()

    if not all_tools:
        console.print("[yellow]No tools registered.[/yellow]")
        return

    # Pre-generate sample PDF for tools that need it
    sample_pdf_path = ""
    results_log = []  # For JSON output

    # Group tools by category
    by_category = {}
    for tool_info in all_tools:
        cat = tool_info.get("category", "general")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(tool_info)

    total_run = 0
    total_skipped = 0

    for category in sorted(by_category.keys()):
        cat_tools = by_category[category]
        cat_printed = False

        for tool_info in cat_tools:
            tool_name = tool_info["name"]
            samples = ToolRegistry.get_samples(tool_name)

            if not samples:
                continue

            if not cat_printed:
                console.print(f"\n[bold magenta]{'=' * 60}[/bold magenta]")
                console.print(f"[bold magenta]  {category.upper()} TOOLS[/bold magenta]")
                console.print(f"[bold magenta]{'=' * 60}[/bold magenta]")
                cat_printed = True

            tool_obj = ToolRegistry.get(tool_name)
            if not tool_obj:
                continue

            for sample in samples:
                requires = sample.get("requires", "")
                sample_name = sample["name"]
                sample_desc = sample["description"]
                sample_input = dict(sample["input"])

                # Check skip conditions
                skip_reason = None
                if requires == "network" and not include_network:
                    skip_reason = "requires --demo-network"
                elif requires == "ollama" and not include_ollama:
                    skip_reason = "requires --demo-ollama"
                elif requires == "destructive" and not include_destructive:
                    skip_reason = "requires --demo-destructive"

                if skip_reason:
                    total_skipped += 1
                    if not output_json:
                        console.print(
                            f"\n  [dim][skip] {tool_name} / {sample_name} — {skip_reason}[/dim]"
                        )
                    results_log.append({
                        "tool": tool_name,
                        "sample": sample_name,
                        "description": sample_desc,
                        "input": sample_input,
                        "skipped": True,
                        "skip_reason": skip_reason,
                    })
                    continue

                # Handle __auto_pdf__ sentinel
                for key, val in sample_input.items():
                    if val == "__auto_pdf__":
                        if not sample_pdf_path:
                            sample_pdf_path = _create_sample_pdf()
                        if not sample_pdf_path:
                            skip_reason = "pymupdf not installed"
                            break
                        sample_input[key] = sample_pdf_path

                if skip_reason:
                    total_skipped += 1
                    if not output_json:
                        console.print(
                            f"\n  [dim][skip] {tool_name} / {sample_name} — {skip_reason}[/dim]"
                        )
                    continue

                # Run the sample
                if not output_json:
                    console.print(f"\n  [bold cyan]{tool_name}[/bold cyan] / [yellow]{sample_name}[/yellow]")
                    console.print(f"  [dim]{sample_desc}[/dim]")
                    input_str = json.dumps(sample_input, indent=2, default=str)
                    console.print(Panel(
                        input_str,
                        title="[cyan]Input[/cyan]",
                        border_style="cyan",
                        width=80,
                    ))

                result = tool_obj.run(**sample_input)
                total_run += 1

                if not output_json:
                    if result.success:
                        output_str = result.to_llm_response()
                        # Truncate very long output
                        if len(output_str) > 1500:
                            output_str = output_str[:1500] + "\n... (truncated)"
                        console.print(Panel(
                            output_str,
                            title=f"[green]Output[/green] [dim]({result.execution_time_ms:.1f}ms)[/dim]",
                            border_style="green",
                            width=80,
                        ))
                    else:
                        console.print(Panel(
                            result.error or "Unknown error",
                            title="[red]Error[/red]",
                            border_style="red",
                            width=80,
                        ))

                results_log.append({
                    "tool": tool_name,
                    "sample": sample_name,
                    "description": sample_desc,
                    "input": sample_input,
                    "skipped": False,
                    "success": result.success,
                    "output": result.data if result.success else None,
                    "error": result.error if not result.success else None,
                    "execution_time_ms": result.execution_time_ms,
                })

    # Summary
    console.print(f"\n[bold]Demo complete:[/bold] {total_run} run, {total_skipped} skipped")
    if total_skipped > 0:
        flags = []
        if not include_network:
            flags.append("--demo-network")
        if not include_ollama:
            flags.append("--demo-ollama")
        if not include_destructive:
            flags.append("--demo-destructive")
        console.print(f"[dim]Use {' '.join(flags)} to include skipped tools[/dim]")

    if output_json:
        print(json.dumps(results_log, indent=2, default=str))

    # Clean up temp PDF
    if sample_pdf_path:
        import shutil
        shutil.rmtree(os.path.dirname(sample_pdf_path), ignore_errors=True)


def main_menu():
    """Display the main menu."""
    choices = [
        ("Chat with Agent", chat_command),
        ("List Tools", list_tools_command),
        ("Run Tool", run_tool_command),
        ("Demo: Run Samples", lambda: demo_command()),
        ("Arena: Compare Tools", arena_command),
        ("Dashboard", dashboard_command),
        ("MCP Server", mcp_server_command),
        ("Show Schemas", show_schemas_command),
        ("Exit", None),
    ]

    while True:
        labels = [c[0] for c in choices]
        selected = _select_from_list(labels, "Select an action")
        if selected is None:
            break

        for label, func in choices:
            if label == selected:
                if func is None:
                    return
                func()
                break

        console.print()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Agent Tooling CLI")
    parser.add_argument("--chat", "-c", action="store_true", help="Start interactive chat with Ollama agent")
    parser.add_argument("--list", "-l", action="store_true", help="List all tools")
    parser.add_argument("--run", "-r", metavar="TOOL", help="Run a specific tool")
    parser.add_argument("--arena", "-a", action="store_true", help="Start arena mode")
    parser.add_argument("--dashboard", "-d", action="store_true", help="Start dashboard")
    parser.add_argument("--mcp", "-m", action="store_true", help="Start MCP server")
    parser.add_argument("--schemas", "-s", action="store_true", help="Show tool schemas")
    parser.add_argument("--demo", action="store_true", help="Run tool demos with sample inputs")
    parser.add_argument("--demo-network", action="store_true", help="Include network-dependent tools in demo")
    parser.add_argument("--demo-ollama", action="store_true", help="Include Ollama-dependent tools in demo")
    parser.add_argument("--demo-destructive", action="store_true", help="Include destructive tools in demo")
    parser.add_argument("--demo-all", action="store_true", help="Include all tools in demo (network + ollama + destructive)")
    parser.add_argument("--demo-json", action="store_true", help="Output demo results as JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output (show tool calls/results)")

    args = parser.parse_args()

    # Load built-in tools
    try:
        from agent_tooling.tools import developer, data, cognitive, media
    except ImportError:
        pass

    if args.chat:
        chat_command(verbose=args.verbose)
    elif args.demo or args.demo_json:
        print_banner()
        use_all = args.demo_all
        demo_command(
            include_network=use_all or args.demo_network,
            include_ollama=use_all or args.demo_ollama,
            include_destructive=use_all or args.demo_destructive,
            output_json=args.demo_json,
        )
    elif args.list:
        print_banner()
        list_tools_command()
    elif args.run:
        print_banner()
        tool = ToolRegistry.get(args.run)
        if tool:
            console.print(f"[cyan]Running {args.run}...[/cyan]")
            # Would need params from stdin or args
            console.print("[yellow]Use interactive mode for tool execution with parameters.[/yellow]")
        else:
            console.print(f"[red]Tool not found: {args.run}[/red]")
    elif args.arena:
        print_banner()
        arena_command()
    elif args.dashboard:
        print_banner()
        dashboard_command()
    elif args.mcp:
        mcp_server_command()
    elif args.schemas:
        print_banner()
        show_schemas_command()
    else:
        print_banner()
        main_menu()


if __name__ == "__main__":
    main()
