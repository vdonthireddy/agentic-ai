#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Activate venv if present
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

export PYTHONPATH="$DIR/agent-client:$DIR/mcp-server:$PYTHONPATH"
echo "Running End-to-End Automated Demo..."
python "$DIR/agent-client/demo.py"
