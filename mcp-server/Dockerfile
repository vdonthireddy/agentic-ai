FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MCP_TRANSPORT=stdio

RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    && rm -rf /var/lib/apt/lists/*

COPY mcp-server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp-server/ /app/mcp-server/
RUN mkdir -p /app/workspace

CMD ["python", "mcp-server/server.py"]
