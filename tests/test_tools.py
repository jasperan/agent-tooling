"""Basic tests for agent-tooling."""

import pytest
from agent_tooling import tool, ToolRegistry, BaseTool, ToolResult
from agent_tooling.tools.cognitive.calculator import calculate


class TestToolDecorator:
    """Tests for the @tool decorator."""

    def test_basic_tool_creation(self):
        """Test creating a tool with the decorator."""
        @tool(name="test_tool", category="test")
        def my_test_tool(value: str) -> str:
            """A test tool.

            Args:
                value: The input value

            Returns:
                The processed value
            """
            return f"processed: {value}"

        # Check tool is registered
        assert ToolRegistry.get("test_tool") is not None

        # Check tool attributes
        assert my_test_tool.name == "test_tool"
        assert my_test_tool.category == "test"

        # Check execution
        result = my_test_tool(value="hello")
        assert result.success
        assert result.data == "processed: hello"

    def test_tool_with_optional_params(self):
        """Test tool with optional parameters."""
        @tool(name="optional_test")
        def optional_tool(required: str, optional: int = 10) -> dict:
            """Tool with optional param.

            Args:
                required: Required parameter
                optional: Optional parameter
            """
            return {"required": required, "optional": optional}

        # With both params
        result = optional_tool(required="test", optional=20)
        assert result.success
        assert result.data["optional"] == 20

        # With only required
        result = optional_tool(required="test")
        assert result.success
        assert result.data["optional"] == 10


class TestCalculatorTool:
    """Tests for the calculator tool."""

    def test_basic_arithmetic(self):
        """Test basic arithmetic operations."""
        result = calculate(expression="2 + 2")
        assert result.success
        assert result.data["result"] == 4

    def test_complex_expression(self):
        """Test complex mathematical expression."""
        result = calculate(expression="sqrt(16) + pow(2, 3)")
        assert result.success
        assert result.data["result"] == 12.0

    def test_division_by_zero(self):
        """Test division by zero handling."""
        result = calculate(expression="1 / 0")
        assert not result.success
        assert "zero" in result.error.lower()

    def test_invalid_expression(self):
        """Test invalid expression handling."""
        result = calculate(expression="import os")
        assert not result.success


class TestToolRegistry:
    """Tests for the tool registry."""

    def test_list_tools(self):
        """Test listing registered tools."""
        tools = ToolRegistry.list_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_get_by_category(self):
        """Test getting tools by category."""
        cognitive_tools = ToolRegistry.get_by_category("cognitive")
        assert len(cognitive_tools) > 0
        assert all(t.category == "cognitive" for t in cognitive_tools)

    def test_schema_generation(self):
        """Test OpenAI schema generation."""
        schemas = ToolRegistry.to_openai_functions()
        assert isinstance(schemas, list)
        assert len(schemas) > 0

        for schema in schemas:
            assert "name" in schema
            assert "description" in schema
            assert "parameters" in schema


class TestToolResult:
    """Tests for ToolResult."""

    def test_success_result(self):
        """Test successful result."""
        result = ToolResult(
            success=True,
            data={"key": "value"},
            tool_name="test",
        )
        assert result.success
        assert result.to_llm_response() == '{\n  "key": "value"\n}'

    def test_error_result(self):
        """Test error result."""
        result = ToolResult(
            success=False,
            error="Something went wrong",
            tool_name="test",
        )
        assert not result.success
        assert "Error:" in result.to_llm_response()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
