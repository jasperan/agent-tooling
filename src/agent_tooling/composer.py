"""
ToolComposer - Create composite tools from atomic tools.

Enables building hierarchical tool structures where complex tools
are composed from simpler ones. This matches the whitepaper's
concept of tool composition and hierarchies.
"""

from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

from agent_tooling.tools.base import BaseTool, ToolResult, ToolError, ToolParameter
from agent_tooling.tools.registry import ToolRegistry


class CompositionMode(Enum):
    """How to combine multiple tool results."""
    SEQUENTIAL = "sequential"  # Run in order, pass output to next
    PARALLEL = "parallel"      # Run all at once, collect results
    CONDITIONAL = "conditional"  # Run based on conditions
    PIPELINE = "pipeline"      # Chain outputs to inputs


@dataclass
class ToolStep:
    """A single step in a composite tool."""
    tool_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    output_key: str = ""  # Key to store result for later steps
    input_mapping: Dict[str, str] = field(default_factory=dict)  # Map from context to params
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None  # Optional condition


class CompositeTool(BaseTool):
    """
    A tool composed of multiple other tools.

    Composite tools allow building complex workflows from atomic tools.
    They support sequential, parallel, and conditional execution patterns.

    Example:
        # Research Assistant: search -> summarize -> save
        research = CompositeTool(
            name="research_assistant",
            description="Search web, summarize, and save results",
            steps=[
                ToolStep("web_search", output_key="search_results"),
                ToolStep("summarize", input_mapping={"text": "search_results"}),
                ToolStep("save_file", input_mapping={"content": "summary"}),
            ]
        )
    """

    def __init__(
        self,
        name: str,
        description: str,
        steps: List[ToolStep],
        mode: CompositionMode = CompositionMode.SEQUENTIAL,
        category: str = "composite",
        mcp_enabled: bool = True,
        verbose: bool = False,
    ):
        super().__init__(verbose=verbose)
        self.name = name
        self.description = description
        self.steps = steps
        self.mode = mode
        self.category = category
        self.mcp_enabled = mcp_enabled
        self._parameters: Optional[List[ToolParameter]] = None

    def get_parameters(self) -> List[ToolParameter]:
        """
        Derive parameters from the first step's tool.

        For more complex cases, parameters should be explicitly defined.
        """
        if self._parameters is not None:
            return self._parameters

        # Get parameters from first step's tool
        if self.steps:
            first_tool = ToolRegistry.get(self.steps[0].tool_name)
            if first_tool:
                return first_tool.get_parameters()

        return []

    def set_parameters(self, parameters: List[ToolParameter]) -> None:
        """Explicitly set the composite tool's parameters."""
        self._parameters = parameters

    def execute(self, **kwargs) -> ToolResult:
        """Execute the composite tool based on composition mode."""
        if self.mode == CompositionMode.SEQUENTIAL:
            return self._execute_sequential(**kwargs)
        elif self.mode == CompositionMode.PARALLEL:
            return self._execute_parallel(**kwargs)
        elif self.mode == CompositionMode.PIPELINE:
            return self._execute_pipeline(**kwargs)
        elif self.mode == CompositionMode.CONDITIONAL:
            return self._execute_conditional(**kwargs)
        else:
            return ToolResult(
                success=False,
                error=f"Unknown composition mode: {self.mode}",
                tool_name=self.name,
            )

    def _execute_sequential(self, **kwargs) -> ToolResult:
        """Execute steps in sequence, collecting all results."""
        context = dict(kwargs)
        results = []
        total_time = 0.0

        for step in self.steps:
            # Check condition if present
            if step.condition and not step.condition(context):
                continue

            # Get the tool
            tool = ToolRegistry.get(step.tool_name)
            if tool is None:
                return ToolResult(
                    success=False,
                    error=f"Tool not found: {step.tool_name}",
                    tool_name=self.name,
                )

            # Build parameters from step config and context
            params = dict(step.parameters)
            for param_name, context_key in step.input_mapping.items():
                if context_key in context:
                    params[param_name] = context[context_key]

            # Execute
            result = tool.run(**params)
            total_time += result.execution_time_ms
            results.append({
                "step": step.tool_name,
                "success": result.success,
                "data": result.data,
            })

            if not result.success:
                return ToolResult(
                    success=False,
                    error=f"Step '{step.tool_name}' failed: {result.error}",
                    tool_name=self.name,
                    execution_time_ms=total_time,
                    metadata={"steps": results},
                )

            # Store result in context
            if step.output_key:
                context[step.output_key] = result.data

        return ToolResult(
            success=True,
            data=results[-1]["data"] if results else None,
            tool_name=self.name,
            execution_time_ms=total_time,
            metadata={"steps": results, "context": context},
        )

    def _execute_parallel(self, **kwargs) -> ToolResult:
        """Execute all steps in parallel (simulated - actual parallel would use asyncio)."""
        results = []
        total_time = 0.0
        all_success = True

        for step in self.steps:
            tool = ToolRegistry.get(step.tool_name)
            if tool is None:
                results.append({
                    "step": step.tool_name,
                    "success": False,
                    "error": f"Tool not found: {step.tool_name}",
                })
                all_success = False
                continue

            # Build parameters
            params = {**kwargs, **step.parameters}

            # Execute
            result = tool.run(**params)
            total_time = max(total_time, result.execution_time_ms)  # Parallel = max time
            results.append({
                "step": step.tool_name,
                "success": result.success,
                "data": result.data,
                "error": result.error,
            })

            if not result.success:
                all_success = False

        return ToolResult(
            success=all_success,
            data=[r["data"] for r in results if r["success"]],
            error="; ".join(r["error"] for r in results if r.get("error")),
            tool_name=self.name,
            execution_time_ms=total_time,
            metadata={"steps": results},
        )

    def _execute_pipeline(self, **kwargs) -> ToolResult:
        """Execute as a pipeline where each step's output is the next step's input."""
        current_input = kwargs
        total_time = 0.0
        steps_trace = []

        for step in self.steps:
            tool = ToolRegistry.get(step.tool_name)
            if tool is None:
                return ToolResult(
                    success=False,
                    error=f"Tool not found: {step.tool_name}",
                    tool_name=self.name,
                )

            # Merge step parameters with pipeline input
            params = {**step.parameters}

            # Map input from previous step
            if step.input_mapping:
                for param_name, source_key in step.input_mapping.items():
                    if source_key in current_input:
                        params[param_name] = current_input[source_key]
                    elif isinstance(current_input, dict) and source_key == "_output":
                        params[param_name] = current_input
            else:
                # Default: pass previous output as first parameter
                tool_params = tool.get_parameters()
                if tool_params and isinstance(current_input, dict):
                    first_param = tool_params[0].name
                    if first_param not in params:
                        # Try to find matching key or use entire output
                        if first_param in current_input:
                            params[first_param] = current_input[first_param]

            result = tool.run(**params)
            total_time += result.execution_time_ms
            steps_trace.append({
                "step": step.tool_name,
                "success": result.success,
            })

            if not result.success:
                return ToolResult(
                    success=False,
                    error=f"Pipeline step '{step.tool_name}' failed: {result.error}",
                    tool_name=self.name,
                    execution_time_ms=total_time,
                    metadata={"steps": steps_trace},
                )

            # Pass output to next step
            current_input = {"_output": result.data, **(result.data if isinstance(result.data, dict) else {})}

        return ToolResult(
            success=True,
            data=current_input.get("_output", current_input),
            tool_name=self.name,
            execution_time_ms=total_time,
            metadata={"steps": steps_trace},
        )

    def _execute_conditional(self, **kwargs) -> ToolResult:
        """Execute steps based on their conditions."""
        context = dict(kwargs)
        executed = []
        total_time = 0.0

        for step in self.steps:
            # Check condition
            if step.condition and not step.condition(context):
                continue

            tool = ToolRegistry.get(step.tool_name)
            if tool is None:
                continue

            params = {**step.parameters}
            for param_name, context_key in step.input_mapping.items():
                if context_key in context:
                    params[param_name] = context[context_key]

            result = tool.run(**params)
            total_time += result.execution_time_ms
            executed.append({
                "step": step.tool_name,
                "success": result.success,
                "data": result.data,
            })

            if step.output_key:
                context[step.output_key] = result.data

        return ToolResult(
            success=True,
            data=executed[-1]["data"] if executed else None,
            tool_name=self.name,
            execution_time_ms=total_time,
            metadata={"executed_steps": executed},
        )


