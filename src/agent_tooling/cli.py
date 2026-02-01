"""
Agent Tooling CLI - Interactive command-line interface.

Provides:
- Interactive tool exploration and execution
- Arena mode for tool comparison
- Dashboard for monitoring
- MCP server management
"""

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

    if HAS_INQUIRER:
        questions = [
            inquirer.List(
                "tool",
                message="Select a tool to run",
                choices=tool_names,
            )
        ]
        answers = inquirer.prompt(questions)
        if not answers:
            return
        tool_name = answers["tool"]
    else:
        console.print("Available tools:")
        for i, name in enumerate(tool_names, 1):
            console.print(f"  {i}. {name}")
        choice = Prompt.ask("Enter tool number", default="1")
        try:
            tool_name = tool_names[int(choice) - 1]
        except (ValueError, IndexError):
            console.print("[red]Invalid selection[/red]")
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


def main_menu():
    """Display the main menu."""
    choices = [
        ("Chat with Agent", chat_command),
        ("List Tools", list_tools_command),
        ("Run Tool", run_tool_command),
        ("Arena: Compare Tools", arena_command),
        ("Dashboard", dashboard_command),
        ("MCP Server", mcp_server_command),
        ("Show Schemas", show_schemas_command),
        ("Exit", None),
    ]

    while True:
        if HAS_INQUIRER:
            questions = [
                inquirer.List(
                    "action",
                    message="Select an action",
                    choices=[c[0] for c in choices],
                )
            ]
            answers = inquirer.prompt(questions)
            if not answers:
                break

            for label, func in choices:
                if label == answers["action"]:
                    if func is None:
                        return
                    func()
                    break
        else:
            console.print("\n[bold]Main Menu:[/bold]")
            for i, (label, _) in enumerate(choices, 1):
                console.print(f"  {i}. {label}")

            choice = Prompt.ask("Select", default="1")
            try:
                idx = int(choice) - 1
                if idx == len(choices) - 1:  # Exit
                    return
                _, func = choices[idx]
                if func:
                    func()
            except (ValueError, IndexError):
                console.print("[red]Invalid selection[/red]")

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
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output (show tool calls/results)")

    args = parser.parse_args()

    # Load built-in tools
    try:
        from agent_tooling.tools import developer, data, cognitive
    except ImportError:
        pass

    if args.chat:
        chat_command(verbose=args.verbose or True)
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
