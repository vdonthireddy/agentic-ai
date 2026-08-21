# ==============================================================================
# Stage 1: Build React WebUI Frontend
# ==============================================================================
FROM node:22-alpine AS webui-builder
WORKDIR /app/webui

COPY webui/package.json ./
RUN npm install

COPY webui/ ./
RUN npm run build

# ==============================================================================
# Stage 2: Python 3.12 Production Runtime
# ==============================================================================
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies and curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications
COPY llm_gateway/requirements.txt /app/llm_gateway_req.txt
COPY mcp_server/requirements.txt /app/mcp_server_req.txt
COPY ai_agent/requirements.txt /app/ai_agent_req.txt
COPY evals_framework/requirements.txt /app/evals_framework_req.txt

# Install all Python dependencies
RUN pip install --no-cache-dir -r /app/llm_gateway_req.txt \
    && pip install --no-cache-dir -r /app/mcp_server_req.txt \
    && pip install --no-cache-dir -r /app/ai_agent_req.txt \
    && pip install --no-cache-dir -r /app/evals_framework_req.txt

# Copy application source directories
COPY llm_gateway /app/llm_gateway
COPY mcp_server /app/mcp_server
COPY ai_agent /app/ai_agent
COPY evals_framework /app/evals_framework
COPY workspace /app/workspace
COPY scripts /app/scripts

# Copy compiled React WebUI bundle from builder stage
COPY --from=webui-builder /app/webui/dist /app/webui/dist

# Configure environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8000
ENV DOCKER_CONTAINER=1
ENV OLLAMA_API_BASE=http://host.docker.internal:11434

EXPOSE 8000

# Container Healthcheck
HEALTHCHECK --interval=15s --timeout=10s --start-period=30s --retries=5 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start the Gateway and React Studio
CMD ["python", "llm_gateway/main.py"]
