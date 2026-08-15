"""FastAPI LLM Gateway powered by LiteLLM with comprehensive audit logging."""

import os
import sys
import time
import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, Request, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import litellm

# Ensure local imports work
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from models import ChatCompletionRequest, LogQueryFilter
from logger import audit_logger, logger
from db import query_logs, get_stats

app = FastAPI(
    title="LiteLLM Gateway with Audit Logging",
    description="Intelligent LLM Gateway with Ollama routing, tool-calling support, and full audit logging of prompts, token usage, caller context, and tools/skills.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static dashboard assets
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.on_event("startup")
async def startup_event():
    logger.info(f"LLM Gateway started. Default model: {config.default_model}, Ollama Base: {config.ollama_api_base}")
    logger.info(f"Audit SQLite DB: {config.db_path}")
    logger.info(f"Audit JSONL log: {config.json_log_path}")

@app.get("/")
@app.get("/dashboard")
async def serve_dashboard():
    """Serve the real-time LLM Gateway & Audit Observatory Dashboard UI."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "LLM Gateway is online. Dashboard static files not found."}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "llm-gateway",
        "default_model": config.default_model,
        "ollama_api_base": config.ollama_api_base
    }

@app.get("/v1/models")
@app.get("/models")
async def list_models():
    """List available local Ollama models and default route."""
    return {
        "object": "list",
        "data": [
            {"id": "ollama/qwen2.5-coder:7b", "object": "model", "owned_by": "ollama"},
            {"id": "ollama/llama3.2", "object": "model", "owned_by": "ollama"},
            {"id": "ollama/mistral:latest", "object": "model", "owned_by": "ollama"},
            {"id": "ollama/gemma2:2b", "object": "model", "owned_by": "ollama"}
        ],
        "default_model": config.default_model
    }

@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    raw_req: Request,
    x_caller_id: Optional[str] = Header(None),
    x_agent_name: Optional[str] = Header(None),
    x_session_id: Optional[str] = Header(None),
    x_caller_context: Optional[str] = Header(None),
    x_skill_names: Optional[str] = Header(None),
    x_tool_names: Optional[str] = Header(None),
):
    """
    OpenAI-compatible Chat Completions proxy endpoint.
    Routes to local Ollama via LiteLLM and logs prompts, token usage, caller context, and tools/skills.
    """
    start_time = time.time()
    
    # 1. Resolve Caller Context and Identity
    caller_id = request.caller_id or x_caller_id or raw_req.client.host if raw_req.client else "unknown_caller"
    agent_name = request.agent_name or x_agent_name or "Agentic-AI-Client"
    session_id = request.session_id or x_session_id or f"session_{uuid.uuid4().hex[:8]}"
    
    caller_context_data = request.caller_context or {}
    if not caller_context_data and x_caller_context:
        try:
            caller_context_data = json.loads(x_caller_context)
        except Exception:
            caller_context_data = {"raw": x_caller_context}

    # 2. Resolve Skills and Tools
    skill_names = list(request.skill_names or [])
    if x_skill_names:
        for s in x_skill_names.split(","):
            s = s.strip()
            if s and s not in skill_names:
                skill_names.append(s)

    tool_names = []
    if request.tools:
        for t in request.tools:
            if isinstance(t, dict):
                fn = t.get("function", {})
                name = fn.get("name") if isinstance(fn, dict) else t.get("name")
                if name:
                    tool_names.append(name)
    if x_tool_names:
        for t in x_tool_names.split(","):
            t = t.strip()
            if t and t not in tool_names:
                tool_names.append(t)

    # 3. Resolve Target Model
    target_model = request.model or config.default_model
    if not target_model.startswith("ollama/") and not target_model.startswith("openai/"):
        target_model = f"ollama/{target_model}"

    # Prepare messages payload
    messages_payload = [m.model_dump(exclude_none=True) for m in request.messages]
    
    # Request parameters
    req_params = {
        "temperature": request.temperature,
        "top_p": request.top_p,
        "max_tokens": request.max_tokens,
        "stream": request.stream
    }

    # 4. Invoke LiteLLM
    try:
        litellm_kwargs = {
            "model": target_model,
            "messages": messages_payload,
            "api_base": config.ollama_api_base,
            "temperature": request.temperature
        }
        if request.tools:
            litellm_kwargs["tools"] = request.tools
        if request.tool_choice:
            litellm_kwargs["tool_choice"] = request.tool_choice
        if request.max_tokens:
            litellm_kwargs["max_tokens"] = request.max_tokens

        response = await litellm.acompletion(**litellm_kwargs)
        latency_ms = (time.time() - start_time) * 1000

        # Extract response message details
        choice = response.choices[0]
        msg = choice.message
        resp_content = getattr(msg, "content", None)
        
        # Extract tool calls if any
        resp_tool_calls = []
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                if hasattr(tc, "model_dump"):
                    resp_tool_calls.append(tc.model_dump())
                elif isinstance(tc, dict):
                    resp_tool_calls.append(tc)
                else:
                    resp_tool_calls.append({
                        "id": getattr(tc, "id", str(uuid.uuid4())),
                        "type": getattr(tc, "type", "function"),
                        "function": {
                            "name": getattr(getattr(tc, "function", None), "name", ""),
                            "arguments": getattr(getattr(tc, "function", None), "arguments", "{}")
                        }
                    })

        # Token usage
        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens) if usage else 0

        # 5. Log call in Audit System
        audit_record = audit_logger.log_call(
            caller_id=caller_id,
            agent_name=agent_name,
            session_id=session_id,
            caller_context=caller_context_data,
            model=target_model,
            skill_names=skill_names,
            tool_names=tool_names,
            request_messages=messages_payload,
            request_tools=request.tools,
            request_params=req_params,
            response_content=resp_content,
            response_tool_calls=resp_tool_calls,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            status="SUCCESS"
        )

        # 6. Format standard OpenAI-like response dictionary
        response_dict = response.model_dump() if hasattr(response, "model_dump") else dict(response)
        # Attach gateway audit metadata in the response headers/json
        response_dict["gateway_metadata"] = {
            "call_id": audit_record["id"],
            "logged": True,
            "latency_ms": audit_record["latency_ms"],
            "session_id": session_id,
            "agent_name": agent_name
        }
        return JSONResponse(content=response_dict)

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        err_msg = str(e)
        logger.error(f"Error invoking LLM {target_model}: {err_msg}")

        # Log failed interaction
        audit_logger.log_call(
            caller_id=caller_id,
            agent_name=agent_name,
            session_id=session_id,
            caller_context=caller_context_data,
            model=target_model,
            skill_names=skill_names,
            tool_names=tool_names,
            request_messages=messages_payload,
            request_tools=request.tools,
            request_params=req_params,
            response_content=None,
            response_tool_calls=[],
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            latency_ms=latency_ms,
            status="ERROR",
            error_message=err_msg
        )

        raise HTTPException(status_code=500, detail={"error": "LLM Gateway Execution Error", "message": err_msg})

@app.get("/v1/logs")
@app.get("/logs")
async def get_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    model: Optional[str] = None
):
    """Retrieve audit logs stored in the SQLite database."""
    logs = query_logs(
        limit=limit,
        offset=offset,
        session_id=session_id,
        agent_name=agent_name,
        model=model,
        db_path=config.db_path
    )
    return {
        "count": len(logs),
        "limit": limit,
        "offset": offset,
        "logs": logs
    }

@app.get("/v1/stats")
@app.get("/stats")
async def get_statistics():
    """Retrieve summary metrics and token consumption statistics."""
    stats = get_stats(db_path=config.db_path)
    return stats

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.host, port=config.port)
