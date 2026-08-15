#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

echo "🐳 Building and starting Agentic AI Unified Studio..."
docker compose up --build -d

echo ""
echo "=========================================================================="
echo "✨ Agentic AI Unified Studio is UP and RUNNING at: http://localhost:8000/"
echo "=========================================================================="
echo "Features available in the single Web UI:"
echo "  💬 1. AI Agent Chatbot (Turn-by-turn chat with ReAct tool calling & skills)"
echo "  📊 2. Telemetry Observatory (Real-time token & latency metrics)"
echo "  📜 3. Audit Logs Explorer (Searchable prompts & interaction modal)"
echo "  🧪 4. Evals & Benchmarks Runner (4-Grader evaluation scorecard)"
echo ""
echo "To view live logs: docker compose logs -f"
echo "To stop:           docker compose down"
echo ""
