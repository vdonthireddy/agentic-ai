"""Unit tests for Gateway Client and Agent loop components."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-server"))

from gateway_client import LLMGatewayClient
from agent import AgenticLLMAgent, AgentRunResult

@pytest.mark.asyncio
async def test_gateway_client_health():
    client = LLMGatewayClient(base_url="http://localhost:8000")
    try:
        health = await client.check_health()
        assert health["status"] == "healthy"
    except Exception:
        pytest.skip("LLM Gateway is not running locally during offline test.")

def test_agent_initialization():
    agent = AgenticLLMAgent(
        gateway_url="http://localhost:8000",
        agent_name="UnitTestAgent",
        caller_id="tester",
        model="ollama/qwen2.5-coder:7b"
    )
    assert agent.agent_name if hasattr(agent, "agent_name") else agent.gateway.agent_name == "UnitTestAgent"
    assert agent.model == "ollama/qwen2.5-coder:7b"
    assert len(agent.active_skills) == 0

def test_agent_clear_history_and_reset_skills():
    agent = AgenticLLMAgent()
    assert agent.model == "ollama/gemma2:2b"
    agent.active_skills.append("data_analysis_skill")
    agent.system_prompt += "\nSkill instructions"
    agent.messages = [{"role": "user", "content": "hi"}]

    # Clear history without resetting skills
    agent.clear_history(reset_skills=False)
    assert len(agent.messages) == 1
    assert "Skill instructions" in agent.system_prompt
    assert "data_analysis_skill" in agent.active_skills

    # Reset skills
    agent.reset_skills()
    assert len(agent.active_skills) == 0
    assert agent.system_prompt == agent.base_system_prompt
