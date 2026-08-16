"""Entrypoint script for starting LLM Gateway with Uvicorn."""

import os
import uvicorn
from llm_gateway.config import config

if __name__ == "__main__":
    host = os.environ.get("HOST", config.host)
    port = int(os.environ.get("PORT", config.port))
    uvicorn.run("llm_gateway.app:app", host=host, port=port, reload=False)
