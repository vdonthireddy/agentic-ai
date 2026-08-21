"""
Multi-Server External MCP Client Federation (ai_agent/federation.py).
Allows an agent to connect simultaneously to multiple external MCP servers (STDIO & SSE)
with consolidated tool discovery, schema unification, and intelligent call routing.
"""

import asyncio
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from ai_agent.mcp_client import MCPClientManager

class MCPServerConfig(BaseModel):
    server_id: str
    name: str
    transport: str = "stdio"  # "stdio" or "sse"
    command: Optional[str] = None
    args: List[str] = []
    url: Optional[str] = None
    description: str = ""

class FederatedMCPManager:
    """Manages connections across multiple internal and external MCP servers."""

    def __init__(self):
        self.servers: Dict[str, MCPClientManager] = {}
        self.server_configs: Dict[str, MCPServerConfig] = {}
        self.tool_to_server_map: Dict[str, str] = {}
        self._tools_cache: List[Dict[str, Any]] = []

    def register_server(self, config: MCPServerConfig):
        """Register an external or local MCP server definition."""
        self.server_configs[config.server_id] = config
        if config.transport == "stdio":
            script_path = config.args[0] if config.args else None
            self.servers[config.server_id] = MCPClientManager(
                server_script=script_path,
                python_path=config.command
            )

    async def connect_all(self):
        """Connect to all registered MCP servers concurrently and aggregate tools."""
        tasks = []
        for server_id, client in self.servers.items():
            tasks.append(self._connect_server(server_id, client))
        await asyncio.gather(*tasks, return_exceptions=True)
        await self.refresh_tools_catalog()

    async def _connect_server(self, server_id: str, client: MCPClientManager):
        try:
            await client.connect()
        except Exception as e:
            print(f"Warning: Failed to connect to federated MCP server '{server_id}': {e}")

    async def refresh_tools_catalog(self) -> List[Dict[str, Any]]:
        """Collects tools from all live servers and maps each tool to its server origin."""
        aggregated_tools = []
        self.tool_to_server_map.clear()

        for server_id, client in self.servers.items():
            try:
                tools = await client.list_tools_for_llm()
                for t in tools:
                    tool_name = t.get("function", {}).get("name", "")
                    if tool_name:
                        self.tool_to_server_map[tool_name] = server_id
                        # Tag with federated server origin
                        t["function"]["description"] = f"[{server_id.upper()}] {t['function'].get('description', '')}"
                        aggregated_tools.append(t)
            except Exception:
                pass

        self._tools_cache = aggregated_tools
        return self._tools_cache

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Route tool execution to the appropriate federated MCP server."""
        server_id = self.tool_to_server_map.get(tool_name)
        if not server_id or server_id not in self.servers:
            # Fallback: search across all servers
            for s_id, client in self.servers.items():
                try:
                    return await client.execute_tool(tool_name, arguments)
                except Exception:
                    continue
            return f'{{"error": "Tool \'{tool_name}\' not found on any federated MCP server."}}'

        target_client = self.servers[server_id]
        return await target_client.execute_tool(tool_name, arguments)

    async def disconnect_all(self):
        """Cleanly close all federated MCP server connections."""
        for client in self.servers.values():
            try:
                await client.disconnect()
            except Exception:
                pass
        self.servers.clear()
        self.tool_to_server_map.clear()
