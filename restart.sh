#!/usr/bin/env bash
# ==============================================================================
# Agentic AI: Complete System Restarter & URL Dashboard
# ==============================================================================
# Usage:
#   ./restart.sh           -> Restart in Unified Production Mode (FastAPI + React UI on port 8000)
#   ./restart.sh --dev     -> Restart in Dev Mode (FastAPI on 8000 + Vite HMR on 5173)
#   ./restart.sh --rebuild -> Recompile React WebUI bundle before restarting
#   ./restart.sh stop      -> Stop all running Agentic AI background services
#   ./restart.sh --docker  -> Restart services inside Docker containers
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
NC='\033[0m' # No Color
BOLD='\033[1m'

GATEWAY_PORT=8000
VITE_PORT=5173
PID_FILE="$SCRIPT_DIR/gateway.pid"
VITE_PID_FILE="$SCRIPT_DIR/webui.pid"
LOG_FILE="$SCRIPT_DIR/gateway.log"
VITE_LOG_FILE="$SCRIPT_DIR/webui_dev.log"

# ------------------------------------------------------------------------------
# Action: Stop Services
# ------------------------------------------------------------------------------
stop_services() {
    echo -e "${YELLOW}🛑 Stopping active Agentic AI services...${NC}"
    
    # 1. Stop Gateway via PID file
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE" 2>/dev/null || true)
        if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
            kill "$PID" 2>/dev/null || true
            sleep 1
            kill -9 "$PID" 2>/dev/null || true
        fi
        rm -f "$PID_FILE"
    fi

    # 2. Stop Vite Dev Server via PID file
    if [ -f "$VITE_PID_FILE" ]; then
        V_PID=$(cat "$VITE_PID_FILE" 2>/dev/null || true)
        if [ -n "$V_PID" ] && kill -0 "$V_PID" 2>/dev/null; then
            kill "$V_PID" 2>/dev/null || true
            sleep 1
            kill -9 "$V_PID" 2>/dev/null || true
        fi
        rm -f "$VITE_PID_FILE"
    fi

    # 3. Kill any lingering process on port 8000
    PORT_8000_PIDS=$(lsof -ti:$GATEWAY_PORT 2>/dev/null || true)
    if [ -n "$PORT_8000_PIDS" ]; then
        echo -e "${YELLOW}  Killing process(es) on port $GATEWAY_PORT: $PORT_8000_PIDS...${NC}"
        kill -9 $PORT_8000_PIDS 2>/dev/null || true
    fi

    # 4. Kill any lingering process on port 5173
    PORT_5173_PIDS=$(lsof -ti:$VITE_PORT 2>/dev/null || true)
    if [ -n "$PORT_5173_PIDS" ]; then
        echo -e "${YELLOW}  Killing process(es) on port $VITE_PORT: $PORT_5173_PIDS...${NC}"
        kill -9 $PORT_5173_PIDS 2>/dev/null || true
    fi

    echo -e "${GREEN}✓ All services stopped.${NC}"
}

if [ "$1" = "stop" ]; then
    stop_services
    exit 0
fi

# ------------------------------------------------------------------------------
# Action: Docker Mode
# ------------------------------------------------------------------------------
if [ "$1" = "--docker" ]; then
    echo -e "${CYAN}${BOLD}"
    echo "================================================================="
    echo "       🐳 AGENTIC AI: DOCKER CONTAINER RESTART & DEPLOY          "
    echo "================================================================="
    echo -e "${NC}"

    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}❌ Error: Docker daemon is not running or accessible.${NC}"
        echo "Please start Docker Desktop or run './restart.sh' for native local mode."
        exit 1
    fi

    stop_services
    echo -e "\n${YELLOW}🛑 Stopping Docker containers...${NC}"
    docker compose down --remove-orphans || true

    echo -e "\n${YELLOW}🔨 Building & starting Docker services...${NC}"
    docker compose up -d --build

    echo -e "\n${YELLOW}⏳ Waiting for Docker health check...${NC}"
    MAX_RETRIES=30
    RETRY_COUNT=0
    HEALTHY=false
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        RETRY_COUNT=$((RETRY_COUNT+1))
        if curl -s -f "http://localhost:$GATEWAY_PORT/health" > /dev/null 2>&1; then
            HEALTHY=true
            break
        fi
        echo -n "."
        sleep 2
    done
    echo ""

    if [ "$HEALTHY" = true ]; then
        echo -e "\n${GREEN}${BOLD}🎉 Docker deployment is ONLINE and HEALTHY!${NC}\n"
    else
        echo -e "\n${RED}❌ Warning: Gateway health check timed out. Showing logs:${NC}\n"
        docker compose logs --tail=40
        exit 1
    fi
