#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"
cd "$DIR"

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

export PYTHONPATH="$DIR/evals-framework:$DIR/agent-client:$DIR/mcp-server:$PYTHONPATH"

MODEL="${1:-ollama/qwen2.5-coder:7b}"
echo "Running LLM & Agent Evaluation Framework for: $MODEL"
python "$DIR/evals-framework/runner.py" --model "$MODEL"
