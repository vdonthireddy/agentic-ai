"""HTTP Client to communicate with the LLM Gateway."""

import json
import httpx
from typing import Dict, Any, List, Optional

class LLMGatewayClient:
    """Client for dispatching chat completions and queries through the LiteLLM Gateway."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        agent_name: str = "AgenticAI",
        caller_id: str = "local_user",
        session_id: Optional[str] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.agent_name = agent_name
        self.caller_id = caller_id
        self.session_id = session_id or "sess_default"

    async def check_health(self) -> Dict[str, Any]:
        """Check gateway health status."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{self.base_url}/health")
            resp.raise_for_status()
            return resp.json()

    async def list_models(self) -> List[Dict[str, Any]]:
        """List models available on the gateway."""
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
        timeout_seconds: float = 120.0
    ) -> Dict[str, Any]:
        """
        Sends chat completion request to the LLM Gateway with full caller context and skills metadata.
        """
        tool_names = [t["function"]["name"] for t in (tools or []) if "function" in t and "name" in t["function"]]
        
        headers = {
            "Content-Type": "application/json",
            "X-Caller-Id": self.caller_id,
            "X-Agent-Name": self.agent_name,
            "X-Session-Id": self.session_id,
            "X-Caller-Context": json.dumps(caller_context or {}),
            "X-Skill-Names": ",".join(skill_names or []),
            "X-Tool-Names": ",".join(tool_names)
        }

        payload = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "temperature": temperature,
            "caller_id": self.caller_id,
            "agent_name": self.agent_name,
            "session_id": self.session_id,
            "caller_context": caller_context or {},
            "skill_names": skill_names or []
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
        params = {"limit": limit}
        if session_id:
            params["session_id"] = session_id
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{self.base_url}/v1/logs", params=params)
            resp.raise_for_status()
            return resp.json().get("logs", [])

    async def get_gateway_stats(self) -> Dict[str, Any]:
        """Retrieve aggregate usage statistics from gateway."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{self.base_url}/v1/stats")
            resp.raise_for_status()
            return resp.json()
