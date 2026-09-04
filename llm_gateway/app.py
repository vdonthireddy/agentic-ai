"""
FastAPI LLM Gateway powered by LiteLLM with comprehensive audit logging.
Acts as a decoupled, multi-provider proxy server and mounts modular routers for
Agents, MCP Tools & Skills, Evals, and Voice.
"""

import os
import sys
import time
import json
import uuid
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional, TYPE_CHECKING

from fastapi import FastAPI, Request, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import litellm  # type: ignore[import-not-found,import-untyped]

# Ensure local and package imports work
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

if TYPE_CHECKING:
    from llm_gateway.config import config
    from llm_gateway.models import ChatCompletionRequest
    from llm_gateway.logger import audit_logger, logger
    from llm_gateway.db import query_logs, query_hierarchical_logs, get_stats, init_db, save_gateway_setting, get_gateway_settings
    from llm_gateway.router import resolve_model_name, build_litellm_kwargs, get_available_models
    from llm_gateway.rate_limiter import rate_limiter
    from llm_gateway.cost_tracker import cost_tracker
    from llm_gateway.voice_endpoints import router as voice_router
else:
    try:
        from llm_gateway.config import config
        from llm_gateway.models import ChatCompletionRequest
        from llm_gateway.logger import audit_logger, logger
        from llm_gateway.db import query_logs, query_hierarchical_logs, get_stats, init_db, save_gateway_setting, get_gateway_settings
        from llm_gateway.router import resolve_model_name, build_litellm_kwargs, get_available_models
        from llm_gateway.rate_limiter import rate_limiter
        from llm_gateway.cost_tracker import cost_tracker
        from llm_gateway.voice_endpoints import router as voice_router
    except (ImportError, ValueError):
        from config import config  # type: ignore[import-not-found]
        from models import ChatCompletionRequest  # type: ignore[import-not-found]
        from logger import audit_logger, logger  # type: ignore[import-not-found]
        from db import query_logs, query_hierarchical_logs, get_stats, init_db, save_gateway_setting, get_gateway_settings  # type: ignore[import-not-found]
        from router import resolve_model_name, build_litellm_kwargs, get_available_models  # type: ignore[import-not-found]
        from rate_limiter import rate_limiter  # type: ignore[import-not-found]
        from cost_tracker import cost_tracker  # type: ignore[import-not-found]
        from voice_endpoints import router as voice_router  # type: ignore[import-not-found]


# Initialize and restore persisted settings on module load
try:
    init_db(config.db_path)
    _persisted = get_gateway_settings(config.db_path)
    if _persisted.get("default_model"):
        config.default_model = _persisted["default_model"]
    if _persisted.get("fallback_model"):
        config.fallback_model = _persisted["fallback_model"]
    if _persisted.get("ollama_api_base"):
        config.ollama_api_base = _persisted["ollama_api_base"]
