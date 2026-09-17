#!/usr/bin/env bash
# ==============================================================================
# 🎭 Agentic-AI: Master Demo Launcher
# ==============================================================================
# Usage:
#   ./demo.sh          -> Interactive Demo Menu (Web UI, Swarm, E2E, Evals, CLI)
#   ./demo.sh --web    -> Boot Gateway & Open Web Studio UI at http://localhost:8000
#   ./demo.sh --agent  -> Run Automated ReAct Agent Demo (Math, Weather, Shopping, Files)
#   ./demo.sh --e2e    -> Run 18-Feature Playwright Browser Verification Suite
#   ./demo.sh --evals  -> Run 9-Grader Benchmark Evaluation Suite
#   ./demo.sh --cli    -> Launch Interactive Rich Terminal Agent CLI
#   ./demo.sh --all    -> Full-Spectrum Demo: Boot Gateway + Agent Demo + Web UI
#   ./demo.sh --story  -> Display the Story Summary from story.md
#   ./demo.sh --help   -> Show help and usage options
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Formatting Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

GATEWAY_URL="http://localhost:8000"

# Activate Python virtual environment if present
if [ -d "$SCRIPT_DIR/.venv" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

export PYTHONPATH="$SCRIPT_DIR:$SCRIPT_DIR/ai_agent:$SCRIPT_DIR/mcp_server:$PYTHONPATH"
export DEFAULT_MODEL="${DEFAULT_MODEL:-ollama/qwen2.5-coder:7b}"

# ------------------------------------------------------------------------------
# Banner
# ------------------------------------------------------------------------------
print_banner() {
    echo -e "${CYAN}${BOLD}"
    echo "=========================================================================="
    echo "  🧠 AGENTIC-AI : UNIFIED ENTERPRISE DEMO RUNNER"
    echo "  503 Features · 8 Modules · 13 Studio Tabs · 23 MCP Tools · 10 Skills"
    echo "=========================================================================="
    echo -e "${NC}"
}

# ------------------------------------------------------------------------------
# Check & Ensure Gateway is Online
# ------------------------------------------------------------------------------
ensure_gateway() {
    echo -e "${BLUE}🔍 Checking LiteLLM Gateway & Web Studio at ${GATEWAY_URL}/health...${NC}"
    if curl -s -f "${GATEWAY_URL}/health" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Gateway is already running and healthy at ${GATEWAY_URL}${NC}"
        return 0
    fi

    echo -e "${YELLOW}⚡ Gateway is not running. Starting background services via ./restart.sh...${NC}"
    "$SCRIPT_DIR/restart.sh" >/dev/null 2>&1 || true

    echo -ne "${BLUE}⏳ Waiting for Gateway to initialize"
    for i in {1..25}; do
        if curl -s -f "${GATEWAY_URL}/health" >/dev/null 2>&1; then
            echo -e "\n${GREEN}✓ Gateway successfully initialized and online!${NC}"
            return 0
        fi
        echo -ne "."
        sleep 1
    done

    echo -e "\n${RED}✗ Timed out waiting for Gateway at ${GATEWAY_URL}.${NC}"
    echo -e "${YELLOW}Check gateway.log for details.${NC}"
    return 1
}

# ------------------------------------------------------------------------------
# Open Browser Utility
# ------------------------------------------------------------------------------
open_browser() {
    local url="${1:-$GATEWAY_URL}"
    echo -e "${GREEN}🌐 Opening Web Studio in your browser: ${url}${NC}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open "$url"
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$url"
    else
        echo -e "${YELLOW}Please open ${url} in your web browser.${NC}"
    fi
}

# ------------------------------------------------------------------------------
# Sub-Actions
# ------------------------------------------------------------------------------
run_web() {
    ensure_gateway
    open_browser "$GATEWAY_URL"
    echo -e "\n${CYAN}🌟 Web Studio is live! Access all 13 Studio Tabs:${NC}"
    echo -e "  • Chatbot Studio:      ${GATEWAY_URL}/chat"
    echo -e "  • Workflow Canvas DAG: ${GATEWAY_URL}/canvas"
    echo -e "  • Orchestrator Swarm:  ${GATEWAY_URL}/orchestrator"
    echo -e "  • 23 FastMCP Tools:    ${GATEWAY_URL}/tools"
    echo -e "  • 10 Domain Skills:    ${GATEWAY_URL}/skills"
    echo -e "  • Memory Explorer:     ${GATEWAY_URL}/memory"
    echo -e "  • Smart Router:        ${GATEWAY_URL}/smart-router"
    echo -e "  • 9-Grader Evals:      ${GATEWAY_URL}/evals"
    echo -e "  • Safety Approvals:    ${GATEWAY_URL}/approvals"
    echo -e "  • Audit Logs & Telemetry: ${GATEWAY_URL}/logs\n"
}

run_agent_demo() {
    ensure_gateway
    echo -e "\n${PURPLE}${BOLD}🤖 Executing Automated Agentic AI Demo Suite...${NC}\n"
    python "$SCRIPT_DIR/ai_agent/demo.py"
}

run_e2e() {
    ensure_gateway
    echo -e "\n${BLUE}${BOLD}🧪 Executing 18-Feature Playwright E2E Verification Suite...${NC}\n"
    node "$SCRIPT_DIR/scripts/verify_all_docs_workflows.mjs"
}

run_evals() {
    echo -e "\n${YELLOW}${BOLD}📊 Running 9-Grader Evaluation Benchmark Suite...${NC}\n"
    python "$SCRIPT_DIR/evals_framework/runner.py" \
        --model "ollama/qwen2.5-coder:7b" \
        --dataset "tool_calling_evals.json"
}

run_cli() {
    ensure_gateway
    echo -e "\n${CYAN}${BOLD}💻 Launching Interactive Rich Terminal Agent CLI...${NC}\n"
    python -m ai_agent.cli
}

run_story_summary() {
    echo -e "\n${PURPLE}${BOLD}📜 Story Summary: The Grand Demo Odyssey${NC}\n"
    if [ -f "$SCRIPT_DIR/story.md" ]; then
        head -n 46 "$SCRIPT_DIR/story.md"
        echo -e "\n${CYAN}👉 Read the complete 1,400+ line walkthrough in: ${SCRIPT_DIR}/story.md${NC}\n"
    else
        echo -e "${RED}story.md not found in repository root.${NC}"
    fi
}

run_all() {
    ensure_gateway
    echo -e "\n${GREEN}${BOLD}🚀 Running Full-Spectrum Enterprise Demo...${NC}\n"
    echo -e "${BLUE}Step 1: Running Automated Agentic ReAct Suite...${NC}"
    python "$SCRIPT_DIR/ai_agent/demo.py"
    
    echo -e "\n${BLUE}Step 2: Launching Unified Web Studio UI...${NC}"
    open_browser "$GATEWAY_URL"
    
    echo -e "\n${GREEN}✨ Full-Spectrum Demo successfully executed!${NC}"
}

# ------------------------------------------------------------------------------
# Interactive Menu
# ------------------------------------------------------------------------------
interactive_menu() {
    print_banner
    echo -e "Please select an option to demonstrate:"
    echo -e "  ${BOLD}1)${NC} 🌐 ${GREEN}Launch Web Studio UI${NC} & Open Browser (${GATEWAY_URL})"
    echo -e "  ${BOLD}2)${NC} 🤖 ${PURPLE}Run Automated Agent Demo${NC} (ReAct loop, Math, Weather, Shopping, Files)"
    echo -e "  ${BOLD}3)${NC} 🧪 ${BLUE}Run 18-Feature Playwright E2E Suite${NC} (Headless browser verification)"
    echo -e "  ${BOLD}4)${NC} 📊 ${YELLOW}Run 9-Grader Evals Suite${NC} (Quality & compliance benchmark)"
    echo -e "  ${BOLD}5)${NC} 💻 ${CYAN}Launch Interactive Terminal CLI${NC} (Rich CLI chat & /skills)"
    echo -e "  ${BOLD}6)${NC} 🌟 ${BOLD}Full-Spectrum Demo${NC} (Boot Gateway + Agent Demo + Open Web UI)"
    echo -e "  ${BOLD}7)${NC} 📜 ${BOLD}View Demo Story (story.md)${NC}"
    echo -e "  ${BOLD}q)${NC} Quit\n"
    
    read -rp "Enter choice [1-7 or q]: " choice
    case "$choice" in
        1) run_web ;;
        2) run_agent_demo ;;
        3) run_e2e ;;
        4) run_evals ;;
        5) run_cli ;;
        6) run_all ;;
        7) run_story_summary ;;
        q|Q) echo -e "${CYAN}Exiting demo runner. Goodbye!${NC}"; exit 0 ;;
        *) echo -e "${RED}Invalid choice: $choice${NC}"; exit 1 ;;
    esac
}

