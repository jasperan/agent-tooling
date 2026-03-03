"""
Workspace abstraction for tool execution environments.

Workspaces determine WHERE tools execute:
- LocalWorkspace: In-process (default, no container needed)
- DockerWorkspace: Inside a Docker container (requires openhands-workspace)
- RemoteWorkspace: On a remote agent-server (requires openhands-workspace)
"""

from agent_tooling.workspace.base import Workspace, CommandResult
from agent_tooling.workspace.local import LocalWorkspace

__all__ = ["Workspace", "CommandResult", "LocalWorkspace"]

# Conditionally import Docker/Remote workspaces
try:
    from agent_tooling.workspace.docker import DockerWorkspace
    __all__.append("DockerWorkspace")
except ImportError:
    pass

try:
    from agent_tooling.workspace.remote import RemoteWorkspace
    __all__.append("RemoteWorkspace")
except ImportError:
    pass
