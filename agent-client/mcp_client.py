"""MCP Client integration for connecting to the MCP Server, discovering tools & skills, and executing tools."""

import sys
import json
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClientManager:
    """Manages connection to the MCP Server over STDIO or SSE."""

    def __init__(self, server_script: Optional[str] = None, python_path: Optional[str] = None):
        if not server_script:
            # Default to mcp-server/server.py
            base_dir = Path(__file__).parent.parent
            server_script = str(base_dir / "mcp-server" / "server.py")
        self.server_script = server_script
        self.python_path = python_path or sys.executable
        self._session: Optional[ClientSession] = None
        self._exit_stack = None

    async def connect(self):
        """Establish stdio connection and initialize MCP session."""
        server_params = StdioServerParameters(
            command=self.python_path,
            args=[self.server_script, "--transport", "stdio"],
            env=None
        )
        self._client_ctx = stdio_client(server_params)
        read, write = await self._client_ctx.__aenter__()
        self._session = ClientSession(read, write)
        await self._session.__aenter__()
        await self._session.initialize()
        return self._session

    async def disconnect(self):
        """Gracefully close MCP session and process streams."""
        if self._session:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception:
                pass
            self._session = None
        if hasattr(self, "_client_ctx") and self._client_ctx:
            try:
                await self._client_ctx.__aexit__(None, None, None)
            except Exception:
                pass

    async def list_tools_for_llm(self) -> List[Dict[str, Any]]:
        """
        Fetches tools from MCP server and converts them to OpenAI/LiteLLM tool definitions.
        """
        if not self._session:
            raise RuntimeError("MCP Client is not connected. Call connect() first.")
        
        tool_list = await self._session.list_tools()
        openai_tools = []
        for t in tool_list.tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": t.inputSchema if hasattr(t, "inputSchema") and t.inputSchema else {"type": "object", "properties": {}}
                }
            })
        return openai_tools

    async def list_skills(self) -> List[Dict[str, Any]]:
        """
        Fetches available prompts (skills) from the MCP server.
        """
        if not self._session:
            raise RuntimeError("MCP Client is not connected. Call connect() first.")
        
        prompt_list = await self._session.list_prompts()
        skills = []
        for p in prompt_list.prompts:
            args = []
            if hasattr(p, "arguments") and p.arguments:
                for a in p.arguments:
                    args.append({
                        "name": a.name,
                        "description": getattr(a, "description", ""),
                        "required": getattr(a, "required", False)
                    })
            skills.append({
                "name": p.name,
                "description": p.description or "",
                "arguments": args
            })
        return skills

    async def get_skill_prompt(self, skill_name: str, arguments: Optional[Dict[str, str]] = None) -> str:
        """
        Retrieves rendered skill instructions from MCP server for a given skill.
        """
        if not self._session:
            raise RuntimeError("MCP Client is not connected. Call connect() first.")
        
        res = await self._session.get_prompt(skill_name, arguments=arguments or {})
        text_parts = []
        for msg in res.messages:
            content = getattr(msg, "content", None)
            if content:
                if hasattr(content, "text"):
                    text_parts.append(content.text)
                elif isinstance(content, str):
                    text_parts.append(content)
        return "\n\n".join(text_parts)

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Executes a tool on the MCP server and returns the text result.
        """
        if not self._session:
            raise RuntimeError("MCP Client is not connected. Call connect() first.")
        
        result = await self._session.call_tool(tool_name, arguments=arguments)
        text_outputs = []
        for c in result.content:
            if hasattr(c, "text"):
                text_outputs.append(c.text)
            elif isinstance(c, str):
                text_outputs.append(c)
            else:
                text_outputs.append(str(c))
        return "\n".join(text_outputs)