else
    # ------------------------------------------------------------------------------
    # Action: Native Local Mode
    # ------------------------------------------------------------------------------
    echo -e "${CYAN}${BOLD}"
    echo "================================================================="
    echo "         ⚡ AGENTIC AI: LOCAL SYSTEM RESTART & LAUNCH            "
    echo "================================================================="
    echo -e "${NC}"

    # Stop existing instances first
    stop_services

    # 1. Check Python Environment
    echo -e "\n${YELLOW}🔍 Step 1: Verifying Python Environment...${NC}"
    PYTHON_BIN=""
    if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
        PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
    elif command -v python3 > /dev/null 2>&1; then
        PYTHON_BIN=$(command -v python3)
    else
        echo -e "${RED}❌ Python 3 was not found! Please create a virtualenv in .venv/${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Using Python interpreter: $($PYTHON_BIN --version) ($PYTHON_BIN)${NC}"

    # 2. Check Environment & Persistent Storage
    echo -e "\n${YELLOW}📁 Step 2: Preparing Environment & Storage...${NC}"
    if [ ! -f ".env" ] && [ -f ".env.example" ]; then
        echo -e "${YELLOW}ℹ️  Creating .env from .env.example...${NC}"
        cp .env.example .env
    fi
    touch llm_gateway.db gateway_audit.jsonl
    mkdir -p workspace
    echo -e "${GREEN}✓ Environment & SQLite storage mounts verified.${NC}"

    # 3. Check React WebUI Build
    DEV_MODE=false
    if [ "$1" = "--dev" ] || [ "$2" = "--dev" ]; then
        DEV_MODE=true
    fi

    REBUILD=false
    if [ "$1" = "--rebuild" ] || [ "$2" = "--rebuild" ]; then
        REBUILD=true
    fi

    if [ "$DEV_MODE" = false ]; then
        echo -e "\n${YELLOW}📦 Step 3: Checking React WebUI Studio Bundle...${NC}"
        if [ ! -f "webui/dist/index.html" ] || [ "$REBUILD" = true ]; then
            echo -e "${YELLOW}ℹ️  Compiling production React bundle (npm run build)...${NC}"
            (cd webui && npm run build)
            echo -e "${GREEN}✓ React bundle compiled successfully.${NC}"
        else
            echo -e "${GREEN}✓ Pre-built React Studio bundle detected (webui/dist/index.html).${NC}"
            echo -e "  ${BLUE}Tip: Run './restart.sh --rebuild' to force a fresh WebUI compilation.${NC}"
        fi
    fi

    # 4. Start LLM Gateway
    echo -e "\n${YELLOW}🚀 Step 4: Starting Unified LLM Gateway...${NC}"
    export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
    nohup "$PYTHON_BIN" "$SCRIPT_DIR/llm_gateway/main.py" > "$LOG_FILE" 2>&1 &
    GATEWAY_PID=$!
    echo "$GATEWAY_PID" > "$PID_FILE"
    echo -e "${GREEN}✓ LLM Gateway launched (PID: $GATEWAY_PID, Log: $LOG_FILE).${NC}"

    # Optional: Start Vite Dev Server if --dev passed
    if [ "$DEV_MODE" = true ]; then
        echo -e "\n${YELLOW}⚡ Starting Vite React Dev Server (--dev)...${NC}"
        (cd webui && nohup npm run dev > "$VITE_LOG_FILE" 2>&1 & echo $! > "$VITE_PID_FILE")
        VITE_PID=$(cat "$VITE_PID_FILE" 2>/dev/null || true)
        echo -e "${GREEN}✓ Vite Dev Server launched (PID: $VITE_PID, Log: $VITE_LOG_FILE).${NC}"
    fi

    # 5. Wait for Gateway Health
    echo -e "\n${YELLOW}⏳ Step 5: Waiting for Gateway to report healthy...${NC}"
    MAX_RETRIES=25
    RETRY_COUNT=0
    HEALTHY=false

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        RETRY_COUNT=$((RETRY_COUNT+1))
        if curl -s -f "http://localhost:$GATEWAY_PORT/health" > /dev/null 2>&1; then
            HEALTHY=true
            break
        fi
        echo -n "."
        sleep 1
    done
    echo ""

    if [ "$HEALTHY" = false ]; then
        echo -e "${RED}❌ Error: Gateway failed to start or timed out on port $GATEWAY_PORT.${NC}"
        echo -e "Showing last 30 lines of $LOG_FILE:\n"
        tail -n 30 "$LOG_FILE"
        exit 1
    fi
