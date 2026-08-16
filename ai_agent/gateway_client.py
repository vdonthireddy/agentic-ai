"""Client supporting both HTTP and Stdio transports for LLM Gateway."""

import sys
import os
import json
import asyncio
import httpx
from typing import Dict, Any, List, Optional


class LLMGatewayClient:
    """Client for dispatching chat completions and telemetry queries through the LLM Gateway via HTTP or Stdio."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        agent_name: str = "AgenticAI",
        caller_id: str = "local_user",
        session_id: Optional[str] = None,
        transport: Optional[str] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.agent_name = agent_name
        self.caller_id = caller_id
        self.session_id = session_id or "sess_default"
        
        # Resolve transport: parameter -> env var -> "http"
        self.transport = (transport or os.environ.get("GATEWAY_TRANSPORT", "http")).lower()
        
        # Stdio subprocess handles
        self._stdio_proc: Optional[asyncio.subprocess.Process] = None
        self._lock = asyncio.Lock()

    async def _ensure_stdio_process(self):
        """Spawns the stdio gateway subprocess if not already running."""
        if self._stdio_proc is None or self._stdio_proc.returncode is not None:
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            env = dict(os.environ)
            env["PYTHONPATH"] = root_dir
            
            self._stdio_proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "llm_gateway",
                "--transport",
                "stdio",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                env=env
            )

    async def _send_stdio_command(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Sends a JSON line to the stdio gateway process and reads the JSON response line."""
        async with self._lock:
            await self._ensure_stdio_process()
            if not self._stdio_proc or not self._stdio_proc.stdin or not self._stdio_proc.stdout:
                raise RuntimeError("Failed to establish stdio pipes to LLM Gateway process.")

            req_line = (json.dumps(payload) + "\n").encode("utf-8")
            self._stdio_proc.stdin.write(req_line)
            await self._stdio_proc.stdin.drain()

            resp_line = await self._stdio_proc.stdout.readline()
            if not resp_line:
                raise RuntimeError("LLM Gateway Stdio subprocess returned empty response (EOF).")

            res = json.loads(resp_line.decode("utf-8").strip())
            if "error" in res and res.get("status") == "ERROR":
                raise RuntimeError(f"Stdio Gateway Error: {res.get('message', res['error'])}")
            return res

    async def check_health(self) -> Dict[str, Any]:
        """Check gateway health status."""
        if self.transport == "stdio":
            return await self._send_stdio_command({"action": "health"})
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{self.base_url}/health")
            resp.raise_for_status()
            return resp.json()

    async def list_models(self) -> List[Dict[str, Any]]:
        """List models available on the gateway."""
        if self.transport == "stdio":
            res = await self._send_stdio_command({"action": "models"})
            return res.get("data", [])

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{self.base_url}/v1/models")
            resp.raise_for_status()
            return resp.json().get("data", [])

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        skill_names: Optional[List[str]] = None,
        caller_context: Optional[Dict[str, Any]] = None,
        temperature: float = 0.2,
        timeout_seconds: float = 120.0,
        conversation_id: Optional[str] = None,
        turn_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends chat completion request to the LLM Gateway with full caller context, hierarchical IDs, and skills metadata.
        """
        tool_names = [t["function"]["name"] for t in (tools or []) if "function" in t and "name" in t["function"]]
        conv_id = conversation_id or self.session_id
        
        context = dict(caller_context or {})
        if conv_id: context["conversation_id"] = conv_id
        if turn_id: context["turn_id"] = turn_id
        if request_id: context["request_id"] = request_id
        
        payload = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "temperature": temperature,
            "caller_id": self.caller_id,
            "agent_name": self.agent_name,
            "session_id": conv_id,
            "conversation_id": conv_id,
            "turn_id": turn_id,
            "request_id": request_id,
            "caller_context": context,
            "skill_names": skill_names or [],
            "action": "chat_completions"
        }

        if self.transport == "stdio":
            return await self._send_stdio_command(payload)

        headers = {
            "Content-Type": "application/json",
            "X-Caller-Id": self.caller_id,
            "X-Agent-Name": self.agent_name,
            "X-Session-Id": conv_id,
            "X-Conversation-Id": conv_id,
            "X-Turn-Id": turn_id or "",
            "X-Request-Id": request_id or "",
            "X-Caller-Context": json.dumps(context),
            "X-Skill-Names": ",".join(skill_names or []),
            "X-Tool-Names": ",".join(tool_names)
        }

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers=headers
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Gateway Error ({resp.status_code}): {resp.text}")
            return resp.json()

    async def get_audit_logs(self, limit: int = 10, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve recent audit logs from gateway."""
        if self.transport == "stdio":
            res = await self._send_stdio_command({
                "action": "logs",
                "limit": limit,
                "session_id": session_id
            })
            return res.get("logs", [])

        params = {"limit": limit}
        if session_id:
            params["session_id"] = session_id
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{self.base_url}/v1/logs", params=params)
            resp.raise_for_status()
            return resp.json().get("logs", [])

    async def get_gateway_stats(self) -> Dict[str, Any]:
        """Retrieve aggregate usage statistics from gateway."""
        if self.transport == "stdio":
            return await self._send_stdio_command({"action": "stats"})

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{self.base_url}/v1/stats")
            resp.raise_for_status()
            return resp.json()

    async def close(self):
        """Terminate any active stdio subprocess."""
        if self._stdio_proc:
            try:
                if self._stdio_proc.stdin:
                    self._stdio_proc.stdin.close()
                self._stdio_proc.terminate()
                await self._stdio_proc.wait()
            except Exception:
                pass
            self._stdio_proc = None
