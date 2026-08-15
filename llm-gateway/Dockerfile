FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LLM_GATEWAY_HOST=0.0.0.0 \
    LLM_GATEWAY_PORT=8000 \
    LLM_GATEWAY_DB_PATH=/app/data/llm_gateway.db \
    LLM_GATEWAY_JSON_LOG_PATH=/app/data/gateway_audit.jsonl

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install all workspace dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project modules for unified runtime
COPY mcp-server/ /app/mcp-server/
COPY agent-client/ /app/agent-client/
COPY evals-framework/ /app/evals-framework/
COPY llm-gateway/ /app/llm-gateway/

RUN mkdir -p /app/data /app/workspace /app/evals-framework/reports

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "llm-gateway/app.py"]
