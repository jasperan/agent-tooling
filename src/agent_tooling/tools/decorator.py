"""
The @tool decorator - unified tool definition for both direct Python and MCP usage.

This is the primary way to define tools in agent-tooling. The decorator
automatically handles:
- Parameter extraction from function signature and docstring
- JSON schema generation for function calling
- MCP server registration
- Input validation
- Error handling
"""

import inspect
import functools
from typing import Any, Callable, Dict, List, Optional, get_type_hints, Union
from pydantic import BaseModel
import re

from agent_tooling.tools.base import (
    BaseTool,
    ToolResult,
    ToolError,
    ToolParameter,
    ToolDefinition,
)
from agent_tooling.tools.registry import ToolRegistry


# Type mapping from Python types to JSON Schema types
PYTHON_TO_JSON_TYPE = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
    List: "array",
    Dict: "object",
    Any: "string",  # Default to string for Any
}


def _get_json_type(python_type: type) -> str:
    """Convert Python type to JSON Schema type."""
    # Handle Optional types
    origin = getattr(python_type, "__origin__", None)
    if origin is Union:
        args = getattr(python_type, "__args__", ())
        # Filter out NoneType for Optional
        non_none = [a for a in args if a is not type(None)]
        if non_none:
            return _get_json_type(non_none[0])

    # Handle generic types like List[str], Dict[str, int]
    if origin is not None:
        if origin in (list, List):
            return "array"
        if origin in (dict, Dict):
            return "object"

    return PYTHON_TO_JSON_TYPE.get(python_type, "string")


def _parse_docstring(docstring: str) -> Dict[str, str]:
    """
    Parse docstring to extract parameter descriptions.

    Supports Google-style docstrings:
        Args:
            param1: Description of param1
            param2: Description of param2

    Returns:
        Dict mapping parameter names to descriptions
    """
    if not docstring:
        return {}

    descriptions = {}
    in_args = False
    current_param = None
    current_desc = []

    for line in docstring.split("\n"):
        line = line.strip()

        if line.lower().startswith("args:"):
            in_args = True
            continue
        elif line.lower().startswith(("returns:", "raises:", "example:", "note:")):
            in_args = False
            if current_param:
                descriptions[current_param] = " ".join(current_desc).strip()
            current_param = None
            continue

        if in_args:
            # Check for new parameter definition
            match = re.match(r"(\w+)\s*(?:\([^)]*\))?\s*:\s*(.*)", line)
            if match:
                if current_param:
                    descriptions[current_param] = " ".join(current_desc).strip()
                current_param = match.group(1)
                current_desc = [match.group(2)] if match.group(2) else []
            elif current_param and line:
                # Continuation of previous parameter description
                current_desc.append(line)

    if current_param:
        descriptions[current_param] = " ".join(current_desc).strip()

    return descriptions


def _extract_parameters(func: Callable) -> List[ToolParameter]:
    """Extract parameters from function signature and docstring."""
    sig = inspect.signature(func)
    type_hints = get_type_hints(func) if hasattr(func, "__annotations__") else {}
    docstring_params = _parse_docstring(func.__doc__ or "")

    parameters = []

    for name, param in sig.parameters.items():
        if name in ("self", "cls"):
            continue

        # Get type
        python_type = type_hints.get(name, str)
        json_type = _get_json_type(python_type)

        # Check if required (no default value)
        required = param.default is inspect.Parameter.empty
        default = None if required else param.default

        # Get description from docstring
        description = docstring_params.get(name, f"The {name} parameter")

        parameters.append(
            ToolParameter(
                name=name,
                type=json_type,
                description=description,
                required=required,
                default=default,
            )
        )

    return parameters


