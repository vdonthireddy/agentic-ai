"""
Unit tests for Context Compaction in llm_gateway.
"""

import pytest
from fastapi.testclient import TestClient
from llm_gateway.app import app
from llm_gateway.compact import (
    estimate_tokens,
    estimate_messages_tokens,
    summarize_transcript_fallback,
    compact_conversation_history
)

client = TestClient(app)


def test_estimate_tokens():
    assert estimate_tokens("") == 0
    assert estimate_tokens("hello") == 1
    assert estimate_tokens("a" * 400) == 100


def test_estimate_messages_tokens():
    msgs = [
        {"role": "system", "content": "You are a travel guide."},
        {"role": "user", "content": "What is the weather in Paris?"},
        {"role": "assistant", "content": "It is 68F and sunny."}
    ]
    tokens = estimate_messages_tokens(msgs)
    assert tokens > 15


@pytest.mark.asyncio
async def test_compact_short_conversation():
    msgs = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hi"}
    ]
    result = await compact_conversation_history(msgs)
    assert result["tokens_saved"] == 0
    assert len(result["compacted_messages"]) == len(msgs)


@pytest.mark.asyncio
async def test_compact_long_conversation():
    msgs = [{"role": "system", "content": "You are Donna, executive assistant."}]
    
    # Add 12 conversation turns
    for i in range(12):
        msgs.append({"role": "user", "content": f"Step {i}: Can you check item #{i} in the product database and calculate price?"})
        msgs.append({"role": "assistant", "content": f"Step {i}: Item #{i} costs ${i*10}. Tool calculate returned ${i*10 + 5} with shipping."})

    result = await compact_conversation_history(msgs, keep_recent_turns=2)
    assert result["tokens_saved"] > 0
    assert result["savings_percent"] > 30.0
    assert len(result["compacted_messages"]) < len(msgs)
    
    # Check that system prompt and summary card exist
    assert result["compacted_messages"][0]["role"] == "system"
    assert result["compacted_messages"][1]["is_compaction_summary"] is True
    # Recent turns are retained
    assert result["compacted_messages"][-1]["role"] == "assistant"


def test_compact_api_endpoint():
    msgs = [{"role": "system", "content": "You are Donna."}]
    for i in range(8):
        msgs.append({"role": "user", "content": f"Query {i} regarding budget allocations."})
        msgs.append({"role": "assistant", "content": f"Response {i}: Budget for team {i} is approved at $5,000."})

    resp = client.post("/api/chat/compact", json={"messages": msgs, "keep_recent_turns": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["tokens_saved"] > 0
    assert data["savings_percent"] > 0
