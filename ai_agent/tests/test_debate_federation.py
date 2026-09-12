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

@pytest.mark.asyncio
async def test_multi_agent_debate_separate_models():
    """Verify distinct models are dispatched to Proposer, Critic, and Arbitrator roles."""
    manager = MultiAgentDebateManager(
        gateway_url="http://mock-gateway:8000",
        proposer_model="proposer-model-v1",
        critic_model="critic-model-v2",
        arbitrator_model="arbitrator-model-v3"
    )

    calls = []
    async def mock_chat(*args, **kwargs):
        calls.append(kwargs)
        role = kwargs.get("caller_context", {}).get("role", "")
        return {
            "choices": [{"message": {"content": f"Response from {role}. RISK_SCORE: 4.0"}}],
            "usage": {"total_tokens": 50}
        }

    manager.gateway.chat_completion = AsyncMock(side_effect=mock_chat)

    result = await manager.run_debate(topic="Kubernetes vs Nomad", rounds=1)
    assert isinstance(result, DebateResult)
    assert result.proposer_model == "proposer-model-v1"
    assert result.critic_model == "critic-model-v2"
    assert result.arbitrator_model == "arbitrator-model-v3"

    # Verify models used in each call
    assert len(calls) == 3
    assert calls[0]["model"] == "proposer-model-v1"
    assert calls[1]["model"] == "critic-model-v2"
    assert calls[2]["model"] == "arbitrator-model-v3"

@pytest.mark.asyncio
async def test_debate_endpoint_separate_models():
    """Verify router.run_multi_agent_debate parses separate models or falls back."""
    from ai_agent.router import run_multi_agent_debate, DebateRequest
    from unittest.mock import patch

    # 1. Test separate models passed
    with patch("ai_agent.debate.MultiAgentDebateManager.run_debate", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = DebateResult(
            debate_id="test_deb",
            topic="Testing",
            rounds_executed=1,
            rounds=[],
            consensus_verdict="All clear",
            confidence_score=95.0,
            key_vulnerabilities_resolved=[],
            proposer_model="p-mod",
            critic_model="c-mod",
            arbitrator_model="a-mod"
        )
        req = DebateRequest(
            topic="Testing",
            rounds=1,
            proposer_model="p-mod",
            critic_model="c-mod",
            arbitrator_model="a-mod"
        )
        data = await run_multi_agent_debate(req)
        assert data["proposer_model"] == "p-mod"
        assert data["critic_model"] == "c-mod"
        assert data["arbitrator_model"] == "a-mod"

    # 2. Test fallback to req.model when role-specific models are omitted
    with patch("ai_agent.debate.MultiAgentDebateManager.run_debate", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = DebateResult(
            debate_id="test_deb2",
            topic="Testing Fallback",
            rounds_executed=1,
            rounds=[],
            consensus_verdict="Fallback consensus",
            confidence_score=90.0,
            key_vulnerabilities_resolved=[],
            proposer_model="fallback-mod",
            critic_model="fallback-mod",
            arbitrator_model="fallback-mod"
        )
        req = DebateRequest(
            topic="Testing Fallback",
            rounds=1,
            model="fallback-mod"
        )
        data = await run_multi_agent_debate(req)
        assert data["proposer_model"] == "fallback-mod"
        assert data["critic_model"] == "fallback-mod"
        assert data["arbitrator_model"] == "fallback-mod"

