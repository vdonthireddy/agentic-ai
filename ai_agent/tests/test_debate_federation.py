"""Tests for MultiAgentDebate and FederatedMCPManager."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from ai_agent.debate import MultiAgentDebateManager, DebateResult
from ai_agent.federation import FederatedMCPManager, MCPServerConfig

@pytest.mark.asyncio
async def test_multi_agent_debate_mocked():
    manager = MultiAgentDebateManager(gateway_url="http://mock-gateway:8000")
    
    mock_resp_proposer = {
        "choices": [{"message": {"content": "Initial proposal: Use blue-green deployment."}}],
        "usage": {"total_tokens": 120}
    }
    mock_resp_critic = {
        "choices": [{"message": {"content": "Criticism: Traffic cutover might drop websockets. RISK_SCORE: 6.5"}}],
        "usage": {"total_tokens": 90}
    }
    mock_resp_arbitrator = {
        "choices": [{"message": {"content": "Final synthesis: Graceful websocket drain with blue-green deployment."}}],
        "usage": {"total_tokens": 150}
    }

    manager.gateway.chat_completion = AsyncMock(side_effect=[
        mock_resp_proposer,
        mock_resp_critic,
        mock_resp_arbitrator
    ])

    result = await manager.run_debate(topic="Zero downtime deploy", rounds=1)
    assert isinstance(result, DebateResult)
    assert result.rounds_executed == 1
    assert "websocket drain" in result.consensus_verdict.lower()
    assert result.total_tokens == 360

def test_federated_mcp_manager_registration():
    fed = FederatedMCPManager()
    config = MCPServerConfig(
        server_id="github_mcp",
        name="GitHub MCP Server",
        transport="stdio",
        command="python3",
        args=["./scripts/mock_server.py"]
    )
    fed.register_server(config)
    assert "github_mcp" in fed.servers
    assert "github_mcp" in fed.server_configs