except Exception:
    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern FastAPI lifespan handler for startup and shutdown logging."""
    try:
        init_db(config.db_path)
        persisted = get_gateway_settings(config.db_path)
        if persisted.get("default_model"):
            config.default_model = persisted["default_model"]
        if persisted.get("fallback_model"):
            config.fallback_model = persisted["fallback_model"]
        if persisted.get("ollama_api_base"):
            config.ollama_api_base = persisted["ollama_api_base"]
    except Exception:
        pass
    logger.info(f"LLM Gateway started. Default model: {config.default_model}, Ollama Base: {config.ollama_api_base}")
    logger.info(f"Configured Providers: {config.get_configured_providers()}")
    logger.info(f"Audit SQLite DB: {config.db_path}")
    logger.info(f"Audit JSONL log: {config.json_log_path}")
    yield


app = FastAPI(
    title="LiteLLM Multi-Provider Gateway with Audit Logging",
    description="Intelligent Multi-Provider LLM Gateway with Ollama and Cloud routing, rate-limiting, cost tracking, and decoupled agent/tool/eval routers.",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------------------
# Decoupled Subsystem Router Inclusions
# ------------------------------------------------------------------------------

app.include_router(voice_router)

try:
    from mcp_server.router import router as mcp_router
    app.include_router(mcp_router)
    logger.info("Loaded MCP Tools & Memory router.")
except ImportError as e:
    logger.warning(f"MCP server router not loaded: {e}")

try:
    from ai_agent.router import router as agent_router
    app.include_router(agent_router)
    logger.info("Loaded AI Agent & Swarm router.")
except ImportError as e:
    logger.warning(f"AI agent router not loaded: {e}")

try:
    from evals_framework.router import router as evals_router
    app.include_router(evals_router)
    logger.info("Loaded Evals Framework router.")
except ImportError as e:
    logger.warning(f"Evals framework router not loaded: {e}")


# ------------------------------------------------------------------------------
# Static & WebUI Asset Mounts
# ------------------------------------------------------------------------------

webui_dist_dir = Path(__file__).parent.parent / "webui" / "dist"
static_dir = Path(__file__).parent / "static"

if (webui_dist_dir / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(webui_dist_dir / "assets")), name="webui_assets")

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
@app.get("/dashboard")
@app.get("/chat")
@app.get("/canvas")
@app.get("/orchestrator")
@app.get("/memory")
@app.get("/debate")
@app.get("/tools")
@app.get("/skills")
@app.get("/workspace")
@app.get("/overview")
@app.get("/telemetry")
@app.get("/logs")
@app.get("/evals")
@app.get("/settings")
async def serve_dashboard():
    """Serve the real-time LLM Gateway & React WebUI Studio Dashboard."""
    if (webui_dist_dir / "index.html").exists():
        return FileResponse(str(webui_dist_dir / "index.html"))
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "LLM Gateway is online. Dashboard static files not found."}


@app.get("/favicon.ico")
@app.get("/favicon.svg")
async def get_favicon():
    """Serve the application SVG/ICO favicon."""
    for candidate in [
        webui_dist_dir / "favicon.svg",
        static_dir / "favicon.svg",
        static_dir / "favicon.ico",
        Path(__file__).parent.parent / "webui" / "public" / "favicon.svg",
    ]:
        if candidate.exists():
            return FileResponse(str(candidate), media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Favicon not found")


# ------------------------------------------------------------------------------
# Core Gateway Proxy Endpoints
# ------------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "llm-gateway",
        "default_model": config.default_model,
        "fallback_model": config.fallback_model,
        "ollama_api_base": config.ollama_api_base,
        "configured_providers": config.get_configured_providers(),
        "supported_providers": [
            "ollama", "openai", "anthropic", "gemini",
            "groq", "mistral", "deepseek", "openrouter", "azure", "bedrock"
        ]
    }


@app.get("/v1/models")
@app.get("/models")
async def list_models():
    """List available local Ollama models and configured cloud models."""
    models = get_available_models(config)
    return {
        "object": "list",
        "data": models,
        "default_model": config.default_model,
        "configured_providers": config.get_configured_providers()
    }


@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    raw_req: Request,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
    x_api_base: Optional[str] = Header(None),
    x_caller_id: Optional[str] = Header(None),
    x_agent_name: Optional[str] = Header(None),
    x_session_id: Optional[str] = Header(None),
    x_conversation_id: Optional[str] = Header(None),
    x_turn_id: Optional[str] = Header(None),
    x_request_id: Optional[str] = Header(None),
    x_caller_context: Optional[str] = Header(None),
    x_skill_names: Optional[str] = Header(None),
    x_tool_names: Optional[str] = Header(None),
):
    """
    OpenAI-compatible Chat Completions proxy endpoint.
    Routes to local Ollama or Cloud Providers via LiteLLM.
    Logs prompts, token usage, caller context, and tools/skills to SQLite and JSONL audit logs.
    """
    start_time = time.time()

    caller_id = request.caller_id or x_caller_id or (raw_req.client.host if raw_req.client else "unknown_caller")
    agent_name = request.agent_name or x_agent_name or "Agentic-AI-Client"

    caller_context_data = request.caller_context or {}
    if not caller_context_data and x_caller_context:
        try:
            caller_context_data = json.loads(x_caller_context)
        except Exception:
            caller_context_data = {"raw": x_caller_context}

    conv_id = (
        request.conversation_id or
        request.session_id or
        x_conversation_id or
        x_session_id or
        (caller_context_data.get("conversation_id") if caller_context_data else None) or
        f"conv_{uuid.uuid4().hex[:8]}"
    )
    turn_id = (
        request.turn_id or
        x_turn_id or
        (caller_context_data.get("turn_id") if caller_context_data else None)
    )
    req_id = (
        request.request_id or
        x_request_id or
        (caller_context_data.get("request_id") if caller_context_data else None) or
        f"req_{uuid.uuid4().hex[:12]}"
    )

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

    target_model = resolve_model_name(request.model, config.default_model)

    api_key = request.api_key or x_api_key
    if not api_key and authorization and authorization.startswith("Bearer "):
        bearer_token = authorization.replace("Bearer ", "").strip()
        if bearer_token and bearer_token != "null":
            api_key = bearer_token

    api_base = request.api_base or x_api_base
    messages_payload = [m.model_dump(exclude_none=True) for m in request.messages]

    req_params = {
        "temperature": request.temperature,
        "top_p": request.top_p,
        "max_tokens": request.max_tokens,
        "stream": request.stream
    }

    try:
        litellm_kwargs = build_litellm_kwargs(
            target_model=target_model,
            messages=messages_payload,
            config=config,
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens,
            tools=request.tools,
            tool_choice=request.tool_choice,
            stream=request.stream,
            api_key=api_key,
            api_base=api_base,
        )

        response = await litellm.acompletion(**litellm_kwargs)
        latency_ms = (time.time() - start_time) * 1000

        choice = response.choices[0]
        msg = choice.message
        resp_content = getattr(msg, "content", None)

        resp_tool_calls = []
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                if hasattr(tc, "model_dump"):
                    tc_dict = tc.model_dump()
                elif isinstance(tc, dict):
                    tc_dict = dict(tc)
                else:
                    tc_dict = {
                        "id": getattr(tc, "id", str(uuid.uuid4())),
                        "type": getattr(tc, "type", "function"),
                        "function": {
                            "name": getattr(getattr(tc, "function", None), "name", ""),
                            "arguments": getattr(getattr(tc, "function", None), "arguments", "{}")
                        }
                    }
                if "function" in tc_dict and isinstance(tc_dict["function"], dict):
                    fn_args = tc_dict["function"].get("arguments")
                    if isinstance(fn_args, (dict, list)):
                        tc_dict["function"]["arguments"] = json.dumps(fn_args)
                    elif fn_args is None:
                        tc_dict["function"]["arguments"] = "{}"
                    elif not isinstance(fn_args, str):
                        tc_dict["function"]["arguments"] = str(fn_args)
                resp_tool_calls.append(tc_dict)

        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens) if usage else 0

        audit_record = audit_logger.log_call(
            caller_id=caller_id,
            agent_name=agent_name,
            session_id=conv_id,
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
            status="SUCCESS",
            conversation_id=conv_id,
            turn_id=turn_id,
            request_id=req_id
        )

        response_dict = response.model_dump() if hasattr(response, "model_dump") else dict(response)
        response_dict["gateway_metadata"] = {
            "call_id": audit_record["id"],
            "request_id": audit_record["request_id"],
            "turn_id": audit_record["turn_id"],
            "conversation_id": audit_record["conversation_id"],
            "session_id": audit_record["session_id"],
            "logged": True,
            "latency_ms": audit_record["latency_ms"],
            "agent_name": agent_name
        }
        return JSONResponse(content=response_dict)

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        err_msg = str(e)
        logger.error(f"Error invoking LLM {target_model}: {err_msg}")

        audit_logger.log_call(
            caller_id=caller_id,
            agent_name=agent_name,
            session_id=conv_id,
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
            error_message=err_msg,
            conversation_id=conv_id,
            turn_id=turn_id,
            request_id=req_id
        )
        raise HTTPException(status_code=500, detail={"error": "LLM Gateway Execution Error", "message": err_msg})


@app.get("/v1/logs")
@app.get("/logs")
async def get_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    conversation_id: Optional[str] = None,
    session_id: Optional[str] = None,
    turn_id: Optional[str] = None,
    request_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    model: Optional[str] = None,
    hierarchical: bool = Query(False)
):
    """Retrieve audit logs stored in SQLite (hierarchical tree or flat list)."""
    if hierarchical:
        conv_trees = query_hierarchical_logs(
            conversation_id=conversation_id or session_id,
            limit_conversations=limit,
            db_path=config.db_path
        )
        return {
            "count": len(conv_trees),
            "hierarchical": True,
            "conversations": conv_trees
        }

    logs = query_logs(
        limit=limit,
        offset=offset,
        conversation_id=conversation_id,
        session_id=session_id,
        turn_id=turn_id,
        request_id=request_id,
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


# ------------------------------------------------------------------------------
# System Telemetry & Gateway Config Endpoints
# ------------------------------------------------------------------------------

@app.get("/api/system/metrics")
async def get_system_telemetry():
    """Retrieve host CPU, memory, disk, and platform telemetry."""
    try:
        from mcp_server.tools.system_tools import get_system_metrics
        return get_system_metrics()
    except Exception as e:
        return {"error": str(e), "status": "unavailable"}


class ConfigUpdateRequest(BaseModel):
    default_model: Optional[str] = None
    fallback_model: Optional[str] = None
    ollama_api_base: Optional[str] = None
    transport: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    compaction_token_threshold: Optional[int] = None
    compaction_keep_recent_turns: Optional[int] = None
    hitl_timeout_seconds: Optional[float] = None
    rate_limit_rpm: Optional[int] = None
    rate_limit_tpm: Optional[int] = None
    react_max_iterations: Optional[int] = None
    python_sandbox_timeout_seconds: Optional[float] = None
    debate_max_rounds: Optional[int] = None
    graph_max_depth: Optional[int] = None


@app.get("/api/config")
async def get_gateway_runtime_config():
    """Get active Gateway configuration with masked credentials and runtime hyperparameters."""
    def mask_key(k: Optional[str]) -> str:
        if not k: return "Not Configured"
        if len(k) <= 8: return "****"
        return f"{k[:4]}...{k[-4:]}"

    return {
        "transport": config.transport,
        "host": config.host,
        "port": config.port,
        "default_model": config.default_model,
        "fallback_model": config.fallback_model,
        "ollama_api_base": config.ollama_api_base,
        "db_path": str(config.db_path),
        "json_log_path": str(config.json_log_path),
        "configured_providers": config.get_configured_providers(),
        "provider_keys_status": {
            "openai": mask_key(config.openai_api_key or os.environ.get("OPENAI_API_KEY")),
            "anthropic": mask_key(config.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")),
            "gemini": mask_key(config.gemini_api_key or os.environ.get("GEMINI_API_KEY")),
            "groq": mask_key(config.groq_api_key or os.environ.get("GROQ_API_KEY")),
            "mistral": mask_key(config.mistral_api_key or os.environ.get("MISTRAL_API_KEY")),
            "deepseek": mask_key(config.deepseek_api_key or os.environ.get("DEEPSEEK_API_KEY")),
        },
        "hyperparameters": {
            "compaction_token_threshold": config.compaction_token_threshold,
            "compaction_keep_recent_turns": config.compaction_keep_recent_turns,
            "compaction_auto_prune_message_count": config.compaction_auto_prune_message_count,
            "hitl_timeout_seconds": config.hitl_timeout_seconds,
            "rate_limit_rpm": config.rate_limit_rpm,
            "rate_limit_tpm": config.rate_limit_tpm,
            "react_max_iterations": config.react_max_iterations,
            "python_sandbox_timeout_seconds": config.python_sandbox_timeout_seconds,
            "debate_max_rounds": config.debate_max_rounds,
            "graph_max_depth": config.graph_max_depth
        }
    }


@app.post("/api/config")
async def update_gateway_runtime_config(req: ConfigUpdateRequest):
    """Update runtime Gateway configuration and hyperparameters."""
    if req.default_model:
        config.default_model = req.default_model
        save_gateway_setting("default_model", req.default_model, config.db_path)
    if req.fallback_model:
        config.fallback_model = req.fallback_model
        save_gateway_setting("fallback_model", req.fallback_model, config.db_path)
    if req.ollama_api_base:
        config.ollama_api_base = req.ollama_api_base
        save_gateway_setting("ollama_api_base", req.ollama_api_base, config.db_path)
    if req.transport: config.transport = req.transport.lower()
    if req.openai_api_key:
        config.openai_api_key = req.openai_api_key
        os.environ["OPENAI_API_KEY"] = req.openai_api_key
    if req.anthropic_api_key:
        config.anthropic_api_key = req.anthropic_api_key
        os.environ["ANTHROPIC_API_KEY"] = req.anthropic_api_key
    if req.gemini_api_key:
        config.gemini_api_key = req.gemini_api_key
        os.environ["GEMINI_API_KEY"] = req.gemini_api_key
    if req.groq_api_key:
        config.groq_api_key = req.groq_api_key
        os.environ["GROQ_API_KEY"] = req.groq_api_key
    if req.mistral_api_key:
        config.mistral_api_key = req.mistral_api_key
        os.environ["MISTRAL_API_KEY"] = req.mistral_api_key
    if req.deepseek_api_key:
        config.deepseek_api_key = req.deepseek_api_key
        os.environ["DEEPSEEK_API_KEY"] = req.deepseek_api_key

    if req.compaction_token_threshold is not None:
        config.compaction_token_threshold = req.compaction_token_threshold
    if req.compaction_keep_recent_turns is not None:
        config.compaction_keep_recent_turns = req.compaction_keep_recent_turns
    if req.hitl_timeout_seconds is not None:
        config.hitl_timeout_seconds = req.hitl_timeout_seconds
    if req.rate_limit_rpm is not None:
        config.rate_limit_rpm = req.rate_limit_rpm
    if req.rate_limit_tpm is not None:
        config.rate_limit_tpm = req.rate_limit_tpm
    if req.react_max_iterations is not None:
        config.react_max_iterations = req.react_max_iterations
    if req.python_sandbox_timeout_seconds is not None:
        config.python_sandbox_timeout_seconds = req.python_sandbox_timeout_seconds
    if req.debate_max_rounds is not None:
        config.debate_max_rounds = req.debate_max_rounds
    if req.graph_max_depth is not None:
        config.graph_max_depth = req.graph_max_depth

    return {"success": True, "config": await get_gateway_runtime_config()}


# ------------------------------------------------------------------------------
# Cost Tracking, Rate Limiting & Firewall Endpoints
# ------------------------------------------------------------------------------

@app.get("/api/costs")
async def get_costs():
    """Get aggregate cost breakdown by model and caller."""
    return cost_tracker.get_cost_summary(config.db_path)


@app.get("/api/costs/forecast")
async def get_cost_forecast(days: int = 30):
    """Get projected cost forecast based on recent usage."""
    return cost_tracker.get_cost_forecast(config.db_path, days_ahead=days)


@app.get("/api/costs/pricing")
async def get_pricing_table():
    """Get the current model pricing table."""
    return {"pricing": cost_tracker.get_pricing_table()}


@app.get("/api/rate-limit/status")
async def get_rate_limit_status(caller_id: Optional[str] = None):
    """Get current rate limiter status."""
    return rate_limiter.get_status(caller_id)


class FirewallInspectRequest(BaseModel):
    text: str


@app.post("/api/firewall/inspect")
async def firewall_inspect_api(req: FirewallInspectRequest):
    """Inspect text for prompt injections and preview PII masking."""
    from llm_gateway.firewall import firewall
    safety = firewall.inspect_prompt_safety(req.text)
    redacted_text, redaction_map = firewall.redact_pii(req.text)
    return {
        "safety": safety,
        "original_text": req.text,
        "redacted_text": redacted_text,
        "pii_detected_count": len(redaction_map),
        "redaction_tokens": list(redaction_map.keys())
    }


class CompactRequest(BaseModel):
    messages: List[Dict[str, Any]]
    keep_recent_turns: Optional[int] = 2
    model: Optional[str] = "ollama/gemma2:2b"


@app.post("/api/chat/compact")
async def chat_compact_api(req: CompactRequest):
    """
    Compacts older conversation messages into a structured executive summary,
    retaining active system persona and recent turns to save context tokens.
    """
    from llm_gateway.compact import compact_conversation_history
    result = await compact_conversation_history(
        messages=req.messages,
        keep_recent_turns=req.keep_recent_turns or 2
    )
    return {
        "status": "success",
        **result
    }


# ------------------------------------------------------------------------------
# SPA Catch-All Fallback
# ------------------------------------------------------------------------------

@app.get("/{full_path:path}")
async def serve_spa_fallback(full_path: str):
    """Catch-all route to serve the React SPA for any direct slash URLs."""
    if (
        full_path.startswith("api/")
        or full_path.startswith("v1/")
        or full_path.startswith("docs")
        or full_path.startswith("openapi.json")
        or full_path.startswith("redoc")
        or full_path.startswith("assets/")
        or full_path.startswith("static/")
    ):
        raise HTTPException(status_code=404, detail="Not Found")

    if (webui_dist_dir / "index.html").exists():
        return FileResponse(str(webui_dist_dir / "index.html"))
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    raise HTTPException(status_code=404, detail="Not Found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.host, port=config.port)