# ------------------------------------------------------------------------------
# Dispatcher
# ------------------------------------------------------------------------------
case "${1:-}" in
    --web|-w)
        print_banner
        run_web
        ;;
    --agent|--auto|-a)
        print_banner
        run_agent_demo
        ;;
    --e2e|-e)
        print_banner
        run_e2e
        ;;
    --evals)
        print_banner
        run_evals
        ;;
    --cli|-c)
        print_banner
        run_cli
        ;;
    --all)
        print_banner
        run_all
        ;;
    --story|-s)
        print_banner
        run_story_summary
        ;;
    --help|-h)
        print_banner
        echo "Usage: ./demo.sh [OPTION]"
        echo ""
        echo "Options:"
        echo "  (no args)    Open the interactive demo menu"
        echo "  --web, -w    Boot Gateway and open Web Studio UI at http://localhost:8000"
        echo "  --agent, -a  Run automated ReAct Agent suite (Math, Weather, Shopping, Files)"
        echo "  --e2e, -e    Run 18-Feature Playwright browser verification suite"
        echo "  --evals      Run 9-grader benchmark evaluation suite"
        echo "  --cli, -c    Launch interactive terminal CLI"
        echo "  --all        Full-spectrum demo: boot gateway, run agent suite, open web UI"
        echo "  --story, -s  Display summary from story.md"
        echo "  --help, -h   Show this help message"
        ;;
    "")
        if [ -t 0 ]; then
            interactive_menu
        else
            # Non-interactive fallback: execute full demo
            print_banner
            run_all
        fi
        ;;
    *)
        echo -e "${RED}Unknown option: $1${NC}"
        echo "Run ./demo.sh --help for available options."
        exit 1
        ;;
esac
