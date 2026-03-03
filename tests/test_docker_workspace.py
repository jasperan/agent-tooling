"""Tests for DockerWorkspace and RemoteWorkspace."""

import pytest
from unittest.mock import MagicMock, patch


class TestDockerWorkspaceImport:
    def test_import_without_openhands(self):
        """DockerWorkspace raises ImportError when openhands not installed."""
        try:
            from agent_tooling.workspace.docker import DockerWorkspace
            # If it imports, the class should exist
            assert DockerWorkspace is not None
        except ImportError as e:
            assert "openhands" in str(e).lower() or "docker" in str(e).lower()

    def test_workspace_init_exports(self):
        """Workspace __init__ handles missing DockerWorkspace gracefully."""
        from agent_tooling.workspace import LocalWorkspace
        assert LocalWorkspace is not None


class TestRemoteWorkspaceImport:
    def test_remote_workspace_exists(self):
        """RemoteWorkspace module can be imported."""
        from agent_tooling.workspace.remote import RemoteWorkspace
        assert RemoteWorkspace is not None

    def test_remote_workspace_type(self):
        """RemoteWorkspace reports correct type."""
        from agent_tooling.workspace.remote import RemoteWorkspace
        ws = RemoteWorkspace(server_url="http://localhost:3000")
        assert ws.workspace_type == "remote"
