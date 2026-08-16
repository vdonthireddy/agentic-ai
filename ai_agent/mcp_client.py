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
            # Default to mcp_server/server.py
            base_dir = Path(__file__).parent.parent
            server_script = str(base_dir / "mcp_server" / "server.py")
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
        
        # Sanitize and adapt arguments for model calling variations
        sanitized_args: Dict[str, Any] = dict(arguments) if isinstance(arguments, dict) else {}
        target_tool = tool_name
        
        if tool_name in ("calculate_tip_and_split", "tip_calculator", "split_bill", "bill_split", "tip_calc"):
            target_tool = "calculate_tip_and_split"
        elif tool_name in ("calculator", "calculate", "math_calculator", "calc"):
            target_tool = "calculator"
            if "expression" not in sanitized_args or not sanitized_args["expression"]:
                if "formula" in sanitized_args:
                    sanitized_args["expression"] = str(sanitized_args["formula"])
                elif "math_expr" in sanitized_args:
                    sanitized_args["expression"] = str(sanitized_args["math_expr"])
                elif "query" in sanitized_args:
                    sanitized_args["expression"] = str(sanitized_args["query"])
                elif "input" in sanitized_args:
                    sanitized_args["expression"] = str(sanitized_args["input"])
                elif sanitized_args:
                    # Pick or combine expressions from dictionary keys (e.g. tip, total)
                    vals = [str(v) for v in sanitized_args.values() if isinstance(v, (str, int, float))]
                    if len(vals) == 1:
                        sanitized_args["expression"] = vals[0]
                    elif "total" in sanitized_args and "tip" in sanitized_args:
                        sanitized_args["expression"] = f"({sanitized_args['total']}) + ({sanitized_args['tip']})"
                    elif vals:
                        sanitized_args["expression"] = vals[-1]

        elif tool_name in ("workspace_file_ops", "file_ops", "file_operation"):
            target_tool = "workspace_file_ops"
            if "action" not in sanitized_args or not sanitized_args["action"]:
                if "operation" in sanitized_args:
                    sanitized_args["action"] = str(sanitized_args["operation"])
                elif "op" in sanitized_args:
                    sanitized_args["action"] = str(sanitized_args["op"])
                elif "mode" in sanitized_args:
                    sanitized_args["action"] = str(sanitized_args["mode"])
                elif "content" in sanitized_args or "text" in sanitized_args:
                    sanitized_args["action"] = "write"
                else:
                    sanitized_args["action"] = "read"

        try:
            result = await self._session.call_tool(target_tool, arguments=sanitized_args)
            text_outputs = []
            for c in result.content:
                if hasattr(c, "text"):
                    text_outputs.append(c.text)
                elif isinstance(c, str):
                    text_outputs.append(c)
                else:
                    text_outputs.append(str(c))
            return "\n".join(text_outputs)
        except Exception as e:
            # Check if this tool name matches any registered skill
            matching_skill = next((s for s in self.skills if s["name"] == target_tool or s["name"] == tool_name), None)
            if matching_skill or tool_name.endswith("_skill"):
                skill_id = matching_skill["name"] if matching_skill else tool_name
                try:
                    prompt_res = await self.get_prompt(skill_id, sanitized_args)
                    return json.dumps({
                        "success": True,
                        "skill": skill_id,
                        "instructions": prompt_res.get("content", "")
                    }, indent=2)
                except Exception:
                    pass
            return f"Unknown tool: {tool_name}"
