"""HTTP REST Agent Adapter for benchmarking external/remote agents."""

import time
import httpx
from typing import Dict, Any, Optional
from evals_framework.adapters.base import BaseAgentAdapter, AgentRunOutput


class HTTPAgentAdapter(BaseAgentAdapter):
    """Adapter to benchmark any external agent exposed via HTTP REST endpoint."""

    def __init__(
        self,
        adapter_id: str,
        name: str,
        endpoint_url: str,
        description: str = "External HTTP REST Agent endpoint",
        model: Optional[str] = None,
        auth_header: Optional[str] = None,
        timeout_seconds: float = 60.0,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            adapter_id=adapter_id,
            name=name,
            description=description,
            model=model,
            config=config or {}
        )
        self.endpoint_url = endpoint_url
        self.auth_header = auth_header
        self.timeout_seconds = timeout_seconds
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        if not self._client:
            headers = {"Content-Type": "application/json"}
            if self.auth_header:
                headers["Authorization"] = self.auth_header
            self._client = httpx.AsyncClient(headers=headers, timeout=self.timeout_seconds)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def run(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        caller_context: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> AgentRunOutput:
        await self.initialize()
        assert self._client is not None

        payload = {
            "prompt": prompt,
            "session_id": session_id or "eval_session",
            "model": self.model,
            "context": caller_context or {},
            **kwargs
        }

        start_time = time.time()
        resp = await self._client.post(self.endpoint_url, json=payload)
        latency_ms = (time.time() - start_time) * 1000
        resp.raise_for_status()
        data = resp.json()

        return AgentRunOutput(
            response=data.get("response", str(data)),
            tool_calls_executed=data.get("tool_calls_executed", data.get("tool_calls", [])),
            total_prompt_tokens=data.get("total_prompt_tokens", data.get("prompt_tokens", 0)),
            total_completion_tokens=data.get("total_completion_tokens", data.get("completion_tokens", 0)),
            latency_ms=latency_ms,
            session_id=session_id or "",
            active_skills=data.get("active_skills", []),
            metadata={"endpoint": self.endpoint_url, "status_code": resp.status_code}
        )
