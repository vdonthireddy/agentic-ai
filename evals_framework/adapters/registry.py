"""Agent Adapter Registry for registering and selecting agents dynamically."""

from typing import Dict, List, Optional, Type, Any
from evals_framework.adapters.base import BaseAgentAdapter
from evals_framework.adapters.mcp_adapter import MCPAgentAdapter


class AgentRegistry:
    """Singleton registry to manage, register, and retrieve Agent Adapters."""

    def __init__(self) -> None:
        self._adapters: Dict[str, BaseAgentAdapter] = {}
        self._register_builtins()

    def _register_builtins(self) -> None:
        # Register default MCP Agent
        default_mcp = MCPAgentAdapter(
            adapter_id="mcp_default",
            name="Default MCP Tool & Skill Agent",
            description="Autonomous agent connecting to FastMCP server with tools (math, weather, search, products, files) and skills."
        )
        self.register(default_mcp)

    def register(self, adapter: BaseAgentAdapter) -> None:
        """Register an agent adapter."""
        self._adapters[adapter.adapter_id] = adapter

    def unregister(self, adapter_id: str) -> Optional[BaseAgentAdapter]:
        """Unregister an agent adapter."""
        return self._adapters.pop(adapter_id, None)

    def get(self, adapter_id: str) -> Optional[BaseAgentAdapter]:
        """Retrieve an agent adapter by ID."""
        return self._adapters.get(adapter_id)

    def list_all(self) -> List[Dict[str, Any]]:
        """List all registered agent adapters as dictionary summaries."""
        return [adapter.to_dict() for adapter in self._adapters.values()]


# Global registry instance
agent_registry = AgentRegistry()
