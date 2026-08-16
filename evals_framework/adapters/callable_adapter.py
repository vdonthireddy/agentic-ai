"""Callable Agent Adapter allowing developers to wrap any Python async function."""

import time
import inspect
from typing import Callable, Any, Dict, Optional, Awaitable
from evals_framework.adapters.base import BaseAgentAdapter, AgentRunOutput


class CallableAgentAdapter(BaseAgentAdapter):
    """Adapter wrapping an arbitrary Python async function or lambda."""

    def __init__(
        self,
        adapter_id: str,
        name: str,
        agent_fn: Callable[..., Any],
        description: str = "Custom Python Callable Agent",
        model: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            adapter_id=adapter_id,
            name=name,
            description=description,
            model=model,
            config=config or {}
        )
        self.agent_fn = agent_fn

    async def run(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        caller_context: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> AgentRunOutput:
        start_time = time.time()
        
        # Invoke sync or async function
        if inspect.iscoroutinefunction(self.agent_fn):
            raw_res = await self.agent_fn(prompt, session_id=session_id, model=self.model, **kwargs)
        else:
            raw_res = self.agent_fn(prompt, session_id=session_id, model=self.model, **kwargs)
            
        latency_ms = (time.time() - start_time) * 1000

        if isinstance(raw_res, AgentRunOutput):
            return raw_res

        if isinstance(raw_res, dict):
            return AgentRunOutput(
                response=raw_res.get("response", str(raw_res)),
                tool_calls_executed=raw_res.get("tool_calls_executed", raw_res.get("tool_calls", [])),
                total_prompt_tokens=raw_res.get("total_prompt_tokens", 0),
                total_completion_tokens=raw_res.get("total_completion_tokens", 0),
                latency_ms=latency_ms,
                session_id=session_id or "",
                active_skills=raw_res.get("active_skills", []),
                metadata={"callable": str(self.agent_fn)}
            )

        return AgentRunOutput(
            response=str(raw_res),
            tool_calls_executed=[],
            total_prompt_tokens=0,
            total_completion_tokens=0,
            latency_ms=latency_ms,
            session_id=session_id or "",
            metadata={"callable": str(self.agent_fn)}
        )
