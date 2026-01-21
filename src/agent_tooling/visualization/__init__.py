"""
Visualization module for agent-tooling.

Provides:
- Arena mode: Compare tools side-by-side
- Dashboard: Live tool call activity monitor
- Traces: Step-by-step execution visualization
"""

from agent_tooling.visualization.arena import ToolArena
from agent_tooling.visualization.dashboard import ToolDashboard
from agent_tooling.visualization.traces import ToolTracer

__all__ = [
    "ToolArena",
    "ToolDashboard",
    "ToolTracer",
]
