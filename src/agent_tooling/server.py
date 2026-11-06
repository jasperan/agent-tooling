"""
Agent Tooling Server - FastAPI-based HTTP server for tool execution.

Provides:
- REST API for tool execution
- OpenAI-compatible function calling endpoint
- Tool discovery and schema endpoints
- WebSocket support for real-time agent sessions
"""

import asyncio
import hmac
import os
import re
import secrets
from typing import Any, Dict, List, Optional
from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import json
import uvicorn

from agent_tooling import __version__
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

    @classmethod
    def from_result(cls, result) -> "ToolCallResponse":
        """Create a response from a ToolResult."""
        return cls(
            success=result.success,
            data=result.data,
            error=result.error,
            tool_name=result.tool_name,
            execution_time_ms=result.execution_time_ms,
        )


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
    version=__version__,
)

# --- Access control -------------------------------------------------------
# Tool execution runs host commands as the server user, so every execution
# route (and the WebSocket session) requires a bearer token, and browsers may
# only call the API from loopback origins unless the operator lists more.
TOKEN_ENV = "AGENT_TOOLING_API_TOKEN"
CORS_ORIGINS_ENV = "AGENT_TOOLING_CORS_ORIGINS"
_LOOPBACK_ORIGIN = re.compile(r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$")


def _extra_origins() -> List[str]:
    raw = os.environ.get(CORS_ORIGINS_ENV, "")
    return [o.strip() for o in raw.split(",") if o.strip() and o.strip() != "*"]


def _origin_allowed(origin: Optional[str]) -> bool:
    """Non-browser clients send no Origin; browsers must be loopback or listed."""
    if origin is None:
        return True
    return bool(_LOOPBACK_ORIGIN.match(origin)) or origin in _extra_origins()


def _token_valid(presented: Optional[str]) -> bool:
    expected = os.environ.get(TOKEN_ENV, "")
    if not expected or not presented:
        return False
    return hmac.compare_digest(presented.encode(), expected.encode())


def _bearer(header: Optional[str]) -> Optional[str]:
    if header and header[:7].lower() == "bearer ":
        return header[7:].strip()
    return None


async def require_auth(request: Request) -> None:
    """Reject execution requests that lack the configured bearer token."""
    if not os.environ.get(TOKEN_ENV):
        raise HTTPException(status_code=503, detail=f"{TOKEN_ENV} is not configured")
    if not _token_valid(_bearer(request.headers.get("authorization"))):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=_extra_origins(),
    allow_origin_regex=_LOOPBACK_ORIGIN.pattern,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Global interceptor
interceptor = ToolingInterceptor()


@app.get("/")
async def root():
    """Server info."""
    return {
        "name": "Agent Tooling Server",
        "version": __version__,
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


@app.post("/tools/{tool_name}/execute", response_model=ToolCallResponse, dependencies=[Depends(require_auth)])
async def execute_tool(tool_name: str, request: ToolCallRequest):
    """Execute a specific tool."""
    # Tool bodies block (subprocess, network); keep them off the event loop.
    result = await asyncio.to_thread(interceptor.execute, tool_name, request.parameters)
    return ToolCallResponse.from_result(result)


@app.post("/execute", response_model=ToolCallResponse, dependencies=[Depends(require_auth)])
async def execute(request: ToolCallRequest):
    """Execute a tool by name."""
    result = await asyncio.to_thread(interceptor.execute, request.name, request.parameters)
    return ToolCallResponse.from_result(result)


@app.post("/function_call", response_model=ToolCallResponse, dependencies=[Depends(require_auth)])
async def function_call(request: FunctionCallRequest):
    """OpenAI-compatible function calling endpoint."""
    try:
        arguments = json.loads(request.arguments)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in arguments")

    result = await asyncio.to_thread(
        interceptor.execute_function_call,
        {"name": request.name, "arguments": arguments},
    )
    return ToolCallResponse.from_result(result)


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


@app.websocket("/ws")
async def websocket_agent_session(websocket: WebSocket):
    """
    WebSocket endpoint for real-time agent sessions.

    Protocol:
        Client sends: {"type": "message", "content": "user message"}
        Server sends: {"type": "text", "content": "assistant response"}
        Server sends: {"type": "tool_call", "name": "...", "input": {...}}
        Server sends: {"type": "tool_result", "name": "...", "result": {...}}
        Server sends: {"type": "done", "content": "final response"}
        Client sends: {"type": "close"} to end session
    """
    # Browsers do not apply CORS to WebSockets, so check Origin and the token
    # before accepting the upgrade.
    presented = _bearer(websocket.headers.get("authorization")) or websocket.query_params.get("token")
    if not _origin_allowed(websocket.headers.get("origin")) or not _token_valid(presented):
        await websocket.close(code=1008)
        return

    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "close":
                await websocket.close()
                break

            if data.get("type") == "message":
                content = data.get("content", "")

                if "tool_name" in data:
                    result = await asyncio.to_thread(
                        interceptor.execute,
                        data["tool_name"],
                        data.get("parameters", {}),
                    )
                    await websocket.send_json({
                        "type": "tool_result",
                        "name": data["tool_name"],
                        "result": {
                            "success": result.success,
                            "data": result.data,
                            "error": result.error,
                            "execution_time_ms": result.execution_time_ms,
                        },
                    })
                else:
                    await websocket.send_json({
                        "type": "text",
                        "content": f"Received: {content}",
                    })

                await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        pass


def main(host: str = "127.0.0.1", port: int = 8082):
    """Run the server."""
    # Load built-in tools
    try:
        from agent_tooling.tools import developer, data, cognitive, media
    except ImportError:
        pass

    if not os.environ.get(TOKEN_ENV):
        os.environ[TOKEN_ENV] = secrets.token_urlsafe(32)
        print(f"{TOKEN_ENV} not set; generated a one-time bearer token: {os.environ[TOKEN_ENV]}")

    print(f"Starting Agent Tooling Server on {host}:{port}")
    print(f"Tools loaded: {ToolRegistry.count()}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Agent Tooling Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8082, help="Port to bind to")

    args = parser.parse_args()
    main(args.host, args.port)
