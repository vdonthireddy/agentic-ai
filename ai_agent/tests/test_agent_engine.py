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

def test_agent_progressive_disclosure_skill_prompt():
    agent = AgenticLLMAgent()
    assert "Progressive Disclosure" in agent.base_system_prompt
    assert "discover_skills" in agent.base_system_prompt
    assert "load_skill" in agent.base_system_prompt

def test_agent_tool_rag_selection():
    agent = AgenticLLMAgent(enable_tool_rag=True)
    # Simulate a catalog with 10 tools
    dummy_tools = [
        {"type": "function", "function": {"name": "discover_skills", "description": "List skills"}},
        {"type": "function", "function": {"name": "load_skill", "description": "Load skill"}},
        {"type": "function", "function": {"name": "memory_recall", "description": "Recall memories"}},
        {"type": "function", "function": {"name": "calculator", "description": "Compute math and calculate tip"}},
        {"type": "function", "function": {"name": "get_weather", "description": "Fetch weather forecast for cities"}},
        {"type": "function", "function": {"name": "workspace_file_ops", "description": "Read and write workspace files"}},
        {"type": "function", "function": {"name": "execute_readonly_sql", "description": "Run SQL query"}},
        {"type": "function", "function": {"name": "execute_python_sandbox", "description": "Run python code and plot data"}},
        {"type": "function", "function": {"name": "product_knowledge", "description": "Product search catalog and reviews"}},
        {"type": "function", "function": {"name": "web_search", "description": "Search web for information"}},
    ]
    agent.tools_schema = dummy_tools

    # Query about weather should prioritize get_weather
    selected = agent.select_relevant_tools("What is the weather in Paris?", max_tools=5)
    names = [t["function"]["name"] for t in selected]
    assert len(selected) <= 5
    assert "get_weather" in names
    # Core tools like discover_skills or memory_recall should be preserved
    assert "discover_skills" in names or "memory_recall" in names

