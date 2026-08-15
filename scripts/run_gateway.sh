#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Activate venv if present
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

export PYTHONPATH="$DIR/llm-gateway:$PYTHONPATH"
echo "Starting LiteLLM Gateway on http://localhost:8000 (Ollama: ${OLLAMA_API_BASE:-http://localhost:11434})..."
python "$DIR/llm-gateway/app.py"
