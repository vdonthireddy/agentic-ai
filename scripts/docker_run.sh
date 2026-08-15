#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

echo "🐳 Building and starting Agentic AI containers..."
docker compose up --build -d llm-gateway

echo ""
echo "🚀 LiteLLM Gateway & Dashboard running at: http://localhost:8000/"
echo ""
echo "To run the automated E2E demo in Docker:"
echo "   docker compose run --rm agent-client"
echo ""
echo "To launch interactive Agent CLI inside Docker:"
echo "   docker compose run --rm agent-client python agent-client/cli.py"
echo ""
echo "To run evaluation benchmarks inside Docker:"
echo "   docker compose --profile evals run --rm evals-framework"
echo ""
echo "To view live Gateway logs:"
echo "   docker compose logs -f llm-gateway"
