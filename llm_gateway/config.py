"""Parameterized configuration management for LLM Gateway."""

import os
from pathlib import Path
from typing import Optional, Union
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Default .env location
DEFAULT_ENV_PATH = Path(__file__).parent.parent / ".env"
if DEFAULT_ENV_PATH.exists():
    load_dotenv(dotenv_path=DEFAULT_ENV_PATH, override=False)
else:
    load_dotenv(override=False)


class GatewayConfig(BaseModel):
    """Configuration class for LLM Gateway supporting full runtime parameterization."""
    
    # Ollama settings
    ollama_api_base: str = Field(default_factory=lambda: os.environ.get("OLLAMA_API_BASE", "http://localhost:11434"))
    default_model: str = Field(default_factory=lambda: os.environ.get("DEFAULT_MODEL", "ollama/gemma2:2b"))
    fallback_model: str = Field(default_factory=lambda: os.environ.get("FALLBACK_MODEL", "ollama/llama3.2"))
    
    # Server & Transport settings ("http" or "stdio")
    transport: str = Field(default_factory=lambda: os.environ.get("GATEWAY_TRANSPORT", "http").lower())
    host: str = Field(default_factory=lambda: os.environ.get("GATEWAY_HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: int(os.environ.get("GATEWAY_PORT", "8000")))
    
    # Storage settings
    db_path: Path = Field(default_factory=lambda: Path(os.environ.get("LLM_GATEWAY_DB_PATH", "./llm_gateway.db")).resolve())
    json_log_path: Path = Field(default_factory=lambda: Path(os.environ.get("LLM_GATEWAY_JSON_LOG", "./gateway_audit.jsonl")).resolve())

    def with_overrides(
        self,
        transport: Optional[str] = None,
        default_model: Optional[str] = None,
        fallback_model: Optional[str] = None,
        ollama_api_base: Optional[str] = None,
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
        host=host if host is not None else base.host,
        port=port if port is not None else base.port,
        db_path=Path(db_path).resolve() if db_path is not None else base.db_path,
        json_log_path=Path(json_log_path).resolve() if json_log_path is not None else base.json_log_path
    )


# Global default configuration instance
config = GatewayConfig()
