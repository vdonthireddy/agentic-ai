"""Model resolution, provider routing, and model discovery for LLM Gateway."""

import os
import re
import urllib.request
import json
from typing import Dict, Any, List, Optional, Union
from llm_gateway.config import GatewayConfig

# Pre-defined catalog of popular local and cloud models
CATALOG_MODELS: List[Dict[str, Any]] = [
    # Local Ollama Models
    {
        "id": "ollama/gemma2:2b",
        "name": "Gemma 2 2B",
        "provider": "ollama",
        "owned_by": "ollama",
        "description": "Compact, efficient Google Gemma 2B local model",
        "supports_tools": True,
        "is_local": True
    },
    {
        "id": "ollama/qwen2.5-coder:7b",
        "name": "Qwen 2.5 Coder 7B",
        "provider": "ollama",
        "owned_by": "ollama",
        "description": "High-performance local code and tool-calling reasoning model",
        "supports_tools": True,
        "is_local": True
    },
    {
        "id": "ollama/llama3.2",
        "name": "LLaMA 3.2 3B",
        "provider": "ollama",
        "owned_by": "ollama",
        "description": "Fast, lightweight local conversational agent model",
        "supports_tools": True,
        "is_local": True
    },
    {
        "id": "ollama/mistral:latest",
        "name": "Mistral 7B",
        "provider": "ollama",
        "owned_by": "ollama",
        "description": "General-purpose instruction tuned local model",
        "supports_tools": True,
        "is_local": True
    },
    {
        "id": "ollama/deepseek-r1:8b",
        "name": "DeepSeek R1 8B",
        "provider": "ollama",
        "owned_by": "ollama",
        "description": "Open-weights reasoning model running locally via Ollama",
        "supports_tools": False,
        "is_local": True
    },

    # OpenAI Models
    {
        "id": "openai/gpt-4o",
        "name": "GPT-4o (Omni)",
        "provider": "openai",
        "owned_by": "openai",
        "description": "Flagship high-intelligence multimodal OpenAI model with tool-use",
        "supports_tools": True,
        "is_local": False
    },
    {
        "id": "openai/gpt-4o-mini",
        "name": "GPT-4o Mini",
        "provider": "openai",
        "owned_by": "openai",
        "description": "Fast, cost-efficient small model for everyday agent tasks",
        "supports_tools": True,
        "is_local": False
    },
    {
        "id": "openai/o3-mini",
        "name": "o3-mini Reasoning",
        "provider": "openai",
        "owned_by": "openai",
        "description": "High-speed reasoning model specialized for coding and math",
        "supports_tools": True,
        "is_local": False
    },

    # Anthropic Claude Models
    {
        "id": "anthropic/claude-3-5-sonnet-20241022",
        "name": "Claude 3.5 Sonnet",
        "provider": "anthropic",
        "owned_by": "anthropic",
        "description": "State-of-the-art coding and agentic reasoning model",
        "supports_tools": True,
        "is_local": False
    },
    {
        "id": "anthropic/claude-3-5-haiku-20241022",
        "name": "Claude 3.5 Haiku",
        "provider": "anthropic",
        "owned_by": "anthropic",
        "description": "Ultra-fast, responsive lightweight Claude model",
        "supports_tools": True,
        "is_local": False
    },

    # Google Gemini Models
    {
        "id": "gemini/gemini-2.0-flash",
        "name": "Gemini 2.0 Flash",
        "provider": "gemini",
        "owned_by": "google",
        "description": "Next-gen multimodal model with native tool use and high speed",
        "supports_tools": True,
        "is_local": False
    },
    {
        "id": "gemini/gemini-1.5-pro",
        "name": "Gemini 1.5 Pro",
        "provider": "gemini",
        "owned_by": "google",
        "description": "Complex reasoning model with large 2M context window",
        "supports_tools": True,
        "is_local": False
    },

    # Groq Cloud
    {
        "id": "groq/llama-3.3-70b-versatile",
        "name": "Groq LLaMA 3.3 70B",
        "provider": "groq",
        "owned_by": "groq",
        "description": "Ultra-low latency LPU-accelerated LLaMA 3.3 70B on Groq Cloud",
        "supports_tools": True,
        "is_local": False
    },

    # DeepSeek Cloud
    {
        "id": "deepseek/deepseek-chat",
        "name": "DeepSeek V3 Chat",
        "provider": "deepseek",
        "owned_by": "deepseek",
        "description": "DeepSeek V3 official cloud API with high reasoning power",
        "supports_tools": True,
        "is_local": False
    },
    {
        "id": "deepseek/deepseek-reasoner",
        "name": "DeepSeek R1 Reasoner",
        "provider": "deepseek",
        "owned_by": "deepseek",
        "description": "DeepSeek R1 official cloud reasoning model",
        "supports_tools": False,
        "is_local": False
    },

    # Mistral AI Cloud
    {
        "id": "mistral/mistral-large-latest",
        "name": "Mistral Large",
        "provider": "mistral",
        "owned_by": "mistral",
        "description": "Top-tier flagship model from Mistral AI Cloud",
        "supports_tools": True,
        "is_local": False
    }
]


