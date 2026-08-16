"""Agent Adapters Package."""

from evals_framework.adapters.base import BaseAgentAdapter, AgentRunOutput
from evals_framework.adapters.mcp_adapter import MCPAgentAdapter
from evals_framework.adapters.http_adapter import HTTPAgentAdapter
from evals_framework.adapters.callable_adapter import CallableAgentAdapter
from evals_framework.adapters.registry import AgentRegistry, agent_registry

__all__ = [
    "BaseAgentAdapter",
    "AgentRunOutput",
    "MCPAgentAdapter",
    "HTTPAgentAdapter",
    "CallableAgentAdapter",
    "AgentRegistry",
    "agent_registry"
]
