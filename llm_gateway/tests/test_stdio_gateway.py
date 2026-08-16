"""Unit tests for LLM Gateway Stdio transport and transport switcher."""

import sys
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from llm_gateway.stdio_gateway import handle_stdio_request
from ai_agent.gateway_client import LLMGatewayClient


@pytest.mark.asyncio
async def test_handle_stdio_health_and_ping():
    res = await handle_stdio_request({"action": "health"})
    assert res["status"] == "healthy"
    assert res["transport"] == "stdio"
    assert "default_model" in res

    res_ping = await handle_stdio_request({"action": "ping"})
    assert res_ping["status"] == "healthy"


@pytest.mark.asyncio
async def test_handle_stdio_models():
    res = await handle_stdio_request({"action": "models"})
    assert res["object"] == "list"
    assert len(res["data"]) > 0
    assert any(m["id"] == "ollama/gemma2:2b" for m in res["data"])


@pytest.mark.asyncio
async def test_handle_stdio_stats():
    res = await handle_stdio_request({"action": "stats"})
    assert "total_calls" in res
    assert "successful_calls" in res
    assert "token_usage" in res


@pytest.mark.asyncio
async def test_gateway_client_stdio_health_and_models():
    client = LLMGatewayClient(transport="stdio")
    assert client.transport == "stdio"

    # Mock subprocess communication
    with patch.object(client, "_send_stdio_command", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {
            "status": "healthy",
            "transport": "stdio",
            "default_model": "ollama/gemma2:2b"
        }
        health = await client.check_health()
        assert health["status"] == "healthy"
        mock_send.assert_called_once_with({"action": "health"})

    with patch.object(client, "_send_stdio_command", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {
            "object": "list",
            "data": [{"id": "ollama/gemma2:2b"}]
        }
        models = await client.list_models()
        assert len(models) == 1
        assert models[0]["id"] == "ollama/gemma2:2b"
        mock_send.assert_called_once_with({"action": "models"})

    await client.close()


@pytest.mark.asyncio
async def test_gateway_client_stdio_chat_completion():
    client = LLMGatewayClient(transport="stdio", session_id="test_sess")
    
    mock_resp = {
        "id": "chatcmpl_mock123",
        "object": "chat.completion",
        "model": "ollama/gemma2:2b",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Hello via stdio!"
                }
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15
        }
    }

    with patch.object(client, "_send_stdio_command", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = mock_resp
        res = await client.chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
            model="ollama/gemma2:2b"
        )
        assert res["choices"][0]["message"]["content"] == "Hello via stdio!"
        mock_send.assert_called_once()
        sent_payload = mock_send.call_args[0][0]
        assert sent_payload["action"] == "chat_completions"
        assert sent_payload["model"] == "ollama/gemma2:2b"

    await client.close()


def test_parameterized_config_factory_and_overrides():
    from llm_gateway.config import get_config, GatewayConfig

    # 1. Custom factory initialization
    custom_cfg = get_config(
        transport="stdio",
        default_model="ollama/mistral:latest",
        port=9000
    )
    assert custom_cfg.transport == "stdio"
    assert custom_cfg.default_model == "ollama/mistral:latest"
    assert custom_cfg.port == 9000

    # 2. Immutable override chaining
    modified_cfg = custom_cfg.with_overrides(transport="http", default_model="ollama/qwen2.5-coder:7b")
    assert modified_cfg.transport == "http"
    assert modified_cfg.default_model == "ollama/qwen2.5-coder:7b"
    assert modified_cfg.port == 9000  # preserved from custom_cfg
    assert custom_cfg.transport == "stdio"  # original untouched
