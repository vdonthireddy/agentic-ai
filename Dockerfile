# ==============================================================================
# Stage 1: Build React WebUI Frontend
# ==============================================================================
FROM node:22-alpine AS webui-builder
WORKDIR /app/webui

COPY webui/package*.json ./
RUN npm ci

COPY webui/ ./
RUN npm run build

# ==============================================================================
# Stage 2: Python Build Environment
# ==============================================================================
FROM python:3.12-slim AS python-builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential

COPY requirements.lock /app/
# Use a virtual environment to copy over easily
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.lock

# ==============================================================================
# Stage 3: Production Runtime (Hardened)
# ==============================================================================
FROM python:3.12-slim

# Create a non-root user
RUN groupadd -g 1001 appuser && useradd -u 1001 -g appuser -s /bin/bash -m appuser

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from python-builder
COPY --from=python-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source directories with correct ownership
COPY --chown=appuser:appuser llm_gateway /app/llm_gateway
COPY --chown=appuser:appuser mcp_server /app/mcp_server
COPY --chown=appuser:appuser ai_agent /app/ai_agent
COPY --chown=appuser:appuser evals_framework /app/evals_framework
COPY --chown=appuser:appuser workspace /app/workspace
COPY --chown=appuser:appuser scripts /app/scripts

# Copy compiled React WebUI bundle from builder stage
COPY --from=webui-builder --chown=appuser:appuser /app/webui/dist /app/webui/dist

# Configure environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8000
ENV DOCKER_CONTAINER=1
ENV OLLAMA_API_BASE=http://host.docker.internal:11434

# Switch to non-root user
USER appuser

EXPOSE 8000

# Container Healthcheck
HEALTHCHECK --interval=15s --timeout=10s --start-period=30s --retries=5 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start the Gateway and React Studio
CMD ["python", "llm_gateway/app.py"]