class ToolComposer:
    """
    Factory for creating composite tools.

    Provides convenient methods for common composition patterns.
    """

    @staticmethod
    def sequential(
        name: str,
        description: str,
        tools: List[Union[str, ToolStep]],
        **kwargs,
    ) -> CompositeTool:
        """
        Create a sequential composite tool.

        Args:
            name: Name for the composite tool
            description: Description of what it does
            tools: List of tool names or ToolStep objects
        """
        steps = [
            ToolStep(tool_name=t) if isinstance(t, str) else t
            for t in tools
        ]
        return CompositeTool(
            name=name,
            description=description,
            steps=steps,
            mode=CompositionMode.SEQUENTIAL,
            **kwargs,
        )

    @staticmethod
    def parallel(
        name: str,
        description: str,
        tools: List[Union[str, ToolStep]],
        **kwargs,
    ) -> CompositeTool:
        """Create a parallel composite tool."""
        steps = [
            ToolStep(tool_name=t) if isinstance(t, str) else t
            for t in tools
        ]
        return CompositeTool(
            name=name,
            description=description,
            steps=steps,
            mode=CompositionMode.PARALLEL,
            **kwargs,
        )

    @staticmethod
    def pipeline(
        name: str,
        description: str,
        tools: List[Union[str, ToolStep]],
        **kwargs,
    ) -> CompositeTool:
        """Create a pipeline composite tool."""
        steps = [
            ToolStep(tool_name=t) if isinstance(t, str) else t
            for t in tools
        ]
        return CompositeTool(
            name=name,
            description=description,
            steps=steps,
            mode=CompositionMode.PIPELINE,
            **kwargs,
        )

    @staticmethod
    def register_composite(tool: CompositeTool) -> CompositeTool:
        """Register a composite tool in the registry."""
        ToolRegistry.register(tool)
        return tool
