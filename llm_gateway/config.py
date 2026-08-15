"""Configuration management for LLM Gateway."""

import os
from pathlib import Path
from pydantic import BaseModel

class GatewayConfig(BaseModel):
    # Ollama settings
    ollama_api_base: str = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")
    default_model: str = os.environ.get("DEFAULT_MODEL", "ollama/qwen2.5-coder:7b")
    fallback_model: str = os.environ.get("FALLBACK_MODEL", "ollama/llama3.2")
    
    # Server settings
    host: str = os.environ.get("GATEWAY_HOST", "0.0.0.0")
    port: int = int(os.environ.get("GATEWAY_PORT", "8000"))
    
    # Storage settings
    db_path: Path = Path(os.environ.get("LLM_GATEWAY_DB_PATH", "./llm_gateway.db")).resolve()
    json_log_path: Path = Path(os.environ.get("LLM_GATEWAY_JSON_LOG", "./gateway_audit.jsonl")).resolve()

config = GatewayConfig()
