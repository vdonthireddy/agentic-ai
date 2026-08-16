"""Unit tests for LLM Gateway multi-provider routing and LiteLLM kwargs resolution."""

import pytest
from unittest.mock import patch, AsyncMock
from llm_gateway.config import GatewayConfig
from llm_gateway.router import resolve_model_name, build_litellm_kwargs, get_available_models


def test_resolve_model_name_default():
    assert resolve_model_name("", "ollama/gemma2:2b") == "ollama/gemma2:2b"
    assert resolve_model_name(None, "ollama/gemma2:2b") == "ollama/gemma2:2b"


def test_resolve_model_name_explicit_providers():
    assert resolve_model_name("openai/gpt-4o", "ollama/llama3.2") == "openai/gpt-4o"
    assert resolve_model_name("anthropic/claude-3-5-sonnet-20241022", "ollama/llama3.2") == "anthropic/claude-3-5-sonnet-20241022"
    assert resolve_model_name("gemini/gemini-2.0-flash", "ollama/llama3.2") == "gemini/gemini-2.0-flash"
    assert resolve_model_name("groq/llama-3.3-70b-versatile", "ollama/llama3.2") == "groq/llama-3.3-70b-versatile"
    assert resolve_model_name("deepseek/deepseek-chat", "ollama/llama3.2") == "deepseek/deepseek-chat"
    assert resolve_model_name("ollama/qwen2.5-coder:7b", "ollama/llama3.2") == "ollama/qwen2.5-coder:7b"
    assert resolve_model_name("azure/my-deployment", "ollama/llama3.2") == "azure/my-deployment"


def test_resolve_model_name_shorthand_cloud_models():
    assert resolve_model_name("gpt-4o", "ollama/llama3.2") == "openai/gpt-4o"
    assert resolve_model_name("gpt-4o-mini", "ollama/llama3.2") == "openai/gpt-4o-mini"
    assert resolve_model_name("o1-preview", "ollama/llama3.2") == "openai/o1-preview"
    assert resolve_model_name("o3-mini", "ollama/llama3.2") == "openai/o3-mini"
    assert resolve_model_name("claude-3-5-sonnet", "ollama/llama3.2") == "anthropic/claude-3-5-sonnet"
    assert resolve_model_name("claude-3-haiku", "ollama/llama3.2") == "anthropic/claude-3-haiku"
    assert resolve_model_name("gemini-2.0-flash", "ollama/llama3.2") == "gemini/gemini-2.0-flash"
    assert resolve_model_name("gemini-1.5-pro", "ollama/llama3.2") == "gemini/gemini-1.5-pro"
    assert resolve_model_name("deepseek-chat", "ollama/llama3.2") == "deepseek/deepseek-chat"
    assert resolve_model_name("deepseek-reasoner", "ollama/llama3.2") == "deepseek/deepseek-reasoner"
    assert resolve_model_name("mistral-large-latest", "ollama/llama3.2") == "mistral/mistral-large-latest"


def test_resolve_model_name_local_shorthands():
    assert resolve_model_name("qwen2.5-coder:7b", "ollama/llama3.2") == "ollama/qwen2.5-coder:7b"
    assert resolve_model_name("llama3.2", "ollama/llama3.2") == "ollama/llama3.2"
    assert resolve_model_name("gemma2:2b", "ollama/llama3.2") == "ollama/gemma2:2b"
    assert resolve_model_name("mistral:latest", "ollama/llama3.2") == "ollama/mistral:latest"


def test_build_litellm_kwargs_ollama():
    config = GatewayConfig(ollama_api_base="http://localhost:11434")
    messages = [{"role": "user", "content": "Hello"}]
    
    kwargs = build_litellm_kwargs(
        target_model="ollama/qwen2.5-coder:7b",
        messages=messages,
        config=config,
        temperature=0.7
    )
    
    assert kwargs["model"] == "ollama/qwen2.5-coder:7b"
    assert kwargs["api_base"] == "http://localhost:11434"
    assert "stop" in kwargs
    assert kwargs["temperature"] == 0.7


def test_build_litellm_kwargs_openai_no_ollama_base():
    config = GatewayConfig(
        ollama_api_base="http://localhost:11434",
        openai_api_key="sk-test-openai-key"
    )
    messages = [{"role": "user", "content": "Hello"}]
    
    kwargs = build_litellm_kwargs(
        target_model="openai/gpt-4o",
        messages=messages,
        config=config,
        temperature=0.2
    )
    
    assert kwargs["model"] == "openai/gpt-4o"
    # Crucial: Must NOT send ollama_api_base to OpenAI!
    assert "api_base" not in kwargs
    assert kwargs.get("api_key") == "sk-test-openai-key"
    assert "stop" not in kwargs


def test_build_litellm_kwargs_anthropic():
    config = GatewayConfig(
        anthropic_api_key="sk-ant-test-key"
    )
    messages = [{"role": "user", "content": "Hello"}]
    
    kwargs = build_litellm_kwargs(
        target_model="anthropic/claude-3-5-sonnet-20241022",
        messages=messages,
        config=config,
        temperature=0.5
    )
    
    assert kwargs["model"] == "anthropic/claude-3-5-sonnet-20241022"
    assert "api_base" not in kwargs
    assert kwargs.get("api_key") == "sk-ant-test-key"


def test_build_litellm_kwargs_custom_request_override():
    config = GatewayConfig()
    messages = [{"role": "user", "content": "Hello"}]
    
    kwargs = build_litellm_kwargs(
        target_model="openai/custom-llm",
        messages=messages,
        config=config,
        api_key="custom-req-key",
        api_base="https://custom-proxy.example.com/v1"
    )
    
    assert kwargs["model"] == "openai/custom-llm"
    assert kwargs["api_key"] == "custom-req-key"
    assert kwargs["api_base"] == "https://custom-proxy.example.com/v1"


def test_get_available_models_returns_both_local_and_cloud():
    config = GatewayConfig(ollama_api_base="http://localhost:11434")
    models = get_available_models(config)
    
    model_ids = [m["id"] for m in models]
    providers = {m["provider"] for m in models}
    
    assert "ollama/qwen2.5-coder:7b" in model_ids
    assert "openai/gpt-4o" in model_ids
    assert "anthropic/claude-3-5-sonnet-20241022" in model_ids
    assert "gemini/gemini-2.0-flash" in model_ids
    assert "groq/llama-3.3-70b-versatile" in model_ids
    assert "deepseek/deepseek-chat" in model_ids
    
    assert "ollama" in providers
    assert "openai" in providers
    assert "anthropic" in providers
    assert "gemini" in providers
