"""
Tool Registry - Central registry for all available tools.

The registry provides:
- Tool discovery and lookup
- Category-based organization
- MCP tool listing
- Schema generation for all registered tools
"""

from typing import Any, Dict, List, Optional, Type, Union
from agent_tooling.tools.base import BaseTool, ToolDefinition


class ToolRegistry:
    """
    Global registry of all available tools.

    Tools are automatically registered when using the @tool decorator.
    They can also be registered manually using ToolRegistry.register().
    """

    _tools: Dict[str, BaseTool] = {}
    _categories: Dict[str, List[str]] = {}
    _samples: Dict[str, List[Dict[str, Any]]] = {}

    @classmethod
    def register(cls, tool: BaseTool) -> None:
        """
        Register a tool in the registry.

        Args:
            tool: The tool instance to register
        """
        cls._tools[tool.name] = tool

        # Track by category
        if tool.category not in cls._categories:
            cls._categories[tool.category] = []
        if tool.name not in cls._categories[tool.category]:
            cls._categories[tool.category].append(tool.name)

    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        Remove a tool from the registry.

        Args:
            name: Name of the tool to remove

        Returns:
            True if tool was removed, False if not found
        """
        if name not in cls._tools:
            return False

        tool = cls._tools[name]
        del cls._tools[name]

        # Remove from category
        if tool.category in cls._categories:
            cls._categories[tool.category] = [
                n for n in cls._categories[tool.category] if n != name
            ]

        return True

    @classmethod
    def get(cls, name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.

        Args:
            name: Name of the tool

        Returns:
            The tool instance or None if not found
        """
        return cls._tools.get(name)

    @classmethod
    def get_all(cls) -> Dict[str, BaseTool]:
        """Get all registered tools."""
        return cls._tools.copy()

    @classmethod
    def get_by_category(cls, category: str) -> List[BaseTool]:
        """
        Get all tools in a category.

        Args:
            category: Category name

        Returns:
            List of tools in the category
        """
        tool_names = cls._categories.get(category, [])
        return [cls._tools[name] for name in tool_names if name in cls._tools]

    @classmethod
    def get_categories(cls) -> List[str]:
        """Get all registered categories."""
        return list(cls._categories.keys())

    @classmethod
    def get_mcp_tools(cls) -> List[BaseTool]:
        """Get all tools that are MCP-enabled."""
        return [tool for tool in cls._tools.values() if tool.mcp_enabled]

    @classmethod
    def list_tools(cls) -> List[Dict[str, Any]]:
        """
        List all tools with their metadata.

        Returns:
            List of tool information dictionaries
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "category": tool.category,
                "mcp_enabled": tool.mcp_enabled,
                "parameters": [p.model_dump() for p in tool.get_parameters()],
            }
            for tool in cls._tools.values()
        ]

    @classmethod
    def to_openai_functions(cls, tools: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Generate OpenAI function calling format for specified or all tools.

        Args:
            tools: List of tool names (None for all tools)

        Returns:
            List of function definitions in OpenAI format
        """
        if tools is None:
            tool_list = list(cls._tools.values())
        else:
            tool_list = [cls._tools[name] for name in tools if name in cls._tools]

        return [tool.to_openai_function() for tool in tool_list]

    @classmethod
    def to_mcp_tools(cls, tools: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Generate MCP tool format for specified or all MCP-enabled tools.

        Args:
            tools: List of tool names (None for all MCP-enabled tools)

        Returns:
            List of tool definitions in MCP format
        """
        if tools is None:
            tool_list = cls.get_mcp_tools()
        else:
            tool_list = [
                cls._tools[name]
                for name in tools
                if name in cls._tools and cls._tools[name].mcp_enabled
            ]

        return [tool.to_mcp_tool() for tool in tool_list]

    @classmethod
    def register_samples(cls, tool_name: str, samples: List[Dict[str, Any]]) -> None:
        """
        Register sample inputs for a tool.

        Args:
            tool_name: Name of the tool
            samples: List of sample dicts with 'name', 'description', 'input', and
                     optional 'requires' (e.g. 'network', 'ollama', 'destructive')
        """
        cls._samples[tool_name] = samples

    @classmethod
    def get_samples(cls, tool_name: str) -> List[Dict[str, Any]]:
        """
        Get sample inputs for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            List of sample dicts, or empty list if none registered
        """
        return cls._samples.get(tool_name, [])

    @classmethod
    def get_all_samples(cls) -> Dict[str, List[Dict[str, Any]]]:
        """Get all registered samples keyed by tool name."""
        return cls._samples.copy()

    @classmethod
    def clear(cls) -> None:
        """Clear all registered tools."""
        cls._tools.clear()
        cls._categories.clear()
        cls._samples.clear()

    @classmethod
    def count(cls) -> int:
        """Get number of registered tools."""
        return len(cls._tools)


# Convenience alias
TOOL_MAP = ToolRegistry._tools


def get_tool(name: str) -> Optional[BaseTool]:
    """Convenience function to get a tool by name."""
    return ToolRegistry.get(name)


def list_tools() -> List[Dict[str, Any]]:
    """Convenience function to list all tools."""
    return ToolRegistry.list_tools()


def run_tool(name: str, **kwargs) -> Any:
    """
    Run a tool by name with the given parameters.

    Args:
        name: Name of the tool to run
        **kwargs: Parameters to pass to the tool

    Returns:
        ToolResult from the tool execution

    Raises:
        KeyError: If tool not found
    """
    tool = ToolRegistry.get(name)
    if tool is None:
        raise KeyError(f"Tool not found: {name}")
    return tool.run(**kwargs)
