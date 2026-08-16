#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"
cd "$DIR"

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

export PYTHONPATH="$DIR:$DIR/evals_framework:$DIR/ai_agent:$DIR/mcp_server:$PYTHONPATH"

MODEL="${1:-ollama/gemma2:2b}"
echo "🧪 Starting LLM Evaluation Framework Benchmark Suite..."
python "$DIR/evals_framework/runner.py" --model "$MODEL"