class FunctionTool(BaseTool):
    """
    A tool created from a decorated function.

    This wraps a regular Python function as a BaseTool, enabling it
    to be used both directly and via MCP.
    """

    def __init__(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: str = "general",
        mcp_enabled: bool = True,
        verbose: bool = False,
    ):
        super().__init__(verbose=verbose)
        self._func = func
        self.name = name or func.__name__
        self.description = description or (func.__doc__ or "").split("\n")[0].strip() or f"Tool: {self.name}"
        self.category = category
        self.mcp_enabled = mcp_enabled
        self._parameters = _extract_parameters(func)

    def get_parameters(self) -> List[ToolParameter]:
        return self._parameters

    def execute(self, **kwargs) -> ToolResult:
        """Execute the wrapped function."""
        try:
            result = self._func(**kwargs)

            # If function returns ToolResult, use it directly
            if isinstance(result, ToolResult):
                return result

            # Otherwise wrap in ToolResult
            return ToolResult(
                success=True,
                data=result,
                tool_name=self.name,
            )

        except ToolError:
            raise
        except Exception as e:
            raise ToolError(str(e), tool_name=self.name)


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: str = "general",
    mcp_enabled: bool = True,
    auto_register: bool = True,
) -> Callable:
    """
    Decorator to create a tool from a function.

    The decorator automatically:
    - Extracts parameters from function signature
    - Parses docstring for parameter descriptions
    - Generates JSON schema for function calling / MCP
    - Registers the tool in the global registry (optional)

    Args:
        name: Tool name (defaults to function name)
        description: Tool description (defaults to first line of docstring)
        category: Tool category for organization
        mcp_enabled: Whether to expose via MCP server
        auto_register: Whether to register in global TOOL_MAP

    Returns:
        Decorated function that is also a FunctionTool

    Example:
        @tool(name="query_database", category="data", mcp_enabled=True)
        def query_database(sql: str, connection: str = "default") -> dict:
            '''Execute SQL query against configured database.

            Args:
                sql: The SQL query to execute
                connection: Database connection name

            Returns:
                Query results as dictionary
            '''
            # Implementation here
            return {"rows": [...]}

        # Use directly:
        result = query_database(sql="SELECT * FROM users")

        # Or via tool interface:
        result = query_database.run(sql="SELECT * FROM users")

        # Get schema for function calling:
        schema = query_database.to_json_schema()
    """

    def decorator(func: Callable) -> FunctionTool:
        # Create the FunctionTool
        func_tool = FunctionTool(
            func=func,
            name=name,
            description=description,
            category=category,
            mcp_enabled=mcp_enabled,
        )

        # Make it callable like the original function
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # If called with positional args, convert to kwargs
            if args:
                sig = inspect.signature(func)
                param_names = [
                    p for p in sig.parameters.keys()
                    if p not in ("self", "cls")
                ]
                for i, arg in enumerate(args):
                    if i < len(param_names):
                        kwargs[param_names[i]] = arg
            return func_tool.run(**kwargs)

        # Copy tool attributes to wrapper
        wrapper.tool = func_tool
        wrapper.run = func_tool.run
        wrapper.execute = func_tool.execute
        wrapper.to_json_schema = func_tool.to_json_schema
        wrapper.to_openai_function = func_tool.to_openai_function
        wrapper.to_mcp_tool = func_tool.to_mcp_tool
        wrapper.definition = func_tool.definition
        wrapper.name = func_tool.name
        wrapper.description = func_tool.description
        wrapper.category = func_tool.category
        wrapper.mcp_enabled = func_tool.mcp_enabled

        # Register in global registry
        if auto_register:
            ToolRegistry.register(func_tool)

        return wrapper

    return decorator


# Convenience function for creating tools imperatively
def create_tool(
    func: Callable,
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: str = "general",
    mcp_enabled: bool = True,
    auto_register: bool = True,
) -> FunctionTool:
    """
    Create a tool from a function without using decorator syntax.

    Useful for dynamically creating tools or wrapping existing functions.
    """
    func_tool = FunctionTool(
        func=func,
        name=name,
        description=description,
        category=category,
        mcp_enabled=mcp_enabled,
    )

    if auto_register:
        ToolRegistry.register(func_tool)

    return func_tool