def resolve_model_name(model_str: Optional[str], default_model: str) -> str:
    """
    Intelligently resolves any model name string into a LiteLLM-compatible provider/model route.
    
    Rules:
    1. Empty/None -> default_model
    2. Explicit provider prefix with '/' (e.g. 'openai/gpt-4o', 'anthropic/claude-3-5-sonnet',
       'gemini/gemini-2.0-flash', 'groq/llama-3.3-70b', 'ollama/llama3.2') -> preserved directly.
    3. Common non-prefixed models:
       - 'gpt-*', 'o1*', 'o3*', 'chatgpt-*', 'text-embedding-*' -> 'openai/<model>'
       - 'claude-*' -> 'anthropic/<model>'
       - 'gemini-*' -> 'gemini/<model>'
       - 'deepseek-*' -> 'deepseek/<model>'
       - 'mistral-large*', 'mistral-small*', 'codestral*', 'pixtral*' -> 'mistral/<model>'
    4. Fallback without prefix (e.g. 'qwen2.5-coder:7b', 'llama3.2', 'gemma2:2b') -> 'ollama/<model>'
    """
    if not model_str or not model_str.strip():
        return default_model

    model = model_str.strip()

    # If it already contains a slash, keep it intact (e.g. "openai/gpt-4o", "anthropic/claude-3", "ollama/llama3")
    if "/" in model:
        return model

    lower_model = model.lower()

    # OpenAI shorthand patterns
    if re.match(r"^(gpt-3\.5|gpt-4|o1|o3|chatgpt|text-embedding)", lower_model):
        return f"openai/{model}"

    # Anthropic shorthand patterns
    if lower_model.startswith("claude-"):
        return f"anthropic/{model}"

    # Google Gemini shorthand patterns
    if lower_model.startswith("gemini-"):
        return f"gemini/{model}"

    # DeepSeek cloud shorthand patterns
    if lower_model.startswith("deepseek-chat") or lower_model.startswith("deepseek-reasoner") or lower_model.startswith("deepseek-v3"):
        return f"deepseek/{model}"

    # Mistral cloud shorthand patterns
    if lower_model.startswith("mistral-large") or lower_model.startswith("mistral-small") or lower_model.startswith("codestral") or lower_model.startswith("pixtral"):
        return f"mistral/{model}"

    # Default to Ollama for local open-weight model shorthands
    return f"ollama/{model}"


