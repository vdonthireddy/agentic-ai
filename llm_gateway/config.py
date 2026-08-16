"""Parameterized configuration management for LLM Gateway supporting local and cloud models."""

import os
from pathlib import Path
from typing import Optional, Union, Dict, List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Default .env location
DEFAULT_ENV_PATH = Path(__file__).parent.parent / ".env"
if DEFAULT_ENV_PATH.exists():
    load_dotenv(dotenv_path=DEFAULT_ENV_PATH, override=False)
else:
    load_dotenv(override=False)


def _resolve_default_ollama_base() -> str:
    base = os.environ.get("OLLAMA_API_BASE")
    if not base:
        if os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER"):
            return "http://host.docker.internal:11434"
        return "http://localhost:11434"
    if (os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER")) and ("localhost:11434" in base or "127.0.0.1:11434" in base):
        return base.replace("localhost:11434", "host.docker.internal:11434").replace("127.0.0.1:11434", "host.docker.internal:11434")
    return base


class GatewayConfig(BaseModel):
    """Configuration class for LLM Gateway supporting local & cloud providers and full runtime parameterization."""
    
    # Ollama settings
    ollama_api_base: str = Field(default_factory=_resolve_default_ollama_base)
    default_model: str = Field(default_factory=lambda: os.environ.get("DEFAULT_MODEL", "ollama/gemma2:2b"))
    fallback_model: str = Field(default_factory=lambda: os.environ.get("FALLBACK_MODEL", "ollama/gemma2:2b"))
    
    # Cloud Provider API Keys (optional; litellm also reads from os.environ directly)
    openai_api_key: Optional[str] = Field(default_factory=lambda: os.environ.get("OPENAI_API_KEY"))
    anthropic_api_key: Optional[str] = Field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY"))
    gemini_api_key: Optional[str] = Field(default_factory=lambda: os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    groq_api_key: Optional[str] = Field(default_factory=lambda: os.environ.get("GROQ_API_KEY"))
    mistral_api_key: Optional[str] = Field(default_factory=lambda: os.environ.get("MISTRAL_API_KEY"))
    openrouter_api_key: Optional[str] = Field(default_factory=lambda: os.environ.get("OPENROUTER_API_KEY"))
    deepseek_api_key: Optional[str] = Field(default_factory=lambda: os.environ.get("DEEPSEEK_API_KEY"))
    
    # Custom API Base endpoints for cloud/custom models (e.g. OpenAI compatible proxies, Azure, vLLM)
    openai_api_base: Optional[str] = Field(default_factory=lambda: os.environ.get("OPENAI_API_BASE"))
    anthropic_api_base: Optional[str] = Field(default_factory=lambda: os.environ.get("ANTHROPIC_API_BASE"))
    
    # Server & Transport settings ("http" or "stdio")
    transport: str = Field(default_factory=lambda: os.environ.get("GATEWAY_TRANSPORT", "http").lower())
    host: str = Field(default_factory=lambda: os.environ.get("GATEWAY_HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: int(os.environ.get("GATEWAY_PORT", "8000")))
    
    # Storage settings
    db_path: Path = Field(default_factory=lambda: Path(os.environ.get("LLM_GATEWAY_DB_PATH", "./llm_gateway.db")).resolve())
    json_log_path: Path = Field(default_factory=lambda: Path(os.environ.get("LLM_GATEWAY_JSON_LOG", "./gateway_audit.jsonl")).resolve())

    def get_configured_providers(self) -> List[str]:
        """Return list of providers that have credentials or active configurations detected."""
        providers = ["ollama"]  # Ollama is always supported
        if self.openai_api_key or os.environ.get("OPENAI_API_KEY"):
            providers.append("openai")
        if self.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY"):
            providers.append("anthropic")
        if self.gemini_api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
            providers.append("gemini")
        if self.groq_api_key or os.environ.get("GROQ_API_KEY"):
            providers.append("groq")
        if self.mistral_api_key or os.environ.get("MISTRAL_API_KEY"):
            providers.append("mistral")
        if self.openrouter_api_key or os.environ.get("OPENROUTER_API_KEY"):
            providers.append("openrouter")
        if self.deepseek_api_key or os.environ.get("DEEPSEEK_API_KEY"):
            providers.append("deepseek")
        return providers

    def with_overrides(
        self,
        transport: Optional[str] = None,
        default_model: Optional[str] = None,
        fallback_model: Optional[str] = None,
        ollama_api_base: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        groq_api_key: Optional[str] = None,
        mistral_api_key: Optional[str] = None,
        openrouter_api_key: Optional[str] = None,
        deepseek_api_key: Optional[str] = None,
        openai_api_base: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db_path: Optional[Union[str, Path]] = None,
        json_log_path: Optional[Union[str, Path]] = None
    ) -> "GatewayConfig":
        """Returns a new GatewayConfig instance with specific parameter overrides."""
        return GatewayConfig(
            transport=transport.lower() if transport is not None else self.transport,
            default_model=default_model if default_model is not None else self.default_model,
            fallback_model=fallback_model if fallback_model is not None else self.fallback_model,
            ollama_api_base=ollama_api_base if ollama_api_base is not None else self.ollama_api_base,
            openai_api_key=openai_api_key if openai_api_key is not None else self.openai_api_key,
            anthropic_api_key=anthropic_api_key if anthropic_api_key is not None else self.anthropic_api_key,
            gemini_api_key=gemini_api_key if gemini_api_key is not None else self.gemini_api_key,
            groq_api_key=groq_api_key if groq_api_key is not None else self.groq_api_key,
            mistral_api_key=mistral_api_key if mistral_api_key is not None else self.mistral_api_key,
            openrouter_api_key=openrouter_api_key if openrouter_api_key is not None else self.openrouter_api_key,
            deepseek_api_key=deepseek_api_key if deepseek_api_key is not None else self.deepseek_api_key,
            openai_api_base=openai_api_base if openai_api_base is not None else self.openai_api_base,
            host=host if host is not None else self.host,
            port=port if port is not None else self.port,
            db_path=Path(db_path).resolve() if db_path is not None else self.db_path,
            json_log_path=Path(json_log_path).resolve() if json_log_path is not None else self.json_log_path
        )


def get_config(
    transport: Optional[str] = None,
    default_model: Optional[str] = None,
    fallback_model: Optional[str] = None,
    ollama_api_base: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    anthropic_api_key: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
    groq_api_key: Optional[str] = None,
    mistral_api_key: Optional[str] = None,
    openrouter_api_key: Optional[str] = None,
    deepseek_api_key: Optional[str] = None,
    openai_api_base: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    db_path: Optional[Union[str, Path]] = None,
    json_log_path: Optional[Union[str, Path]] = None,
    env_file: Optional[Union[str, Path]] = None
) -> GatewayConfig:
    """
    Factory to retrieve a parameterized GatewayConfig instance.
    Loads custom env_file if provided and applies explicit keyword parameter overrides.
    """
    if env_file:
        p = Path(env_file).resolve()
        if p.exists():
            load_dotenv(dotenv_path=p, override=True)

    base = GatewayConfig()
    return GatewayConfig(
        transport=transport.lower() if transport is not None else base.transport,
        default_model=default_model if default_model is not None else base.default_model,
        fallback_model=fallback_model if fallback_model is not None else base.fallback_model,
        ollama_api_base=ollama_api_base if ollama_api_base is not None else base.ollama_api_base,
        openai_api_key=openai_api_key if openai_api_key is not None else base.openai_api_key,
        anthropic_api_key=anthropic_api_key if anthropic_api_key is not None else base.anthropic_api_key,
        gemini_api_key=gemini_api_key if gemini_api_key is not None else base.gemini_api_key,
        groq_api_key=groq_api_key if groq_api_key is not None else base.groq_api_key,
        mistral_api_key=mistral_api_key if mistral_api_key is not None else base.mistral_api_key,
        openrouter_api_key=openrouter_api_key if openrouter_api_key is not None else base.openrouter_api_key,
        deepseek_api_key=deepseek_api_key if deepseek_api_key is not None else base.deepseek_api_key,
        openai_api_base=openai_api_base if openai_api_base is not None else base.openai_api_base,
        host=host if host is not None else base.host,
        port=port if port is not None else base.port,
        db_path=Path(db_path).resolve() if db_path is not None else base.db_path,
        json_log_path=Path(json_log_path).resolve() if json_log_path is not None else base.json_log_path
    )


# Global default configuration instance
config = GatewayConfig()
