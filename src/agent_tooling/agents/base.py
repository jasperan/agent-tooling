"""
BaseAgent — multi-provider agent with workspace-aware tool execution.

Uses OpenHands' LLM class when available for provider-agnostic LLM access.
Falls back to Anthropic SDK (Ollama-compatible) when OpenHands is not installed.
"""

import os
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.markdown import Markdown

from agent_tooling.tools.registry import ToolRegistry
from agent_tooling.tools.base import BaseTool, ToolResult
from agent_tooling.workspace.base import Workspace
from agent_tooling.workspace.local import LocalWorkspace
from agent_tooling.agents.logger import SessionLogger

try:
    from openhands.sdk import LLM
    HAS_OPENHANDS_SDK = True
except ImportError:
    HAS_OPENHANDS_SDK = False


class BaseAgent:
    """
    Multi-provider agent with workspace-aware tool execution.

    Model format: "provider/model-name"
    Examples:
        - "ollama/qwen3-coder" (default)
        - "anthropic/claude-sonnet-4-20250514"
        - "openai/gpt-4o"
    """

    def __init__(
        self,
        model: Optional[str] = None,
        workspace: Optional[Workspace] = None,
        tools: Optional[List[BaseTool]] = None,
        system_prompt: Optional[str] = None,
        logger: Optional[SessionLogger] = None,
        console: Optional[Console] = None,
        verbose: bool = True,
    ):
        self.model = model or os.environ.get("AGENT_MODEL", "ollama/qwen3-coder")
        self.workspace = workspace or LocalWorkspace()
        self.verbose = verbose
        self.console = console or Console()

        # Parse provider/model
        if "/" in self.model:
            self._provider, self._model_name = self.model.split("/", 1)
        else:
            self._provider = "ollama"
            self._model_name = self.model

        # Set up tools
        if tools is None:
            self.tools = ToolRegistry.get_mcp_tools()
        else:
            self.tools = tools
        self._tools_by_name = {tool.name: tool for tool in self.tools}
        self._tools_schema: Optional[List[Dict[str, Any]]] = None

        # System prompt
        self.system_prompt = system_prompt or self._default_system_prompt()

        # Conversation history
        self.messages: List[Dict[str, Any]] = []

        # Logger
        self.logger = logger or SessionLogger(console=self.console, verbose=verbose)

        # Set up LLM client
        self._client = None
        self._init_client()

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def model_name(self) -> str:
        return self._model_name

    def _default_system_prompt(self) -> str:
        tool_names = [tool.name for tool in self.tools]
        return (
            "You are a helpful assistant with access to tools. "
            "Use the available tools to help the user with their tasks. "
            f"Available tools: {', '.join(tool_names)}"
        )

    def _init_client(self):
        """Initialize the LLM client based on provider."""
        if HAS_OPENHANDS_SDK:
            self._client = LLM(model=self.model)
        else:
            import anthropic
            if self._provider == "ollama":
                base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
                self._client = anthropic.Anthropic(
                    api_key="ollama",
                    base_url=base_url,
                )
            elif self._provider == "anthropic":
                self._client = anthropic.Anthropic()
            else:
                raise ValueError(
                    f"Provider '{self._provider}' requires OpenHands SDK. "
                    "Install with: pip install agent-tooling-layer[openhands]"
                )

    def _get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get Anthropic-format tool schemas (cached)."""
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
        """Execute a tool through the workspace."""
        tool = self._tools_by_name.get(tool_name)
        if tool is None:
            return ToolResult(
                success=False,
                error=f"Unknown tool: {tool_name}",
                tool_name=tool_name,
            )

        self.logger.log_tool_call(tool_name, tool_input)
        result = self.workspace.execute_tool(tool, **tool_input)
        self.logger.log_tool_result(
            tool_name=tool_name,
            success=result.success,
            data=result.data,
            execution_time_ms=result.execution_time_ms,
            error=result.error,
        )
        return result

    def chat(self, user_message: str) -> str:
        """Send a message and get a response, executing tools as needed."""
        self.logger.log_user_message(user_message)
        self.messages.append({"role": "user", "content": user_message})
        tools_schema = self._get_tools_schema()

        while True:
            try:
                response = self._client.messages.create(
                    model=self._model_name,
                    max_tokens=4096,
                    system=self.system_prompt,
                    tools=tools_schema,
                    messages=self.messages,
                )
            except Exception as e:
                error_msg = f"LLM error ({self.model}): {e}"
                self.logger.log_error(error_msg, {"exception": str(e)})
                return f"Error: {error_msg}"

            assistant_content = []
            tool_calls = []
            text_response = ""

            for block in response.content:
                if block.type == "text":
                    text_response += block.text
                    assistant_content.append({"type": "text", "text": block.text})
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

            self.messages.append({"role": "assistant", "content": assistant_content})
            self.logger.log_assistant_message(
                text_response, tool_calls if tool_calls else None
            )

            if not tool_calls:
                return text_response

            tool_results = []
            for tc in tool_calls:
                result = self._execute_tool(tc["name"], tc["input"])
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc["id"],
                    "content": result.to_llm_response(),
                })

            self.messages.append({"role": "user", "content": tool_results})

    def clear_history(self) -> None:
        self.messages = []

    def display_response(self, response: str) -> None:
        self.console.print()
        self.console.print(Markdown(response))
        self.console.print()

    def run_interactive(self) -> None:
        """Run an interactive chat session."""
        self.logger.display_session_info(
            model=self.model,
            base_url=getattr(self._client, '_base_url', self.model),
            tool_count=len(self.tools),
        )

        while True:
            try:
                user_input = self.console.input("[bold green]You:[/bold green] ")

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

                response = self.chat(user_input)
                self.display_response(response)

            except KeyboardInterrupt:
                self.console.print("\n[dim]Interrupted. Type 'exit' to quit.[/dim]")
                continue
            except EOFError:
                break
