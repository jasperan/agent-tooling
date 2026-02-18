"""
Calculator Tool - Perform mathematical calculations.

Supports basic arithmetic, scientific functions, and unit conversions.
"""

import math
import re
from typing import Union

from agent_tooling.tools.decorator import tool
from agent_tooling.tools.base import ToolError


SAMPLES = {
    "calculate": [
        {
            "name": "basic_arithmetic",
            "description": "Simple addition",
            "input": {"expression": "2 + 2"},
        },
        {
            "name": "scientific",
            "description": "Square root and power",
            "input": {"expression": "sqrt(144) + pow(2, 3)"},
        },
        {
            "name": "trigonometry",
            "description": "Sine of pi/2",
            "input": {"expression": "sin(pi / 2)"},
        },
    ],
}


# Safe math functions to expose
SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "pow": pow,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "exp": math.exp,
    "floor": math.floor,
    "ceil": math.ceil,
    "pi": math.pi,
    "e": math.e,
    "radians": math.radians,
    "degrees": math.degrees,
}


@tool(name="calculate", category="cognitive", mcp_enabled=True)
def calculate(expression: str) -> dict:
    """Evaluate a mathematical expression.

    Supports basic arithmetic (+, -, *, /, **, %), parentheses,
    and mathematical functions (sqrt, sin, cos, tan, log, etc.).

    Args:
        expression: Mathematical expression to evaluate (e.g., "2 + 2", "sqrt(16)", "sin(pi/2)")

    Returns:
        Dictionary with the expression and result
    """
    try:
        # Clean the expression
        expression = expression.strip()

        # Validate - only allow safe characters
        if not re.match(r'^[\d\s\+\-\*\/\%\(\)\.\,\w]+$', expression):
            raise ToolError(
                f"Invalid characters in expression: {expression}",
                tool_name="calculate"
            )

        # Check for dangerous patterns
        dangerous = ["import", "exec", "eval", "open", "__", "lambda"]
        expr_lower = expression.lower()
        for pattern in dangerous:
            if pattern in expr_lower:
                raise ToolError(
                    f"Forbidden pattern in expression: {pattern}",
                    tool_name="calculate"
                )

        # Evaluate in restricted namespace
        result = eval(expression, {"__builtins__": {}}, SAFE_FUNCTIONS)

        return {
            "expression": expression,
            "result": result,
            "type": type(result).__name__,
        }

    except ZeroDivisionError:
        raise ToolError("Division by zero", tool_name="calculate")
    except ValueError as e:
        raise ToolError(f"Math error: {e}", tool_name="calculate")
    except SyntaxError:
        raise ToolError(f"Invalid expression syntax: {expression}", tool_name="calculate")
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Calculation error: {e}", tool_name="calculate")
