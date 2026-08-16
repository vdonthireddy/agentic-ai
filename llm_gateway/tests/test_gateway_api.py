"""Unit tests for FastAPI endpoints in LLM Gateway supporting local and cloud models."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app

client = TestClient(app)

def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "default_model" in data
    assert "supported_providers" in data
    assert "ollama" in data["supported_providers"]
    assert "openai" in data["supported_providers"]
    assert "anthropic" in data["supported_providers"]
    assert "gemini" in data["supported_providers"]

def test_models_endpoint():
    res = client.get("/v1/models")
    assert res.status_code == 200
    data = res.json()
    assert "data" in data
    assert len(data["data"]) > 0
    assert data["data"][0]["id"] == "ollama/gemma2:2b"
    ids = [m["id"] for m in data["data"]]
    assert "ollama/gemma2:2b" in ids
    assert "ollama/qwen2.5-coder:7b" in ids
    assert "openai/gpt-4o" in ids
    assert "anthropic/claude-3-5-sonnet-20241022" in ids

def test_logs_endpoint():
    res = client.get("/v1/logs?limit=5")
    assert res.status_code == 200
    data = res.json()
    assert "logs" in data
    assert "count" in data

def test_stats_endpoint():
    res = client.get("/v1/stats")
    assert res.status_code == 200
    data = res.json()
    assert "total_calls" in data
    assert "token_usage" in data

def test_dashboard_static_endpoint():
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]

def test_chat_clear_endpoint():
    res = client.post("/api/chat/clear", json={"session_id": "test_session_123"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["old_conversation_id"] == "test_session_123"
    assert "new_conversation_id" in data

def test_hierarchical_logs_endpoint():
    res = client.get("/v1/logs?hierarchical=true&limit=5")
    assert res.status_code == 200
    data = res.json()
    assert data.get("hierarchical") is True
    assert "conversations" in data

def test_chat_missing_message_validation():
    res = client.post("/api/chat", json={"session_id": "test_session"})
    assert res.status_code == 422

@patch("litellm.acompletion")
def test_chat_completions_cloud_model(mock_acompletion):
    # Mock LiteLLM response
    mock_resp = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "This is a cloud model response."
    mock_choice.message.tool_calls = None
    mock_resp.choices = [mock_choice]
    mock_resp.usage.prompt_tokens = 15
    mock_resp.usage.completion_tokens = 8
    mock_resp.usage.total_tokens = 23
    mock_resp.model_dump.return_value = {
        "id": "chatcmpl-123",
        "choices": [{"message": {"role": "assistant", "content": "This is a cloud model response."}}],
        "usage": {"prompt_tokens": 15, "completion_tokens": 8, "total_tokens": 23}
    }
    mock_acompletion.return_value = mock_resp

    payload = {
        "model": "gpt-4o",  # Shorthand should resolve to openai/gpt-4o
        "messages": [{"role": "user", "content": "Explain quantum computing"}],
        "temperature": 0.3
    }
    headers = {
        "Authorization": "Bearer sk-test-openai-key"
    }

    res = client.post("/v1/chat/completions", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "gateway_metadata" in data
    assert data["gateway_metadata"]["logged"] is True

    # Verify acompletion was called with resolved model and api_key without ollama api_base
    mock_acompletion.assert_called_once()
    called_kwargs = mock_acompletion.call_args.kwargs
    assert called_kwargs["model"] == "openai/gpt-4o"
    assert called_kwargs["api_key"] == "sk-test-openai-key"
    assert "api_base" not in called_kwargs

def test_tools_catalog_endpoint():
    res = client.get("/api/tools")
    assert res.status_code == 200
    data = res.json()
    assert "tools" in data
    names = [t["name"] for t in data["tools"]]
    assert "calculator" in names
    assert "weather" in names
    assert "web_search" in names
    assert "product_knowledge" in names
    assert "workspace_file_ops" in names

def test_tool_execute_endpoint():
    res = client.post("/api/tools/execute", json={
        "tool": "calculator",
        "args": {"expression": "10 * 5 + 2"}
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "52" in str(data["result"])

def test_skills_hub_endpoint():
    res = client.get("/api/skills")
    assert res.status_code == 200
    data = res.json()
    assert "skills" in data
    ids = [s["id"] for s in data["skills"]]
    assert "travel_planner_skill" in ids
    assert "shopping_assistant_skill" in ids
    assert "chef_meal_planner_skill" in ids

def test_custom_skill_lifecycle():
    # Register custom skill
    res = client.post("/api/skills/custom", json={
        "id": "pytest_test_skill",
        "name": "🧪 Pytest Automated Skill",
        "description": "Testing custom skill creation",
        "system_prompt": "You are a test agent."
    })
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Verify in list
    res_list = client.get("/api/skills")
    assert any(s["id"] == "pytest_test_skill" for s in res_list.json()["skills"])

    # Delete custom skill
    res_del = client.delete("/api/skills/custom/pytest_test_skill")
    assert res_del.status_code == 200

def test_workspace_files_api():
    # Write file
    res = client.post("/api/workspace/files", json={
        "filename": "test_api_file.txt",
        "content": "Hello from workspace file API test"
    })
    assert res.status_code == 200

    # Read file
    res_read = client.get("/api/workspace/files/test_api_file.txt")
    assert res_read.status_code == 200
    assert "Hello from workspace" in res_read.json()["content"]

    # List files
    res_list = client.get("/api/workspace/files")
    assert res_list.status_code == 200
    assert any(f["filename"] == "test_api_file.txt" for f in res_list.json()["files"])

    # Delete file
    res_del = client.delete("/api/workspace/files/test_api_file.txt")
    assert res_del.status_code == 200

def test_system_metrics_endpoint():
    res = client.get("/api/system/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "cpu" in data or "os" in data

def test_gateway_config_api():
    res = client.get("/api/config")
    assert res.status_code == 200
    data = res.json()
    assert "default_model" in data
    assert "transport" in data
    assert "provider_keys_status" in data

    # Update config
    res_update = client.post("/api/config", json={
        "default_model": "ollama/qwen2.5-coder:7b"
    })
    assert res_update.status_code == 200
    assert res_update.json()["success"] is True
