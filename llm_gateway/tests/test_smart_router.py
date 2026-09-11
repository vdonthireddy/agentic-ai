"""
Unit and Integration tests for Smart Router dynamic routing, accuracy thresholds,
model selection, execution traces, and API endpoints.
"""

import pytest
import json
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from llm_gateway.app import app
from llm_gateway.smart_router import (
    smart_router,
    SmartRouter,
    RouteRequest,
    DEFAULT_CATEGORIES,
    CategoryConfig
)
from llm_gateway.db import (
    save_smart_router_log,
    query_smart_router_logs,
    get_smart_router_log,
    clear_smart_router_logs
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_smart_router_fixture():
    from llm_gateway.smart_router import smart_router, DEFAULT_CATEGORIES
    raw_cats = {}
    for k, v in DEFAULT_CATEGORIES.items():
        if isinstance(v, CategoryConfig):
            raw_cats[k] = v.model_dump()
        elif isinstance(v, dict):
            raw_cats[k] = dict(v)
    smart_router.save_config({
        "enabled": True,
        "default_reasoning_model": "ollama/llama3.2:latest",
        "fallback_model": "ollama/mistral:latest",
        "categories": raw_cats
    })
    yield
    smart_router.save_config({
        "enabled": True,
        "default_reasoning_model": "ollama/llama3.2:latest",
        "fallback_model": "ollama/mistral:latest",
        "categories": raw_cats
    })


def test_smart_router_config_defaults():
    """Verify Smart Router default models, accuracy thresholds, and category definitions."""
    router = SmartRouter()
    cfg = router.get_config_dict()
    assert cfg["enabled"] is True
    assert "default_reasoning_model" in cfg
    assert "categories" in cfg
    
    cats = cfg["categories"]
    assert "coding" in cats
    assert cats["coding"]["accuracy_threshold"] == 0.75
    assert cats["coding"]["target_model"] == "ollama/qwen2.5-coder:7b"
    
    assert "complex_work" in cats
    assert cats["complex_work"]["accuracy_threshold"] == 0.80
    assert cats["complex_work"]["target_model"] == "ollama/mistral:latest"
    
    assert "general_qa" in cats
    assert cats["general_qa"]["accuracy_threshold"] == 0.70
    assert cats["general_qa"]["target_model"] == "ollama/llama3.2:latest"
    
    assert "fast_lightweight" in cats
    assert cats["fast_lightweight"]["accuracy_threshold"] == 0.60
    assert cats["fast_lightweight"]["target_model"] == "ollama/gemma2:2b"


def test_smart_router_heuristic_classification():
    """Test heuristic classification fallback across distinct domains."""
    router = SmartRouter()
    
    # Coding query
    res_code = router._heuristic_classify("Write a python function to compute fibonacci numbers with memoization")
    assert res_code["category"] == "coding"
    assert "qwen" in res_code["selected_model"]
    assert res_code["confidence"] >= 0.75

    # Complex reasoning query
    res_complex = router._heuristic_classify("Evaluate the distributed architectural trade-offs between Raft consensus and Paxos")
    assert res_complex["category"] == "complex_work"
    assert "mistral" in res_complex["selected_model"]
    assert res_complex["confidence"] >= 0.80

    # Fast lightweight query
    res_fast = router._heuristic_classify("Hi there!")
    assert res_fast["category"] == "fast_lightweight"
    assert "gemma2" in res_fast["selected_model"]
    assert res_fast["confidence"] >= 0.60

    # Creative writing query
    res_creative = router._heuristic_classify("Write a poetic story about an astronaut gazing at Earth from orbit")
    assert res_creative["category"] == "creative_writing"
    assert res_creative["confidence"] >= 0.70


def test_smart_router_parse_reasoning_output():
    """Test JSON parsing and threshold evaluation of reasoning model outputs."""
    router = SmartRouter()

    # Valid markdown JSON block
    raw_json = """```json
    {
      "category": "coding",
      "confidence": 0.95,
      "selected_model": "ollama/qwen2.5-coder:7b",
      "reasoning": "The user is asking for an optimized sorting algorithm in Python.",
      "prompt_for_model": "Write an optimized Python sort"
    }
    ```"""
    parsed = router._parse_reasoning_output(raw_json, "test prompt")
    assert parsed["category"] == "coding"
    assert parsed["confidence"] == 0.95
    assert parsed["selected_model"] == "ollama/qwen2.5-coder:7b"
    assert "Python" in parsed["reasoning"]

    # Free text fallback
    free_text = "I think this is about general knowledge and we should use llama."
    parsed2 = router._parse_reasoning_output(free_text, "What is the capital of France?")
    assert parsed2["category"] == "general_qa"
    assert parsed2["confidence"] > 0.0

    # Ensure ollama/gemma2:2b is preserved and not mistakenly normalized to llama due to substring in 'ollama'
    raw_gemma = """{
      "category": "creative_writing",
      "confidence": 0.93,
      "selected_model": "ollama/gemma2:2b",
      "reasoning": "The prompt requires creative writing, best suited for gemma.",
      "prompt_for_model": "write a limerick"
    }"""
    parsed_gemma = router._parse_reasoning_output(raw_gemma, "write a limerick")
    assert parsed_gemma["selected_model"] == "ollama/gemma2:2b"


@pytest.mark.asyncio
async def test_smart_router_accuracy_threshold_enforcement():
    """Test that when confidence falls below the category accuracy threshold, it safely falls back."""
    router = SmartRouter()

    # Mock litellm to simulate reasoning model returning low confidence (0.50 < threshold 0.75)
    mock_stage1_choice = AsyncMock()
    mock_stage1_choice.message.content = json.dumps({
        "category": "coding",
        "confidence": 0.50,  # Below coding threshold 0.75!
        "selected_model": "ollama/qwen2.5-coder:7b",
        "reasoning": "Uncertain if code is actually needed.",
        "prompt_for_model": "test"
    })
    mock_stage1_resp = AsyncMock()
    mock_stage1_resp.choices = [mock_stage1_choice]
    mock_stage1_resp.usage.total_tokens = 50

    mock_stage2_choice = AsyncMock()
    mock_stage2_choice.message.content = "Here is the response."
    mock_stage2_resp = AsyncMock()
    mock_stage2_resp.choices = [mock_stage2_choice]
    mock_stage2_resp.usage.prompt_tokens = 10
    mock_stage2_resp.usage.completion_tokens = 15
    mock_stage2_resp.usage.total_tokens = 25

    with patch("litellm.acompletion", side_effect=[mock_stage1_resp, mock_stage2_resp]):
        result = await router.route_and_execute(
            RouteRequest(prompt="Show me how to sort a list")
        )

        assert result["success"] is True
        trace = result["trace"]
        decision = trace["routing_decision"]
        assert decision["threshold_met"] is False
        assert decision["threshold"] == 0.75
        assert decision["confidence"] == 0.50
        # Target routed to fallback model because confidence was below threshold
        assert "fallback" in decision["reasoning"].lower()


@pytest.mark.asyncio
async def test_smart_router_full_trace_persistence():
    """Verify full call log fields are stored in SQLite and queryable."""
    clear_smart_router_logs()

    test_trace = {
        "id": "sr_test_trace_123",
        "prompt": "Write a python web server",
        "reasoning_model": "ollama/llama3.2:latest",
        "reasoning_raw_response": '{"category": "coding", "confidence": 0.95}',
        "routing_decision": {
            "category": "coding",
            "confidence": 0.95,
            "threshold": 0.75,
            "threshold_met": True,
            "selected_model": "ollama/qwen2.5-coder:7b",
            "reasoning": "Code request"
        },
        "category": "coding",
        "confidence": 0.95,
        "threshold": 0.75,
        "threshold_met": True,
        "selected_model": "ollama/qwen2.5-coder:7b",
        "target_model": "ollama/qwen2.5-coder:7b",
        "target_prompt": "Write a python web server",
        "target_response": "import http.server...",
        "stage1_latency_ms": 120.5,
        "stage2_latency_ms": 340.2,
        "total_latency_ms": 460.7,
        "prompt_tokens": 45,
        "completion_tokens": 120,
        "total_tokens": 165,
        "status": "SUCCESS"
    }

    saved = save_smart_router_log(test_trace)
    assert saved["id"] == "sr_test_trace_123"

    # Query back
    queried = query_smart_router_logs(limit=10, category="coding")
    assert queried["total"] >= 1
    found = [l for l in queried["logs"] if l["id"] == "sr_test_trace_123"]
    assert len(found) == 1
    assert found[0]["target_model"] == "ollama/qwen2.5-coder:7b"
    assert found[0]["threshold_met"] is True

    # Get single trace
    single = get_smart_router_log("sr_test_trace_123")
    assert single is not None
    assert single["prompt"] == "Write a python web server"
    assert single["reasoning_model"] == "ollama/llama3.2:latest"
    assert single["target_response"] == "import http.server..."


def test_smart_router_api_endpoints():
    """Verify FastAPI /api/smart-router/* routes."""
    # 1. Config GET
    res_cfg = client.get("/api/smart-router/config")
    assert res_cfg.status_code == 200
    cfg_data = res_cfg.json()
    assert "categories" in cfg_data
    assert "default_reasoning_model" in cfg_data

    # 2. Config POST
    update_payload = {
        "default_reasoning_model": "ollama/mistral:latest",
        "categories": {
            "coding": {
                "name": "Coding",
                "description": "Programming",
                "accuracy_threshold": 0.85,
                "target_model": "ollama/qwen2.5-coder:7b"
            }
        }
    }
    res_update = client.post("/api/smart-router/config", json=update_payload)
    assert res_update.status_code == 200
    updated_cfg = res_update.json()
    assert updated_cfg["default_reasoning_model"] == "ollama/mistral:latest"
    assert updated_cfg["categories"]["coding"]["accuracy_threshold"] == 0.85

    # 3. Logs GET
    res_logs = client.get("/api/smart-router/logs?limit=5")
    assert res_logs.status_code == 200
    assert "logs" in res_logs.json()


def test_smart_router_chat_completions_model_auto():
    """Test that /v1/chat/completions accepts model='smart-router' and attaches trace."""
    mock_stage1_choice = AsyncMock()
    mock_stage1_choice.message.content = json.dumps({
        "category": "general_qa",
        "confidence": 0.90,
        "selected_model": "ollama/llama3.2:latest",
        "reasoning": "General knowledge query",
        "prompt_for_model": "Why is the sky blue?"
    })
    mock_stage1_resp = AsyncMock()
    mock_stage1_resp.choices = [mock_stage1_choice]
    mock_stage1_resp.usage.total_tokens = 40

    mock_stage2_choice = AsyncMock()
    mock_stage2_choice.message.content = "The sky is blue because of Rayleigh scattering."
    mock_stage2_resp = AsyncMock()
    mock_stage2_resp.choices = [mock_stage2_choice]
    mock_stage2_resp.usage.prompt_tokens = 15
    mock_stage2_resp.usage.completion_tokens = 25
    mock_stage2_resp.usage.total_tokens = 40

    with patch("litellm.acompletion", side_effect=[mock_stage1_resp, mock_stage2_resp]):
        res = client.post("/v1/chat/completions", json={
            "model": "smart-router",
            "messages": [{"role": "user", "content": "Why is the sky blue?"}]
        })
        assert res.status_code == 200
        data = res.json()
        assert "choices" in data
        assert "Rayleigh scattering" in data["choices"][0]["message"]["content"]
        assert "gateway_metadata" in data
        assert "smart_router_trace" in data["gateway_metadata"]
        assert data["gateway_metadata"]["smart_router_trace"]["category"] == "general_qa"


@pytest.mark.asyncio
async def test_smart_router_disabled_bypass():
    """Verify that setting USE_SMART_ROUTING=False bypasses Stage 1 reasoning."""
    original_enabled = smart_router.config.enabled
    try:
        # Disable smart routing
        smart_router.config.enabled = False

        mock_target_choice = AsyncMock()
        mock_target_choice.message.content = "Direct execution response without reasoning dispatch."
        mock_target_resp = AsyncMock()
        mock_target_resp.choices = [mock_target_choice]
        mock_target_resp.usage.prompt_tokens = 10
        mock_target_resp.usage.completion_tokens = 20
        mock_target_resp.usage.total_tokens = 30

        # Litellm should be called only ONCE for Stage 2, not for Stage 1
        with patch("litellm.acompletion", return_value=mock_target_resp) as mock_litellm:
            req = RouteRequest(prompt="Write quick hello code")
            result = await smart_router.route_and_execute(req)

            assert result["success"] is True
            assert result["response"] == "Direct execution response without reasoning dispatch."
            assert mock_litellm.call_count == 1  # Only Stage 2 was executed

            trace = result["trace"]
            assert trace["stage1_latency_ms"] == 0.0
            assert trace["category"] == "direct_bypass"
            assert trace["routing_decision"]["category"] == "direct_bypass"
            assert "USE_SMART_ROUTING=False" in trace["routing_decision"]["reasoning"]

        # Test toggling via /api/smart-router/config
        res = client.post("/api/smart-router/config", json={"use_smart_routing": True})
        assert res.status_code == 200
        assert res.json()["enabled"] is True
        assert smart_router.config.enabled is True

        # Test toggling via /api/config
        res_gw = client.post("/api/config", json={"smart_router_enabled": False})
        assert res_gw.status_code == 200
        assert smart_router.config.enabled is False

    finally:
        smart_router.config.enabled = original_enabled
        client.post("/api/smart-router/config", json={"use_smart_routing": original_enabled})
