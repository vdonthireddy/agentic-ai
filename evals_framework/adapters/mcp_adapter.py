"""MCP Agent Adapter connecting AgenticLLMAgent with MCP Tools and Skills."""

import time
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure base paths available
base_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(base_dir))

from ai_agent import AgenticLLMAgent
from evals_framework.adapters.base import BaseAgentAdapter, AgentRunOutput


class MCPAgentAdapter(BaseAgentAdapter):
    """Adapter for the native MCP Tool & Skill powered AgenticLLMAgent."""

    def __init__(
        self,
        adapter_id: str = "mcp_agent_default",
        name: str = "MCP Tool & Skill Agent",
        description: str = "Native autonomous agent equipped with MCP tools (math, weather, search, products, files) and skills.",
        model: str = "ollama/qwen2.5-coder:7b",
        gateway_url: str = "http://localhost:8000",
        gateway_transport: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            adapter_id=adapter_id,
            name=name,
            description=description,
            model=model,
            config=config or {}
        )
        self.gateway_url = gateway_url
        self.gateway_transport = gateway_transport
        self._agent: Optional[AgenticLLMAgent] = None

    async def initialize(self) -> None:
        if not self._agent:
            self._agent = AgenticLLMAgent(
                gateway_url=self.gateway_url,
                gateway_transport=self.gateway_transport,
                agent_name=self.name,
                caller_id="evals_mcp_adapter",
                model=self.model or "ollama/qwen2.5-coder:7b"
            )
            await self._agent.initialize()

    async def close(self) -> None:
        if self._agent:
            await self._agent.close()
            self._agent = None

    async def run(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        caller_context: Optional[Dict[str, Any]] = None,
        skill_name: Optional[str] = None,
        skill_args: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> AgentRunOutput:
        await self.initialize()
        assert self._agent is not None

        # Reset history for isolated test runs
        self._agent.clear_history(reset_skills=True)
        if session_id:
            self._agent.session_id = session_id
        if self.model and self._agent.model != self.model:
            self._agent.model = self.model

        # Activate skill if specified in benchmark test case
        if skill_name:
            await self._agent.activate_skill(skill_name, skill_args)

        start_time = time.time()
        res = await self._agent.run(prompt, caller_context=caller_context)
        latency_ms = (time.time() - start_time) * 1000

        return AgentRunOutput(
            response=res.response,
            tool_calls_executed=res.tool_calls_executed,
            total_prompt_tokens=res.total_prompt_tokens,
            total_completion_tokens=res.total_completion_tokens,
            latency_ms=latency_ms,
            session_id=res.session_id,
            active_skills=res.active_skills,
            metadata={"adapter": self.adapter_id, "model": self.model}
        )
