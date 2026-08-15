#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Activate venv if present
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

export PYTHONPATH="$DIR:$DIR/ai_agent:$DIR/mcp_server:$PYTHONPATH"
echo "🤖 Starting Interactive Agent CLI (Model: ${MODEL:-ollama/qwen2.5-coder:7b})..."
python "$DIR/ai_agent/cli.py"
