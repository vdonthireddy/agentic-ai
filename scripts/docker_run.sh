#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker daemon is not running or accessible."
    echo "Please start Docker Desktop and try again."
    exit 1
fi

# Detect docker compose v2 vs legacy docker-compose v1
if docker compose version > /dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose > /dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    echo "❌ Error: Neither 'docker compose' nor 'docker-compose' was found."
    exit 1
fi

# Ensure directories and files exist so Docker volume mounts never create directories for files
mkdir -p workspace memory_store
if [ -d "llm_gateway.db" ]; then rm -rf "llm_gateway.db"; fi
if [ -d "gateway_audit.jsonl" ]; then rm -rf "gateway_audit.jsonl"; fi
touch llm_gateway.db gateway_audit.jsonl
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
fi

echo "🐳 Building and starting Agentic AI Unified Studio..."
$DOCKER_COMPOSE_CMD up --build -d

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
echo "To view live logs: $DOCKER_COMPOSE_CMD logs -f"
echo "To stop:           $DOCKER_COMPOSE_CMD down"
echo ""
