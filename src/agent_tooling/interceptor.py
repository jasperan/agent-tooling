"""
ToolingInterceptor - Routes tool calls to appropriate handlers.

Similar to ReasoningInterceptor in agent-reasoning, this provides a
unified interface for executing tools, whether they come from:
- Direct Python calls
- LLM function calling responses
- MCP protocol requests
"""

from typing import Any, Dict, List, Optional, Union
import json
import re

from agent_tooling.tools.base import BaseTool, ToolResult, ToolError
from agent_tooling.tools.registry import ToolRegistry


class ToolingInterceptor:
    """
    Intercepts and routes tool calls to the appropriate handlers.

    This is the main entry point for tool execution in applications.
    It handles:
    - Tool lookup and validation
    - Parameter parsing from various formats
    - Execution and result formatting
    - Logging and tracing
    """

    def __init__(self, verbose: bool = False):
        """
        Initialize the interceptor.

        Args:
            verbose: Whether to enable verbose logging
        """
        self.verbose = verbose
        self._trace: List[Dict[str, Any]] = []

    @property
    def trace(self) -> List[Dict[str, Any]]:
        """Get the execution trace."""
        return self._trace

    def clear_trace(self) -> None:
        """Clear the execution trace."""
        self._trace = []

    def execute(
        self,
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> ToolResult:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters as a dictionary (or use kwargs)
            **kwargs: Parameters as keyword arguments

        Returns:
            ToolResult from the tool execution
        """
        # Merge parameters
        params = {**(parameters or {}), **kwargs}

        # Get tool
        tool = ToolRegistry.get(tool_name)
        if tool is None:
            return ToolResult(
                success=False,
                error=f"Tool not found: {tool_name}",
                tool_name=tool_name,
            )

        # Execute
        tool.verbose = self.verbose
        result = tool.run(**params)

        # Record trace
        self._trace.append({
            "tool": tool_name,
            "parameters": params,
            "success": result.success,
            "execution_time_ms": result.execution_time_ms,
        })

        return result

    def execute_function_call(self, function_call: Dict[str, Any]) -> ToolResult:
        """
        Execute a tool from an OpenAI-style function call.

        Args:
            function_call: Dict with 'name' and 'arguments' keys
                Example: {"name": "query_database", "arguments": '{"sql": "SELECT..."}'}

        Returns:
            ToolResult from the tool execution
        """
        name = function_call.get("name", "")
        arguments = function_call.get("arguments", "{}")

        # Parse arguments if string
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                return ToolResult(
                    success=False,
                    error=f"Failed to parse arguments: {arguments}",
                    tool_name=name,
                )

        return self.execute(name, arguments)

    def execute_tool_call(self, tool_call: Dict[str, Any]) -> ToolResult:
        """
        Execute a tool from an OpenAI-style tool call.

        Args:
            tool_call: Dict with 'function' key containing name and arguments
                Example: {"function": {"name": "...", "arguments": "..."}}

        Returns:
            ToolResult from the tool execution
        """
        function = tool_call.get("function", {})
        return self.execute_function_call(function)

    def parse_and_execute(self, text: str) -> List[ToolResult]:
        """
        Parse tool calls from text and execute them.

        Supports various formats:
        - Action: tool_name[arguments]  (ReAct format)
        - <tool>tool_name</tool><args>{"key": "value"}</args>  (XML format)
        - ```tool\n{"name": "...", "arguments": {...}}\n```  (Markdown format)

        Args:
            text: Text potentially containing tool calls

        Returns:
            List of ToolResults from executed tools
        """
        results = []

        # ReAct format: Action: tool_name[arguments]
        react_pattern = r'Action:\s*(\w+)\[([^\]]*)\]'
        for match in re.finditer(react_pattern, text):
            tool_name = match.group(1)
            args_str = match.group(2)

            # Try to parse as JSON, otherwise use as single argument
            try:
                args = json.loads(args_str) if args_str.startswith("{") else {"input": args_str}
            except json.JSONDecodeError:
                args = {"input": args_str}

            results.append(self.execute(tool_name, args))

        # XML format: <tool>name</tool><args>{...}</args>
        xml_pattern = r'<tool>(\w+)</tool>\s*<args>({[^}]+})</args>'
        for match in re.finditer(xml_pattern, text):
            tool_name = match.group(1)
            try:
                args = json.loads(match.group(2))
            except json.JSONDecodeError:
                args = {}
            results.append(self.execute(tool_name, args))

        return results

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of all available tools."""
        return ToolRegistry.list_tools()

    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get the JSON schema for a specific tool."""
        tool = ToolRegistry.get(tool_name)
        if tool:
            return tool.to_json_schema()
        return None

    def get_openai_functions(self, tools: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get OpenAI function calling format for tools."""
        return ToolRegistry.to_openai_functions(tools)

    def get_mcp_tools(self, tools: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get MCP tool format for tools."""
        return ToolRegistry.to_mcp_tools(tools)


# Global interceptor instance
_interceptor: Optional[ToolingInterceptor] = None


def get_interceptor(verbose: bool = False) -> ToolingInterceptor:
    """Get or create the global interceptor instance."""
    global _interceptor
    if _interceptor is None:
        _interceptor = ToolingInterceptor(verbose=verbose)
    return _interceptor


def execute_tool(tool_name: str, **kwargs) -> ToolResult:
    """Convenience function to execute a tool."""
    return get_interceptor().execute(tool_name, **kwargs)
