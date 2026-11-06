"""Access-control regression tests for the HTTP server and DockerWorkspace."""

import asyncio
import time

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from agent_tooling import server
from agent_tooling.tools.base import ToolResult

TOKEN = "t0ken-for-tests"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
BODY = {"name": "calculate", "parameters": {"expression": "2 + 2"}}


@pytest.fixture
def client(monkeypatch):
    from agent_tooling.tools import cognitive  # noqa: F401  registers calculate

    monkeypatch.setenv(server.TOKEN_ENV, TOKEN)
    monkeypatch.delenv(server.CORS_ORIGINS_ENV, raising=False)
    return TestClient(server.app)


@pytest.mark.parametrize("path", ["/execute", "/tools/calculate/execute"])
def test_execute_requires_token(client, path):
    assert client.post(path, json=BODY).status_code == 401
    assert client.post(path, json=BODY, headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.post(path, json=BODY, headers=AUTH).status_code == 200


def test_function_call_requires_token(client):
    body = {"name": "calculate", "arguments": '{"expression": "1+1"}'}
    assert client.post("/function_call", json=body).status_code == 401
    assert client.post("/function_call", json=body, headers=AUTH).status_code == 200


def test_execute_fails_closed_without_configured_token(client, monkeypatch):
    monkeypatch.delenv(server.TOKEN_ENV)
    assert client.post("/execute", json=BODY, headers=AUTH).status_code == 503


def test_cors_rejects_foreign_origin_and_credentials(client):
    r = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in r.headers
    r = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-credentials" not in r.headers


def test_websocket_requires_token_and_loopback_origin(client):
    frame = {"type": "message", "tool_name": "calculate", "parameters": {"expression": "2 + 2"}}
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws") as ws:
            ws.send_json(frame)
            ws.receive_json()
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws?token={TOKEN}", headers={"Origin": "https://evil.example"}) as ws:
            ws.send_json(frame)
            ws.receive_json()
    with client.websocket_connect(f"/ws?token={TOKEN}") as ws:
        ws.send_json(frame)
        assert ws.receive_json()["result"]["success"] is True


def test_execute_does_not_block_event_loop(client, monkeypatch):
    def slow(name, params):
        time.sleep(0.5)
        return ToolResult(success=True, tool_name=name)

    monkeypatch.setattr(server.interceptor, "execute", slow)

    async def run():
        import httpx

        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
            slow_call = asyncio.create_task(c.post("/execute", json=BODY, headers=AUTH))
            await asyncio.sleep(0.1)
            t0 = time.monotonic()
            await c.get("/health")
            elapsed = time.monotonic() - t0
            await slow_call
            return elapsed

    assert asyncio.run(run()) < 0.3


def test_docker_workspace_refuses_sandbox_required_tool(monkeypatch):
    from agent_tooling.workspace import docker

    monkeypatch.setattr(docker, "HAS_OPENHANDS_WORKSPACE", True)
    ws = docker.DockerWorkspace()
    ran = []

    class Tool:
        name = "untrusted"
        sandbox_required = True

        def run(self, **kw):
            ran.append(kw)

    result = ws.execute_tool(Tool(), payload="x")
    assert result.success is False and "requires a sandbox" in result.error
    assert ran == []
    assert ws._oh_workspace is None