def build_litellm_kwargs(
    target_model: str,
    messages: List[Dict[str, Any]],
    config: GatewayConfig,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
    stream: Optional[bool] = False,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Constructs the exact keyword arguments for LiteLLM based on model type and provider.
    Ensures local Ollama endpoints are isolated and cloud providers use correct keys/endpoints.
    """
    kwargs: Dict[str, Any] = {
        "model": target_model,
        "messages": messages,
    }

    if temperature is not None:
        kwargs["temperature"] = temperature
    if top_p is not None:
        kwargs["top_p"] = top_p
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if tools:
        kwargs["tools"] = tools
    if tool_choice:
        kwargs["tool_choice"] = tool_choice
    if stream:
        kwargs["stream"] = stream

    # Resolve provider-specific API base and API key
    is_ollama = target_model.startswith("ollama/") or target_model.startswith("ollama_chat/")

    if is_ollama:
        resolved_base = api_base or config.ollama_api_base
        if (os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER")) and ("localhost:11434" in resolved_base or "127.0.0.1:11434" in resolved_base):
            resolved_base = resolved_base.replace("localhost:11434", "host.docker.internal:11434").replace("127.0.0.1:11434", "host.docker.internal:11434")
        kwargs["api_base"] = resolved_base
        # Stop sequences for small local models to avoid hallucinated user turns
        kwargs["stop"] = ["### User:", "### User\n", "### Human:", "\n\nUser:", "\n\nHuman:"]
    else:
        # Non-Ollama models (OpenAI, Anthropic, Gemini, Groq, Mistral, DeepSeek, Azure, etc.)
        resolved_api_key = api_key
        resolved_api_base = api_base

        if target_model.startswith("openai/"):
            resolved_api_key = resolved_api_key or config.openai_api_key
            resolved_api_base = resolved_api_base or config.openai_api_base
        elif target_model.startswith("anthropic/"):
            resolved_api_key = resolved_api_key or config.anthropic_api_key
            resolved_api_base = resolved_api_base or config.anthropic_api_base
        elif target_model.startswith("gemini/"):
            resolved_api_key = resolved_api_key or config.gemini_api_key
        elif target_model.startswith("groq/"):
            resolved_api_key = resolved_api_key or config.groq_api_key
        elif target_model.startswith("mistral/"):
            resolved_api_key = resolved_api_key or config.mistral_api_key
        elif target_model.startswith("deepseek/"):
            resolved_api_key = resolved_api_key or config.deepseek_api_key
        elif target_model.startswith("openrouter/"):
            resolved_api_key = resolved_api_key or config.openrouter_api_key

        if resolved_api_key:
            kwargs["api_key"] = resolved_api_key
        if resolved_api_base:
            kwargs["api_base"] = resolved_api_base

    return kwargs


def get_available_models(config: GatewayConfig) -> List[Dict[str, Any]]:
    """
    Returns a unified list of models available in the gateway, combining the catalog
    with dynamically queried local Ollama models (if Ollama is running).
    """
    models_by_id: Dict[str, Dict[str, Any]] = {m["id"]: dict(m) for m in CATALOG_MODELS}

    # Dynamically check local Ollama for any pulled models
    ollama_base = config.ollama_api_base
    if (os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER")) and ("localhost:11434" in ollama_base or "127.0.0.1:11434" in ollama_base):
        ollama_base = ollama_base.replace("localhost:11434", "host.docker.internal:11434").replace("127.0.0.1:11434", "host.docker.internal:11434")

    try:
        req = urllib.request.Request(
            f"{ollama_base.rstrip('/')}/api/tags",
            headers={"User-Agent": "LLM-Gateway"}
        )
        with urllib.request.urlopen(req, timeout=1.0) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                for item in data.get("models", []):
                    tag_name = item.get("name")
                    if tag_name:
                        model_id = f"ollama/{tag_name}"
                        if model_id not in models_by_id:
                            models_by_id[model_id] = {
                                "id": model_id,
                                "name": tag_name,
                                "provider": "ollama",
                                "owned_by": "ollama",
                                "description": f"Locally installed Ollama model ({item.get('details', {}).get('parameter_size', 'local')})",
                                "supports_tools": True,
                                "is_local": True
                            }
    except Exception:
        # If Ollama is offline, catalog models are still returned
        pass

    return list(models_by_id.values())