fi

# ------------------------------------------------------------------------------
# Display Endpoints & URLs Dashboard
# ------------------------------------------------------------------------------
echo -e "\n${GREEN}${BOLD}═════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}   🎉 ALL AGENTIC AI SERVICES ARE UP, HEALTHY & READY!          ${NC}"
echo -e "${GREEN}${BOLD}═════════════════════════════════════════════════════════════════${NC}\n"

echo -e "${CYAN}${BOLD}🖥️  STUDIO WEB INTERFACES:${NC}"
if [ "$DEV_MODE" = true ]; then
    echo -e "  • ${BOLD}React Dev Studio (Vite HMR):${NC}    ${GREEN}${BOLD}http://localhost:$VITE_PORT/${NC}"
    echo -e "  • ${BOLD}FastAPI Unified Studio:${NC}         ${GREEN}http://localhost:$GATEWAY_PORT/${NC}"
else
    echo -e "  • ${BOLD}Unified Web Studio (11 Tabs):${NC}   ${GREEN}${BOLD}http://localhost:$GATEWAY_PORT/${NC}"
fi

echo -e "\n${CYAN}${BOLD}📚 INTERACTIVE API DOCUMENTATION:${NC}"
echo -e "  • ${BOLD}Swagger UI (OpenAPI):${NC}           ${BLUE}http://localhost:$GATEWAY_PORT/docs${NC}"
echo -e "  • ${BOLD}ReDoc Interactive Docs:${NC}         ${BLUE}http://localhost:$GATEWAY_PORT/redoc${NC}"

echo -e "\n${CYAN}${BOLD}🔌 CORE GATEWAY & SWARM API ENDPOINTS:${NC}"
echo -e "  • ${BOLD}System Health Check:${NC}            ${YELLOW}http://localhost:$GATEWAY_PORT/health${NC}"
echo -e "  • ${BOLD}Models Catalog (/v1):${NC}           ${YELLOW}http://localhost:$GATEWAY_PORT/v1/models${NC}"
echo -e "  • ${BOLD}3-Tier Interaction Logs:${NC}        ${YELLOW}http://localhost:$GATEWAY_PORT/v1/logs${NC}"
echo -e "  • ${BOLD}Cost & Budget Telemetry:${NC}        ${YELLOW}http://localhost:$GATEWAY_PORT/api/costs${NC}"
echo -e "  • ${BOLD}Rate Limiter Status:${NC}            ${YELLOW}http://localhost:$GATEWAY_PORT/api/rate-limit/status${NC}"
echo -e "  • ${BOLD}Human-in-the-Loop (HITL):${NC}       ${YELLOW}http://localhost:$GATEWAY_PORT/api/hitl/pending${NC}"

echo -e "\n${CYAN}${BOLD}💾 PHASE 3 DURABLE STATE MACHINE ENDPOINTS:${NC}"
echo -e "  • ${BOLD}List Workflow Runs:${NC}             ${PURPLE}http://localhost:$GATEWAY_PORT/api/canvas/runs${NC}"
echo -e "  • ${BOLD}Run Details & Checkpoints:${NC}      ${PURPLE}http://localhost:$GATEWAY_PORT/api/canvas/runs/{run_id}${NC}"
echo -e "  • ${BOLD}Execute Visual DAG:${NC}             ${PURPLE}POST http://localhost:$GATEWAY_PORT/api/canvas/execute${NC}"
echo -e "  • ${BOLD}Resume Interrupted Run:${NC}         ${PURPLE}POST http://localhost:$GATEWAY_PORT/api/canvas/resume/{run_id}${NC}"

echo -e "\n${CYAN}${BOLD}🛠️  HELPFUL MANAGEMENT COMMANDS:${NC}"
echo -e "  • Tail live server logs:           ${BOLD}tail -f $LOG_FILE${NC}"
if [ "$DEV_MODE" = true ]; then
    echo -e "  • Tail Vite dev server logs:       ${BOLD}tail -f $VITE_LOG_FILE${NC}"
fi
echo -e "  • Stop all background services:    ${BOLD}./restart.sh stop${NC}"
echo -e "  • Restart with Vite live reload:   ${BOLD}./restart.sh --dev${NC}"
echo -e "  • Rebuild React UI bundle:         ${BOLD}./restart.sh --rebuild${NC}"
echo -e "  • Run full automated test suite:   ${BOLD}.venv/bin/pytest${NC}\n"
echo -e "${GREEN}Enjoy building autonomous agentic AI workflows! 🚀${NC}\n"
