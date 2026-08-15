FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LLM_GATEWAY_URL=http://llm-gateway:8000 \
    EVAL_MODEL=ollama/qwen2.5-coder:7b

RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    && rm -rf /var/lib/apt/lists/*

COPY mcp_server/requirements.txt /app/mcp_requirements.txt
COPY ai_agent/requirements.txt /app/agent_requirements.txt
COPY evals_framework/requirements.txt /app/evals_requirements.txt

RUN pip install --no-cache-dir -r mcp_requirements.txt -r agent_requirements.txt -r evals_requirements.txt

COPY mcp_server/ /app/mcp_server/
COPY ai_agent/ /app/ai_agent/
COPY evals_framework/ /app/evals_framework/
RUN mkdir -p /app/workspace /app/evals_framework/reports

CMD ["python", "evals_framework/runner.py", "--model", "ollama/qwen2.5-coder:7b"]
