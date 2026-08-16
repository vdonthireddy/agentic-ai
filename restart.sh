#!/usr/bin/env bash
# ==============================================================================
# Agentic AI: Docker Service Restarter & Health Verifier
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo -e "${CYAN}${BOLD}"
echo "================================================================="
echo "       ⚡ AGENTIC AI: FULL-STACK DOCKER RESTART & DEPLOY         "
echo "================================================================="
echo -e "${NC}"

# 1. Check Docker daemon
echo -e "${YELLOW}🔍 Step 1: Checking Docker Daemon...${NC}"
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker daemon is not running or accessible.${NC}"
    echo "Please start Docker Desktop and run this script again."
    exit 1
fi
echo -e "${GREEN}✓ Docker is running.${NC}"

# 2. Check for .env file and persistent storage
echo -e "\n${YELLOW}📄 Step 2: Checking Environment & Persistent Storage...${NC}"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}ℹ️  No .env file found. Creating from .env.example...${NC}"
        cp .env.example .env
        echo -e "${GREEN}✓ Created .env file.${NC}"
    fi
else
    echo -e "${GREEN}✓ Existing .env file detected.${NC}"
fi

# Ensure persistent database files exist
touch llm_gateway.db gateway_audit.jsonl
mkdir -p workspace
echo -e "${GREEN}✓ Persistent storage mounts initialized.${NC}"

# 3. Stop and clean existing containers
echo -e "\n${YELLOW}🛑 Step 3: Stopping & Removing Existing Containers...${NC}"
docker compose down --remove-orphans || true
echo -e "${GREEN}✓ Containers cleaned.${NC}"

# 4. Build and start containers
echo -e "\n${YELLOW}🔨 Step 4: Building & Launching Docker Services...${NC}"
docker compose up -d --build

# 5. Wait for Health Check
echo -e "\n${YELLOW}⏳ Step 5: Waiting for Agentic AI Studio to become healthy...${NC}"
MAX_RETRIES=30
RETRY_COUNT=0
HEALTHY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    RETRY_COUNT=$((RETRY_COUNT+1))
    if curl -s -f "http://localhost:8000/health" > /dev/null 2>&1; then
        HEALTHY=true
        break
    fi
    echo -n "."
    sleep 2
done
echo ""

if [ "$HEALTHY" = true ]; then
    echo -e "${GREEN}${BOLD}🎉 SUCCESS: All Docker services are UP and HEALTHY!${NC}\n"
    echo -e "${CYAN}=================================================================${NC}"
    echo -e "${BOLD}🌐 Web Studio & React UI:${NC}   ${GREEN}http://localhost:8000/${NC}"
    echo -e "${BOLD}🩺 Gateway Health Endpoint:${NC} ${GREEN}http://localhost:8000/health${NC}"
    echo -e "${BOLD}🤖 Models Catalog Endpoint:${NC} ${GREEN}http://localhost:8000/v1/models${NC}"
    echo -e "${BOLD}📜 Audit Logs Endpoint:${NC}     ${GREEN}http://localhost:8000/v1/logs${NC}"
    echo -e "${CYAN}=================================================================${NC}"
    echo -e "\n${BOLD}Helpful Commands:${NC}"
    echo -e "  • View live streaming logs:   ${CYAN}docker compose logs -f${NC}"
    echo -e "  • Stop all containers:        ${CYAN}docker compose down${NC}"
    echo -e "  • Restart containers:         ${CYAN}./restart.sh${NC}\n"
else
    echo -e "${RED}❌ Warning: Gateway health check timed out on http://localhost:8000/health.${NC}"
    echo -e "Showing recent container logs:\n"
    docker compose logs --tail=40
    exit 1
fi
