FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LLM_GATEWAY_URL=http://llm-gateway:8000 \
    DEFAULT_MODEL=ollama/gemma2:2b

RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    && rm -rf /var/lib/apt/lists/*

COPY mcp_server/requirements.txt /app/mcp_requirements.txt
COPY ai_agent/requirements.txt /app/agent_requirements.txt

RUN pip install --no-cache-dir -r agent_requirements.txt

COPY mcp_server/ /app/mcp_server/
COPY ai_agent/ /app/ai_agent/
RUN mkdir -p /app/workspace

CMD ["python", "ai_agent/demo.py"]
