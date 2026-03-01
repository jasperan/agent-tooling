"""
Ollama Agent - Uses Ollama's Anthropic-compatible API for tool calling.

This agent demonstrates how to use Ollama with the Anthropic SDK format
for function calling / tool use.
"""

import os
from typing import Any, Dict, List, Optional

import anthropic
from rich.console import Console
from rich.markdown import Markdown

from agent_tooling.tools.registry import ToolRegistry
from agent_tooling.tools.base import BaseTool, ToolResult
from agent_tooling.agents.logger import SessionLogger


# Default configuration
DEFAULT_MODEL = "qwen3-coder"
DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaAgent:
    """
    An agent that uses Ollama's Anthropic-compatible API for tool calling.

    The agent maintains conversation history and executes tools automatically
    when the model requests them, continuing the conversation until the model
    produces a final text response.

    Example:
        agent = OllamaAgent()
        response = agent.chat("Create a file called hello.py with a greeting")
        print(response)
    """

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None,
        system_prompt: Optional[str] = None,
        logger: Optional[SessionLogger] = None,
        console: Optional[Console] = None,
        verbose: bool = True,
    ):
        """
        Initialize the Ollama agent.

        Args:
            model: Model name (default: from OLLAMA_MODEL env or 'qwen3-coder')
            base_url: Ollama base URL (default: from OLLAMA_BASE_URL env or 'http://localhost:11434')
            tools: List of tools to use (default: all registered MCP-enabled tools)
            system_prompt: System prompt for the agent
            logger: Session logger for traceability
            console: Rich console for output
            verbose: Whether to show tool calls/results
        """
        self.model = model or os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)
        self.base_url = base_url or os.environ.get("OLLAMA_BASE_URL", DEFAULT_BASE_URL)
        self.verbose = verbose
        self.console = console or Console()

        # Set up Anthropic client pointing to Ollama
        self.client = anthropic.Anthropic(
            api_key="ollama",  # Required but not validated by Ollama
            base_url=self.base_url,
        )

        # Set up tools
        if tools is None:
            self.tools = ToolRegistry.get_mcp_tools()
        else:
            self.tools = tools

        self._tools_by_name = {tool.name: tool for tool in self.tools}
        self._tools_schema: Optional[List[Dict[str, Any]]] = None

        # Set up system prompt
        if system_prompt is None:
            self.system_prompt = self._default_system_prompt()
        else:
            self.system_prompt = system_prompt

        # Conversation history
        self.messages: List[Dict[str, Any]] = []

        # Set up logger
        self.logger = logger or SessionLogger(console=self.console, verbose=verbose)

    def _default_system_prompt(self) -> str:
        """Generate a default system prompt describing available tools."""
        tool_names = [tool.name for tool in self.tools]
        return (
            "You are a helpful assistant with access to tools for file system operations. "
            "Use the available tools to help the user with their tasks. "
            "When you need to read, write, edit, or search files, use the appropriate tools. "
            f"Available tools: {', '.join(tool_names)}"
        )

    def _get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get Anthropic-format tool schemas for all tools (cached)."""
        if self._tools_schema is None:
            self._tools_schema = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.definition.to_json_schema(),
                }
                for tool in self.tools
            ]
        return self._tools_schema

    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> ToolResult:
        """Execute a tool and return the result."""
        tool = self._tools_by_name.get(tool_name)

        if tool is None:
            return ToolResult(
                success=False,
                error=f"Unknown tool: {tool_name}",
                tool_name=tool_name,
            )

        # Log the tool call
        self.logger.log_tool_call(tool_name, tool_input)

        # Execute the tool
        result = tool.run(**tool_input)

        # Log the result
        self.logger.log_tool_result(
            tool_name=tool_name,
            success=result.success,
            data=result.data,
            execution_time_ms=result.execution_time_ms,
            error=result.error,
        )

        return result

    def chat(self, user_message: str) -> str:
        """
        Send a message and get a response, executing tools as needed.

        The agent will continue executing tools and calling the model
        until a final text response is produced.

        Args:
            user_message: The user's message

        Returns:
            The assistant's final text response
        """
        # Log user message
        self.logger.log_user_message(user_message)

        # Add user message to history
        self.messages.append({
            "role": "user",
            "content": user_message,
        })

        # Get tool schemas
        tools_schema = self._get_tools_schema()

        # Agent loop - continue until we get a text response without tool calls
        while True:
            try:
                # Call the model
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=self.system_prompt,
                    tools=tools_schema,
                    messages=self.messages,
                )
            except anthropic.APIConnectionError as e:
                error_msg = f"Failed to connect to Ollama at {self.base_url}. Is Ollama running?"
                self.logger.log_error(error_msg, {"exception": str(e)})
                return f"Error: {error_msg}"
            except anthropic.APIError as e:
                error_msg = f"API error: {e}"
                self.logger.log_error(error_msg, {"exception": str(e)})
                return f"Error: {error_msg}"

            # Process the response
            assistant_content = []
            tool_calls = []
            text_response = ""

            for block in response.content:
                if block.type == "text":
                    text_response += block.text
                    assistant_content.append({
                        "type": "text",
                        "text": block.text,
                    })
                elif block.type == "tool_use":
                    tool_calls.append({
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

            # Add assistant message to history
            self.messages.append({
                "role": "assistant",
                "content": assistant_content,
            })

            # Log assistant message
            self.logger.log_assistant_message(text_response, tool_calls if tool_calls else None)

            # If no tool calls, we're done
            if not tool_calls:
                return text_response

            # Execute tools and add results
            tool_results = []
            for tool_call in tool_calls:
                result = self._execute_tool(tool_call["name"], tool_call["input"])
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call["id"],
                    "content": result.to_llm_response(),
                })

            # Add tool results to history
            self.messages.append({
                "role": "user",
                "content": tool_results,
            })

            # Continue the loop to get the next response

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.messages = []

    def display_response(self, response: str) -> None:
        """Display the assistant's response with markdown formatting."""
        self.console.print()
        self.console.print(Markdown(response))
        self.console.print()

    def run_interactive(self) -> None:
        """
        Run an interactive chat session.

        This is the main entry point for the CLI chat command.
        """
        # Display session info
        self.logger.display_session_info(
            model=self.model,
            base_url=self.base_url,
            tool_count=len(self.tools),
        )

        while True:
            try:
                # Get user input
                user_input = self.console.input("[bold green]You:[/bold green] ")

                # Handle special commands
                if user_input.lower().strip() == "exit":
                    summary = self.logger.get_session_summary()
                    self.console.print(
                        f"\n[dim]Session ended. {summary['tool_calls']} tool calls made. "
                        f"Log saved to {summary['log_file']}[/dim]"
                    )
                    break

                if user_input.lower().strip() == "clear":
                    self.clear_history()
                    self.console.print("[dim]Conversation history cleared.[/dim]\n")
                    continue

                if not user_input.strip():
                    continue

                # Get and display response
                response = self.chat(user_input)
                self.display_response(response)

            except KeyboardInterrupt:
                self.console.print("\n[dim]Interrupted. Type 'exit' to quit.[/dim]")
                continue
            except EOFError:
                break
