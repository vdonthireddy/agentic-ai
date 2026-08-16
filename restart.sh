#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo "🔄 Restarting Agentic AI Studio container..."

# Simply restart the container
docker compose restart || docker restart agentic_ai_studio

# Quick health check
echo "⏳ Checking health..."
for i in {1..10}; do
    if curl -s -f "http://localhost:8000/health" >/dev/null 2>&1; then
        echo "✨ Container is healthy and ready at: http://localhost:8000/"
        exit 0
    fi
    sleep 1
done

echo "⚠️ Container restarted. Status:"
docker ps --filter "name=agentic_ai_studio"
