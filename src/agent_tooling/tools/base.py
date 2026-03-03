"""
Base classes for all tools in the Agent Tooling system.

BaseTool provides:
- Unified interface for tool execution
- Input/output validation via Pydantic
- Automatic JSON schema generation for MCP/function calling
- Logging and error handling
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, List, Callable
from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel
import json
import time
import traceback


console = Console()


class ToolError(Exception):
    """Exception raised when a tool execution fails."""

    def __init__(self, message: str, tool_name: str = "", details: Optional[Dict] = None):
        self.message = message
        self.tool_name = tool_name
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": True,
            "message": self.message,
            "tool_name": self.tool_name,
            "details": self.details,
        }


class ToolResult(BaseModel):
    """Standardized result from tool execution."""

    success: bool = Field(description="Whether the tool executed successfully")
    data: Any = Field(default=None, description="The result data from the tool")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    tool_name: str = Field(default="", description="Name of the tool that produced this result")
    execution_time_ms: float = Field(default=0.0, description="Execution time in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def to_llm_response(self) -> str:
        """Format the result for LLM consumption."""
        if self.success:
            if isinstance(self.data, str):
                return self.data
            return json.dumps(self.data, indent=2, default=str)
        return f"Error: {self.error}"

    def __str__(self) -> str:
        return self.to_llm_response()


class ToolParameter(BaseModel):
    """Definition of a tool parameter."""

    name: str = Field(description="Parameter name")
    type: str = Field(description="Parameter type (string, integer, number, boolean, array, object)")
    description: str = Field(description="Parameter description")
    required: bool = Field(default=True, description="Whether the parameter is required")
    default: Any = Field(default=None, description="Default value if not required")
    enum: Optional[List[Any]] = Field(default=None, description="Allowed values")


class ToolDefinition(BaseModel):
    """Complete definition of a tool for schema generation."""

    name: str = Field(description="Tool name (snake_case)")
    description: str = Field(description="What the tool does and when to use it")
    parameters: List[ToolParameter] = Field(default_factory=list, description="Tool parameters")
    category: str = Field(default="general", description="Tool category")
    mcp_enabled: bool = Field(default=True, description="Whether to expose via MCP")
    sandbox_required: bool = Field(default=False, description="Whether this tool requires sandboxed execution")

    def to_json_schema(self) -> Dict[str, Any]:
        """Generate JSON Schema for function calling / MCP."""
        properties = {}
        required = []

        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default
            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def to_openai_function(self) -> Dict[str, Any]:
        """Generate OpenAI function calling format."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.to_json_schema(),
        }

    def to_mcp_tool(self) -> Dict[str, Any]:
        """Generate MCP tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.to_json_schema(),
        }


class BaseTool(ABC):
    """
    Abstract base class for all tools.

    Tools are the actionable components that translate agent decisions into
    real-world effects. They interact with databases, APIs, file systems,
    and other external systems.

    Example:
        class MyTool(BaseTool):
            name = "my_tool"
            description = "Does something useful"

            def execute(self, **kwargs) -> ToolResult:
                # Implementation here
                return ToolResult(success=True, data="Done!")
    """

    # Class attributes to be overridden
    name: str = "base_tool"
    description: str = "Base tool - override this"
    category: str = "general"
    mcp_enabled: bool = True
    sandbox_required: bool = False

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._definition: Optional[ToolDefinition] = None

    @property
    def definition(self) -> ToolDefinition:
        """Get the tool definition with parameters."""
        if self._definition is None:
            self._definition = ToolDefinition(
                name=self.name,
                description=self.description,
                parameters=self.get_parameters(),
                category=self.category,
                mcp_enabled=self.mcp_enabled,
                sandbox_required=self.sandbox_required,
            )
        return self._definition

    @abstractmethod
    def get_parameters(self) -> List[ToolParameter]:
        """Define the parameters this tool accepts."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with the given parameters.

        Returns:
            ToolResult with success status and data/error
        """
        pass

    def validate_inputs(self, **kwargs) -> Dict[str, Any]:
        """
        Validate and normalize input parameters.

        Raises:
            ToolError: If validation fails
        """
        validated = {}

        for param in self.get_parameters():
            if param.name in kwargs:
                validated[param.name] = kwargs[param.name]
            elif param.required:
                raise ToolError(
                    f"Missing required parameter: {param.name}",
                    tool_name=self.name,
                    details={"parameter": param.name}
                )
            elif param.default is not None:
                validated[param.name] = param.default

        return validated

    def run(self, **kwargs) -> ToolResult:
        """
        Run the tool with validation and error handling.

        This is the main entry point for tool execution.
        """
        start_time = time.perf_counter()

        try:
            # Validate inputs
            validated = self.validate_inputs(**kwargs)

            # Log execution
            if self.verbose:
                self.log_call(validated)

            # Execute
            result = self.execute(**validated)
            result.tool_name = self.name

            # Calculate execution time
            result.execution_time_ms = (time.perf_counter() - start_time) * 1000

            # Log result
            if self.verbose:
                self.log_result(result)

            return result

        except ToolError as e:
            return ToolResult(
                success=False,
                error=e.message,
                tool_name=self.name,
                metadata=e.details,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name,
                metadata={"traceback": traceback.format_exc()},
            )

    def __call__(self, **kwargs) -> ToolResult:
        """Allow calling tool instance directly."""
        return self.run(**kwargs)

    def log_call(self, params: Dict[str, Any]) -> None:
        """Log tool invocation."""
        console.print(
            Panel(
                f"[bold cyan]Parameters:[/bold cyan] {json.dumps(params, indent=2, default=str)}",
                title=f"[yellow]Tool Call: {self.name}[/yellow]",
                border_style="cyan",
            )
        )

    def log_result(self, result: ToolResult) -> None:
        """Log tool result."""
        style = "green" if result.success else "red"
        status = "SUCCESS" if result.success else "FAILED"
        console.print(
            Panel(
                f"[bold {style}]{status}[/bold {style}] ({result.execution_time_ms:.2f}ms)\n"
                f"{result.to_llm_response()[:500]}",
                title=f"[yellow]Tool Result: {self.name}[/yellow]",
                border_style=style,
            )
        )

    def to_json_schema(self) -> Dict[str, Any]:
        """Get JSON schema for this tool."""
        return self.definition.to_json_schema()

    def to_openai_function(self) -> Dict[str, Any]:
        """Get OpenAI function calling format."""
        return self.definition.to_openai_function()

    def to_mcp_tool(self) -> Dict[str, Any]:
        """Get MCP tool format."""
        return self.definition.to_mcp_tool()
