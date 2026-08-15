FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LLM_GATEWAY_URL=http://llm-gateway:8000 \
    DEFAULT_MODEL=ollama/qwen2.5-coder:7b

RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    && rm -rf /var/lib/apt/lists/*

COPY mcp-server/requirements.txt /app/mcp_requirements.txt
COPY agent-client/requirements.txt /app/agent_requirements.txt

RUN pip install --no-cache-dir -r mcp_requirements.txt -r agent_requirements.txt

COPY mcp-server/ /app/mcp-server/
COPY agent-client/ /app/agent-client/
RUN mkdir -p /app/workspace

CMD ["python", "agent-client/demo.py"]
