"""Tests for WebSocket agent session endpoint."""

import pytest
from fastapi.testclient import TestClient


class TestWebSocketEndpoint:
    def test_websocket_route_exists(self):
        """The /ws endpoint is registered."""
        try:
            from agent_tooling.tools import developer, data, cognitive, media
        except ImportError:
            pass

        from agent_tooling.server import app
        routes = [r.path for r in app.routes]
        assert "/ws" in routes

    def test_rest_endpoints_still_work(self):
        """Existing REST endpoints are unaffected."""
        try:
            from agent_tooling.tools import developer, data, cognitive, media
        except ImportError:
            pass

        from agent_tooling.server import app
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"
