"""
Agent Tooling Server - FastAPI-based HTTP server for tool execution.

Provides:
- REST API for tool execution
- OpenAI-compatible function calling endpoint
- Tool discovery and schema endpoints
- WebSocket support for streaming (future)
"""

from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import json
import uvicorn

from agent_tooling.tools.registry import ToolRegistry
from agent_tooling.interceptor import ToolingInterceptor


# Request/Response models
class ToolCallRequest(BaseModel):
    """Request to execute a tool."""
    name: str = Field(description="Tool name")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")


class ToolCallResponse(BaseModel):
    """Response from tool execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    tool_name: str
    execution_time_ms: float


class FunctionCallRequest(BaseModel):
    """OpenAI-style function call request."""
    name: str
    arguments: str  # JSON string


class ToolListResponse(BaseModel):
    """Response listing available tools."""
    tools: List[Dict[str, Any]]
    count: int


# Create FastAPI app
app = FastAPI(
    title="Agent Tooling Server",
    description="HTTP API for executing agent tools",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global interceptor
interceptor = ToolingInterceptor()


@app.get("/")
async def root():
    """Server info."""
    return {
        "name": "Agent Tooling Server",
        "version": "0.1.0",
        "tools_count": ToolRegistry.count(),
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/tools", response_model=ToolListResponse)
async def list_tools():
    """List all available tools."""
    tools = ToolRegistry.list_tools()
    return ToolListResponse(tools=tools, count=len(tools))


@app.get("/tools/{tool_name}")
async def get_tool(tool_name: str):
    """Get information about a specific tool."""
    tool = ToolRegistry.get(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")

    return {
        "name": tool.name,
        "description": tool.description,
        "category": tool.category,
        "mcp_enabled": tool.mcp_enabled,
        "parameters": [p.model_dump() for p in tool.get_parameters()],
        "json_schema": tool.to_json_schema(),
    }


@app.get("/tools/{tool_name}/schema")
async def get_tool_schema(tool_name: str, format: str = "openai"):
    """Get the schema for a tool in various formats."""
    tool = ToolRegistry.get(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")

    if format == "openai":
        return tool.to_openai_function()
    elif format == "mcp":
        return tool.to_mcp_tool()
    elif format == "json":
        return tool.to_json_schema()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown format: {format}")


@app.post("/tools/{tool_name}/execute", response_model=ToolCallResponse)
async def execute_tool(tool_name: str, request: ToolCallRequest):
    """Execute a specific tool."""
    result = interceptor.execute(tool_name, request.parameters)

    return ToolCallResponse(
        success=result.success,
        data=result.data,
        error=result.error,
        tool_name=result.tool_name,
        execution_time_ms=result.execution_time_ms,
    )


@app.post("/execute", response_model=ToolCallResponse)
async def execute(request: ToolCallRequest):
    """Execute a tool by name."""
    result = interceptor.execute(request.name, request.parameters)

    return ToolCallResponse(
        success=result.success,
        data=result.data,
        error=result.error,
        tool_name=result.tool_name,
        execution_time_ms=result.execution_time_ms,
    )


@app.post("/function_call", response_model=ToolCallResponse)
async def function_call(request: FunctionCallRequest):
    """OpenAI-compatible function calling endpoint."""
    try:
        arguments = json.loads(request.arguments)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in arguments")

    result = interceptor.execute_function_call({
        "name": request.name,
        "arguments": arguments,
    })

    return ToolCallResponse(
        success=result.success,
        data=result.data,
        error=result.error,
        tool_name=result.tool_name,
        execution_time_ms=result.execution_time_ms,
    )


@app.get("/schemas/openai")
async def get_openai_schemas(tools: Optional[str] = None):
    """Get OpenAI function schemas for all or specified tools."""
    tool_list = tools.split(",") if tools else None
    return {"functions": ToolRegistry.to_openai_functions(tool_list)}


@app.get("/schemas/mcp")
async def get_mcp_schemas(tools: Optional[str] = None):
    """Get MCP tool schemas for all or specified tools."""
    tool_list = tools.split(",") if tools else None
    return {"tools": ToolRegistry.to_mcp_tools(tool_list)}


@app.get("/categories")
async def get_categories():
    """Get all tool categories."""
    return {"categories": ToolRegistry.get_categories()}


@app.get("/categories/{category}")
async def get_tools_by_category(category: str):
    """Get all tools in a category."""
    tools = ToolRegistry.get_by_category(category)
    return {
        "category": category,
        "tools": [
            {
                "name": t.name,
                "description": t.description,
            }
            for t in tools
        ],
        "count": len(tools),
    }


def main(host: str = "0.0.0.0", port: int = 8082):
    """Run the server."""
    # Load built-in tools
    try:
        from agent_tooling.tools import developer, data, cognitive
    except ImportError:
        pass

    print(f"Starting Agent Tooling Server on {host}:{port}")
    print(f"Tools loaded: {ToolRegistry.count()}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Agent Tooling Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8082, help="Port to bind to")

    args = parser.parse_args()
    main(args.host, args.port)
