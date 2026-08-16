#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Activate venv if present
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

export PYTHONPATH="$DIR/llm_gateway:$DIR:$PYTHONPATH"
echo "🚀 Starting LLM Gateway with arguments: $@ ..."
python -m llm_gateway "$@"
