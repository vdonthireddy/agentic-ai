"""FastAPI LLM Gateway powered by LiteLLM with comprehensive audit logging."""

import os
import sys
import time
import json
import uuid
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, Request, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import litellm  # type: ignore[import-not-found,import-untyped]

# Ensure local and package imports work
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

try:
    from llm_gateway.config import config
    from llm_gateway.models import ChatCompletionRequest, LogQueryFilter, ModelInfo
    from llm_gateway.logger import audit_logger, logger
    from llm_gateway.db import query_logs, query_hierarchical_logs, get_stats
    from llm_gateway.router import resolve_model_name, build_litellm_kwargs, get_available_models
    from llm_gateway.streaming import format_sse_event, format_sse_done, format_sse_keepalive, StreamAccumulator
    from llm_gateway.rate_limiter import rate_limiter
    from llm_gateway.cost_tracker import cost_tracker
    from llm_gateway.voice_endpoints import router as voice_router
except (ImportError, ValueError):
    from config import config  # type: ignore[import-not-found]
    from models import ChatCompletionRequest, LogQueryFilter, ModelInfo  # type: ignore[import-not-found]
    from logger import audit_logger, logger  # type: ignore[import-not-found]
    from db import query_logs, query_hierarchical_logs, get_stats  # type: ignore[import-not-found]
    from router import resolve_model_name, build_litellm_kwargs, get_available_models  # type: ignore[import-not-found]
    from streaming import format_sse_event, format_sse_done, format_sse_keepalive, StreamAccumulator  # type: ignore[import-not-found]
    from rate_limiter import rate_limiter  # type: ignore[import-not-found]
    from cost_tracker import cost_tracker  # type: ignore[import-not-found]
    from voice_endpoints import router as voice_router  # type: ignore[import-not-found]

app = FastAPI(
    title="LiteLLM Multi-Provider Gateway with Audit Logging",
    description="Intelligent Multi-Provider LLM Gateway with Ollama and Cloud routing (OpenAI, Anthropic, Gemini, Groq, Mistral, DeepSeek), tool-calling support, and full audit logging of prompts, token usage, caller context, and tools/skills.",
    version="1.1.0"
)

app.include_router(voice_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static dashboard and React WebUI assets
webui_dist_dir = Path(__file__).parent.parent / "webui" / "dist"
static_dir = Path(__file__).parent / "static"

if (webui_dist_dir / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(webui_dist_dir / "assets")), name="webui_assets")

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.on_event("startup")
async def startup_event():
    logger.info(f"LLM Gateway started. Default model: {config.default_model}, Ollama Base: {config.ollama_api_base}")
    logger.info(f"Configured Providers: {config.get_configured_providers()}")
    logger.info(f"Audit SQLite DB: {config.db_path}")
    logger.info(f"Audit JSONL log: {config.json_log_path}")

@app.get("/")
@app.get("/dashboard")
@app.get("/chat")
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
    Routes to local Ollama or Cloud Providers (OpenAI, Anthropic, Gemini, Groq, DeepSeek, etc.) via LiteLLM.
    Logs prompts, token usage, caller context, and tools/skills to SQLite and JSONL audit logs with Conversation/Turn/Request hierarchy.
    """
    start_time = time.time()
    
    # 1. Resolve Caller Context and Hierarchical Identity
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

    # 3. Resolve Target Model & Credentials
    target_model = resolve_model_name(request.model, config.default_model)

    # Extract API Key from request body, custom header, or Bearer auth header
    api_key = request.api_key or x_api_key
    if not api_key and authorization and authorization.startswith("Bearer "):
        bearer_token = authorization.replace("Bearer ", "").strip()
        if bearer_token and bearer_token != "null":
            api_key = bearer_token

    api_base = request.api_base or x_api_base

    # Prepare messages payload
    messages_payload = [m.model_dump(exclude_none=True) for m in request.messages]
    
    # Request parameters
    req_params = {
        "temperature": request.temperature,
        "top_p": request.top_p,
        "max_tokens": request.max_tokens,
        "stream": request.stream
    }

    # 4. Invoke LiteLLM via Router
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

        # Extract response message details
        choice = response.choices[0]
        msg = choice.message
        resp_content = getattr(msg, "content", None)
        
        # Extract tool calls if any
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

        # Token usage
        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens) if usage else 0

        # 5. Log call in Audit System with 3-tier hierarchy
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

        # 6. Format standard OpenAI-like response dictionary
        response_dict = response.model_dump() if hasattr(response, "model_dump") else dict(response)
        # Attach gateway audit metadata in the response headers/json
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

        # Log failed interaction
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

# ----------------------------------------------------------------------
# Unified UI Endpoints: Chatbot & Evals Framework
# ----------------------------------------------------------------------

# In-memory sessions for interactive chatbot UI
ui_agent_sessions: Dict[str, Any] = {}

class UIChatRequest(BaseModel):
    message: str
    model: Optional[str] = None
    skill_name: Optional[str] = None
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None
    turn_id: Optional[str] = None

@app.post("/api/chat")
async def handle_ui_chat(req: UIChatRequest):
    """Interactive Chatbot endpoint executing MCP Tools & Skills."""
    base_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(base_dir))
    sys.path.insert(0, str(base_dir / "mcp_server"))
    
    from ai_agent import AgenticLLMAgent

    conv_id = req.conversation_id or req.session_id or f"conv_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
    target_model = req.model or config.default_model

    agent = ui_agent_sessions.get(conv_id)
    if agent is None or agent.model != target_model:
        if agent:
            await agent.close()
        agent = AgenticLLMAgent(
            gateway_url=f"http://localhost:{config.port}",
            agent_name="EverydayAssistant",
            caller_id="web_ui_user",
            model=target_model,
            session_id=conv_id
        )
        await agent.initialize()
        ui_agent_sessions[conv_id] = agent

    # Activate skill if selected
    if req.skill_name:
        await agent.activate_skill(req.skill_name)
    else:
        agent.reset_skills()

    turn_id = req.turn_id or f"turn_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"

    # Run agent loop
    result = await agent.run(req.message, caller_context={
        "source": "unified_web_ui",
        "conversation_id": conv_id,
        "turn_id": turn_id
    })

    return {
        "session_id": conv_id,
        "conversation_id": conv_id,
        "turn_id": result.turn_id or turn_id,
        "request_ids": result.request_ids,
        "response": result.response,
        "tool_calls": result.tool_calls_executed,
        "active_skills": agent.active_skills,
        "tokens": {
            "prompt_tokens": result.total_prompt_tokens,
            "completion_tokens": result.total_completion_tokens,
            "total_tokens": result.total_prompt_tokens + result.total_completion_tokens
        },
        "success": bool(result.response)
    }

@app.post("/api/chat/clear")
async def clear_ui_chat(req: Dict[str, str]):
    """Reset chat history for a session and generate a brand new conversation ID."""
    sess_id = req.get("conversation_id") or req.get("session_id")
    if sess_id and sess_id in ui_agent_sessions:
        try:
            await ui_agent_sessions[sess_id].close()
        except Exception:
            pass
        del ui_agent_sessions[sess_id]
    
    new_conv_id = f"conv_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
    return {
        "success": True,
        "status": "cleared",
        "old_conversation_id": sess_id,
        "new_conversation_id": new_conv_id,
        "conversation_id": new_conv_id,
        "session_id": new_conv_id
    }

# ----------------------------------------------------------------------
# Interactive MCP Tools Explorer & Playground Endpoints
# ----------------------------------------------------------------------

class ToolExecutionRequest(BaseModel):
    tool: str
    args: Dict[str, Any] = {}

@app.get("/api/tools")
async def list_available_tools():
    """List all registered MCP tools with JSON schemas, arguments, and descriptions."""
    tools_catalog = [
        {
            "name": "calculator",
            "category": "Math & Budgeting",
            "icon": "🧮",
            "description": "Compute math expressions, tip calculations, bill splitting, and travel budgets.",
            "params": [
                {"name": "expression", "type": "string", "description": "Mathematical formula to evaluate (e.g. '184.50 * 0.18' or '199.99 * 0.85')", "example": "184.50 * 0.18"},
                {"name": "tip", "type": "string", "description": "Optional tip calculation instruction", "example": "18%"},
                {"name": "total", "type": "string", "description": "Optional bill total", "example": "184.50"}
            ]
        },
        {
            "name": "calculate_tip_and_split",
            "category": "Math & Budgeting",
            "icon": "🍕",
            "description": "Calculate restaurant tips and split totals evenly across party members.",
            "params": [
                {"name": "total", "type": "number", "description": "Total bill amount in dollars", "example": 184.50},
                {"name": "tip_percentage", "type": "number", "description": "Tip percentage in decimal (e.g. 0.18 for 18%)", "example": 0.18},
                {"name": "split_count", "type": "integer", "description": "Number of diners splitting the bill", "example": 4}
            ]
        },
        {
            "name": "weather",
            "category": "Weather & Forecasts",
            "icon": "⛅",
            "description": "Live weather conditions, temperatures, humidity, wind, and 3-day forecasts for any city.",
            "params": [
                {"name": "city", "type": "string", "description": "City or destination name (e.g. 'Paris', 'Tokyo', 'New York')", "example": "Paris"}
            ]
        },
        {
            "name": "web_search",
            "category": "Web Search & Discovery",
            "icon": "🔍",
            "description": "Search online travel spots, top food spots, quick recipes, and product deals.",
            "params": [
                {"name": "query", "type": "string", "description": "Search query or question", "example": "top bakeries in Paris"}
            ]
        },
        {
            "name": "product_knowledge",
            "category": "Shopping & Products",
            "icon": "🛍️",
            "description": "Browse consumer product catalog, specs, prices, ratings, and discounts.",
            "params": [
                {"name": "query", "type": "string", "description": "Product search query or product ID", "example": "headphones"},
                {"name": "category", "type": "string", "description": "Optional category filter", "example": "Electronics"}
            ]
        },
        {
            "name": "workspace_file_ops",
            "category": "Workspace & File Ops",
            "icon": "📁",
            "description": "Read, write, append, or list files in the agent workspace directory.",
            "params": [
                {"name": "action", "type": "string", "description": "File action: 'write', 'read', 'list', 'delete'", "example": "write"},
                {"name": "filename", "type": "string", "description": "Target filename (e.g. 'packing_list.txt')", "example": "notes.txt"},
                {"name": "content", "type": "string", "description": "Content to write if action is write/append", "example": "Packing list for Paris"}
            ]
        },
        {
            "name": "system_tools",
            "category": "System & Telemetry",
            "icon": "💻",
            "description": "Inspect host system metrics: CPU, memory utilization, disk space, and OS environment.",
            "params": []
        },
        {
            "name": "knowledge_base_search",
            "category": "Knowledge Base",
            "icon": "📚",
            "description": "Search internal technical knowledge base (LiteLLM proxy, Ollama, fastmcp).",
            "params": [
                {"name": "query", "type": "string", "description": "Keywords to search", "example": "LiteLLM"}
            ]
        }
    ]
    return {"tools": tools_catalog, "count": len(tools_catalog)}

@app.post("/api/tools/execute")
async def execute_tool_endpoint(req: ToolExecutionRequest):
    """Execute a single MCP tool directly in the Sandbox Playground."""
    start_t = time.time()
    tool_name = req.tool.lower().strip()
    args = req.args or {}

    try:
        if tool_name in ("calculator", "calculate"):
            from mcp_server.tools.math_tools import calculate
            res = calculate(
                expression=str(args.get("expression") or args.get("formula") or ""),
                formula=str(args.get("formula") or ""),
                tip=str(args.get("tip") or ""),
                total=str(args.get("total") or "")
            )
        elif tool_name == "calculate_tip_and_split":
            from mcp_server.tools.math_tools import calculate_tip_and_split
            res = calculate_tip_and_split(
                total=float(args.get("total") or args.get("bill") or 0.0),
                tip_percentage=float(args.get("tip_percentage") or args.get("tip_percent") or 0.18),
                split_count=int(args.get("split_count") or args.get("split") or args.get("people") or 1)
            )
        elif tool_name in ("weather", "get_weather"):
            from mcp_server.tools.weather_tools import get_weather
            res = get_weather(city=str(args.get("city") or args.get("location") or "Paris"))
        elif tool_name in ("web_search", "search"):
            from mcp_server.tools.web_search_tools import web_search
            res = web_search(query=str(args.get("query") or args.get("q") or "popular travel destinations"))
        elif tool_name in ("product_knowledge", "product_tools", "products"):
            from mcp_server.tools.product_tools import product_knowledge
            res = product_knowledge(
                query=str(args.get("query") or args.get("q") or ""),
                category=args.get("category")
            )
        elif tool_name in ("workspace_file_ops", "file_tools", "file_ops"):
            from mcp_server.tools.file_tools import workspace_file_ops
            res = workspace_file_ops(
                action=str(args.get("action") or "list"),
                filename=args.get("filename"),
                content=args.get("content")
            )
        elif tool_name in ("system_tools", "get_system_metrics"):
            from mcp_server.tools.system_tools import get_system_metrics
            res = get_system_metrics()
        elif tool_name in ("knowledge_base_search", "search_tools"):
            from mcp_server.tools.search_tools import search_knowledge_base
            res = search_knowledge_base(query=str(args.get("query") or ""))
        else:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

        latency_ms = (time.time() - start_t) * 1000
        return {
            "success": True,
            "tool": tool_name,
            "args": args,
            "result": res,
            "latency_ms": round(latency_ms, 2)
        }
    except Exception as e:
        latency_ms = (time.time() - start_t) * 1000
        return {
            "success": False,
            "tool": tool_name,
            "args": args,
            "error": str(e),
            "latency_ms": round(latency_ms, 2)
        }

# ----------------------------------------------------------------------
# Domain Skills Hub Endpoints
# ----------------------------------------------------------------------

custom_user_skills: Dict[str, Dict[str, Any]] = {}

class CustomSkillRequest(BaseModel):
    id: str
    name: str
    category: Optional[str] = "Custom Skills"
    description: str
    recommended_tools: Optional[List[str]] = []
    system_prompt: str
    default_params: Optional[Dict[str, Any]] = {}

@app.get("/api/skills")
async def list_available_skills():
    """List all built-in and user-registered domain skills."""
    from mcp_server.skills import ALL_SKILLS
    skills_list = list(ALL_SKILLS.values())
    for s in custom_user_skills.values():
        skills_list.append(s)
    return {"skills": skills_list, "total": len(skills_list)}

@app.post("/api/skills/custom")
async def create_custom_skill(req: CustomSkillRequest):
    """Register a new user-defined custom domain skill."""
    skill_data = {
        "id": req.id,
        "name": req.name,
        "category": req.category or "Custom Skills",
        "description": req.description,
        "recommended_tools": req.recommended_tools or [],
        "system_prompt": req.system_prompt,
        "default_params": req.default_params or {},
        "is_custom": True
    }
    custom_user_skills[req.id] = skill_data
    return {"success": True, "skill": skill_data}

@app.delete("/api/skills/custom/{skill_id}")
async def delete_custom_skill(skill_id: str):
    """Delete a custom skill."""
    if skill_id in custom_user_skills:
        del custom_user_skills[skill_id]
        return {"success": True, "deleted": skill_id}
    raise HTTPException(status_code=404, detail="Custom skill not found")

# ----------------------------------------------------------------------
# Workspace File Explorer Endpoints
# ----------------------------------------------------------------------

class WorkspaceFileSaveRequest(BaseModel):
    filename: str
    content: str

@app.get("/api/workspace/files")
async def list_workspace_files():
    """List all files in ./workspace directory."""
    ws_dir = Path(__file__).parent.parent / "workspace"
    ws_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for p in sorted(ws_dir.glob("*")):
        if p.is_file():
            files.append({
                "filename": p.name,
                "size_bytes": p.stat().st_size,
                "modified_time": p.stat().st_mtime,
                "path": str(p)
            })
    return {"files": files, "count": len(files), "workspace_dir": str(ws_dir.resolve())}

@app.get("/api/workspace/files/{filename:path}")
async def get_workspace_file_content(filename: str):
    """Get contents of a file in the workspace directory."""
    ws_dir = (Path(__file__).parent.parent / "workspace").resolve()
    target = (ws_dir / filename).resolve()
    if not str(target).startswith(str(ws_dir)) or not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found in workspace")
    return {
        "filename": filename,
        "content": target.read_text(encoding="utf-8", errors="replace"),
        "size_bytes": target.stat().st_size,
        "modified_time": target.stat().st_mtime
    }

@app.post("/api/workspace/files")
async def save_workspace_file(req: WorkspaceFileSaveRequest):
    """Create or overwrite a file in the workspace directory."""
    ws_dir = (Path(__file__).parent.parent / "workspace").resolve()
    ws_dir.mkdir(parents=True, exist_ok=True)
    target = (ws_dir / req.filename).resolve()
    if not str(target).startswith(str(ws_dir)):
        raise HTTPException(status_code=400, detail="Invalid file path")
    target.write_text(req.content, encoding="utf-8")
    return {
        "success": True,
        "filename": req.filename,
        "size_bytes": target.stat().st_size,
        "modified_time": target.stat().st_mtime
    }

@app.delete("/api/workspace/files/{filename:path}")
async def delete_workspace_file(filename: str):
    """Delete a file from the workspace directory."""
    ws_dir = (Path(__file__).parent.parent / "workspace").resolve()
    target = (ws_dir / filename).resolve()
    if not str(target).startswith(str(ws_dir)) or not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    target.unlink()
    return {"success": True, "deleted": filename}

# ----------------------------------------------------------------------
# System Metrics & Diagnostics Endpoints
# ----------------------------------------------------------------------

@app.get("/api/system/metrics")
async def get_system_telemetry():
    """Retrieve host CPU, memory, disk, and platform telemetry."""
    try:
        from mcp_server.tools.system_tools import get_system_metrics
        return get_system_metrics()
    except Exception as e:
        return {"error": str(e), "status": "unavailable"}

# ----------------------------------------------------------------------
# Gateway Runtime Configuration & Keys Management
# ----------------------------------------------------------------------

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

@app.get("/api/config")
async def get_gateway_runtime_config():
    """Get active Gateway configuration with masked credentials."""
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
        }
    }

@app.post("/api/config")
async def update_gateway_runtime_config(req: ConfigUpdateRequest):
    """Update runtime Gateway configuration."""
    if req.default_model: config.default_model = req.default_model
    if req.fallback_model: config.fallback_model = req.fallback_model
    if req.ollama_api_base: config.ollama_api_base = req.ollama_api_base
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

    return {"success": True, "config": await get_gateway_runtime_config()}

class UIEvalRequest(BaseModel):
    agent_id: Optional[str] = "mcp_default"
    model: Optional[str] = None
    judge_model: Optional[str] = "ollama/gemma2:2b"
    categories: Optional[List[str]] = None
    iterations: Optional[int] = 1

class RegisterAgentRequest(BaseModel):
    adapter_id: str
    name: str
    type: str = "http"  # "http" or "mcp"
    endpoint_url: Optional[str] = None
    description: Optional[str] = ""
    model: Optional[str] = None

class RegisterModelRequest(BaseModel):
    model_id: str
    name: str
    provider: str = "ollama"
    api_base: Optional[str] = None
    description: Optional[str] = ""

class RegisterJudgeRequest(BaseModel):
    judge_id: str
    name: str
    model: str
    rubric_description: Optional[str] = ""

# ---------------------------------------------------------------------------
# Evals Registries & Runner Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/evals/agents")
async def list_eval_agents():
    """List all registered agent adapters."""
    from evals_framework import agent_registry
    return {"agents": agent_registry.list_all()}

@app.post("/api/evals/agents")
async def register_eval_agent(req: RegisterAgentRequest):
    """Register a custom Agent Adapter (e.g. HTTPAgentAdapter or MCPAgentAdapter)."""
    from evals_framework import agent_registry, HTTPAgentAdapter, MCPAgentAdapter
    if req.type == "http" and req.endpoint_url:
        adapter = HTTPAgentAdapter(
            adapter_id=req.adapter_id,
            name=req.name,
            endpoint_url=req.endpoint_url,
            description=req.description or "",
            model=req.model
        )
    else:
        adapter = MCPAgentAdapter(
            adapter_id=req.adapter_id,
            name=req.name,
            description=req.description or "",
            model=req.model or config.default_model,
            gateway_url=f"http://localhost:{config.port}"
        )
    agent_registry.register(adapter)
    return {"success": True, "agent": adapter.to_dict()}

@app.delete("/api/evals/agents/{agent_id}")
async def unregister_eval_agent(agent_id: str):
    """Unregister an Agent Adapter."""
    from evals_framework import agent_registry
    removed = agent_registry.unregister(agent_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"success": True, "removed": agent_id}

@app.get("/api/evals/models")
async def list_eval_models():
    """List all registered candidate benchmark models."""
    from evals_framework import model_registry
    return {"models": model_registry.list_all()}

@app.post("/api/evals/models")
async def register_eval_model(req: RegisterModelRequest):
    """Register a new candidate model in the Model Registry."""
    from evals_framework import model_registry, ModelSpec
    spec = ModelSpec(
        model_id=req.model_id,
        name=req.name,
        provider=req.provider,
        api_base=req.api_base,
        description=req.description or ""
    )
    model_registry.register(spec)
    return {"success": True, "model": spec.model_dump()}

@app.delete("/api/evals/models/{model_id:path}")
async def unregister_eval_model(model_id: str):
    """Unregister a candidate model."""
    from evals_framework import model_registry
    removed = model_registry.unregister(model_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"success": True, "removed": model_id}

@app.get("/api/evals/judges")
async def list_eval_judges():
    """List all registered LLM-as-a-Judge evaluators."""
    from evals_framework import judge_registry
    return {"judges": judge_registry.list_all()}

@app.post("/api/evals/judges")
async def register_eval_judge(req: RegisterJudgeRequest):
    """Register a new LLM Judge specification."""
    from evals_framework import judge_registry, JudgeSpec
    spec = JudgeSpec(
        judge_id=req.judge_id,
        name=req.name,
        model=req.model,
        rubric_description=req.rubric_description or ""
    )
    judge_registry.register(spec)
    return {"success": True, "judge": spec.model_dump()}

@app.delete("/api/evals/judges/{judge_id}")
async def unregister_eval_judge(judge_id: str):
    """Unregister an LLM Judge specification."""
    from evals_framework import judge_registry
    removed = judge_registry.unregister(judge_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Judge not found")
    return {"success": True, "removed": judge_id}

@app.post("/api/evals/run")
async def run_ui_evals(req: UIEvalRequest):
    """Run Evals Framework benchmark evaluation with selected Agent Adapter, Model, Judge, and Iterations."""
    from evals_framework import EvalsRunner

    target_model = req.model or config.default_model
    target_judge = req.judge_model or "ollama/gemma2:2b"
    target_agent = req.agent_id or "mcp_default"
    num_iter = max(1, int(req.iterations or 1))

    runner = EvalsRunner(
        agent_adapter=target_agent,
        model=target_model,
        judge_model=target_judge,
        gateway_url=f"http://localhost:{config.port}"
    )

    results = await runner.run_suite(categories=req.categories, iterations=num_iter)
    return results

@app.get("/api/evals/run-stream")
@app.post("/api/evals/run-stream")
async def run_ui_evals_stream(
    model: Optional[str] = None,
    judge_model: Optional[str] = None,
    agent_id: Optional[str] = None,
    categories: Optional[str] = None,
    iterations: Optional[int] = 1
):
    """Stream real-time log events and grader scores during benchmark suite execution."""
    from fastapi.responses import StreamingResponse
    import asyncio
    import json

    cats = [c.strip() for c in categories.split(",")] if categories else None
    target_model = model or config.default_model
    target_judge = judge_model or "ollama/gemma2:2b"
    target_agent = agent_id or "mcp_default"
    num_iter = max(1, int(iterations or 1))

    async def event_generator():
        queue = asyncio.Queue()

        async def callback(event: dict):
            await queue.put(event)

        async def runner_task():
            from evals_framework import EvalsRunner
            runner = EvalsRunner(
                agent_adapter=target_agent,
                model=target_model,
                judge_model=target_judge,
                gateway_url=f"http://localhost:{config.port}"
            )
            try:
                await runner.run_suite(categories=cats, on_event=callback, iterations=num_iter)
            except Exception as e:
                err_text = str(e).strip() or f"{type(e).__name__} (Execution timed out or connection was reset)"
                await queue.put({"type": "error", "message": f"❌ Benchmark Execution Error: {err_text}"})
            finally:
                await queue.put(None)

        task = asyncio.create_task(runner_task())

        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=1.5)
                if item is None:
                    break
                yield f"data: {json.dumps(item)}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/evals/compare-models-stream")
@app.post("/api/evals/compare-models-stream")
async def run_ui_compare_models_stream(
    models: Optional[str] = None,
    judge_model: Optional[str] = None,
    agent_id: Optional[str] = None,
    categories: Optional[str] = None,
    iterations: Optional[int] = 1
):
    """Stream real-time log events and comparison results across multiple models."""
    from fastapi.responses import StreamingResponse
    import asyncio
    import json

    cats = [c.strip() for c in categories.split(",")] if categories else None
    target_judge = judge_model or "ollama/gemma2:2b"
    target_agent = agent_id or "mcp_default"
    model_list = [m.strip() for m in models.split(",") if m.strip()] if models else ["ollama/gemma2:2b"]
    num_iter = max(1, int(iterations or 1))

    async def event_generator():
        queue = asyncio.Queue()

        async def callback(event: dict):
            await queue.put(event)

        async def runner_task():
            from evals_framework import EvalsRunner, history_engine
            run_summaries = []
            run_ids = []

            avg_note = f" ({num_iter}x Averaged Runs)" if num_iter > 1 else ""
            await queue.put({
                "type": "compare_start",
                "models": model_list,
                "iterations": num_iter,
                "message": f"⚔️ Starting Head-to-Head Benchmark for {len(model_list)} models{avg_note}: {', '.join(model_list)}..."
            })

            try:
                for idx, mdl in enumerate(model_list, 1):
                    await queue.put({
                        "type": "model_start",
                        "model_index": idx,
                        "total_models": len(model_list),
                        "model": mdl,
                        "iterations": num_iter,
                        "message": f"\n======================================================\n📦 [{idx}/{len(model_list)}] Benchmarking Model: {mdl}{avg_note}\n======================================================"
                    })

                    runner = EvalsRunner(
                        agent_adapter=target_agent,
                        model=mdl,
                        judge_model=target_judge,
                        gateway_url=f"http://localhost:{config.port}"
                    )
                    summary = await runner.run_suite(categories=cats, on_event=callback, iterations=num_iter)
                    run_summaries.append(summary)
                    if "run_id" in summary:
                        run_ids.append(summary["run_id"])

                comparison = history_engine.compare_runs(run_ids)
                payload = {
                    "comparison": comparison,
                    "runs": run_summaries,
                    "models": model_list,
                    "iterations": num_iter
                }
                winner_name = comparison.get("winner", {}).get("model", "None")
                await queue.put({
                    "type": "compare_complete",
                    "payload": payload,
                    "winner": winner_name,
                    "message": f"\n🏆 Head-to-Head Benchmark Completed! Winner: {winner_name}\n"
                })
            except Exception as e:
                err_text = str(e).strip() or f"{type(e).__name__} (Execution timed out or connection was reset)"
                await queue.put({"type": "error", "message": f"❌ Head-to-Head Evaluation Error: {err_text}"})
            finally:
                await queue.put(None)

        task = asyncio.create_task(runner_task())

        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=1.5)
                if item is None:
                    break
                yield f"data: {json.dumps(item)}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/evals/runs")
async def list_eval_runs(limit: int = 50):
    """List all historical benchmark evaluation runs with summary scores."""
    from evals_framework import history_engine
    runs = history_engine.list_runs(limit=limit)
    return {"runs": runs, "total": len(runs)}

@app.get("/api/evals/runs/{run_id}")
async def get_eval_run_detail(run_id: str):
    """Fetch full metrics, scorecard, and individual test cases for a specific run."""
    from evals_framework import history_engine
    run = history_engine.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

@app.get("/api/evals/compare")
async def compare_eval_runs(runs: str):
    """Compare multiple benchmark runs side-by-side (runs is comma-separated run IDs)."""
    from evals_framework import history_engine
    run_ids = [r.strip() for r in runs.split(",") if r.strip()]
    if not run_ids:
        raise HTTPException(status_code=400, detail="Must provide at least one run ID")
    comparison = history_engine.compare_runs(run_ids)
    return comparison

@app.get("/api/evals/reports")
async def list_eval_reports():
    """List generated evaluation markdown reports."""
    reports_dir = Path(__file__).parent.parent / "evals_framework" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for f in sorted(reports_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
        files.append({
            "filename": f.name,
            "size_bytes": f.stat().st_size,
            "modified_time": f.stat().st_mtime
        })
    return {"reports": files}

@app.get("/api/evals/reports/{filename}")
async def get_eval_report(filename: str):
    """Fetch content of a specific evaluation markdown report."""
    reports_dir = Path(__file__).parent.parent / "evals_framework" / "reports"
    safe_file = (reports_dir / filename).resolve()
    if not safe_file.exists() or not str(safe_file).startswith(str(reports_dir.resolve())):
        raise HTTPException(status_code=404, detail="Report not found")
    return {"filename": filename, "content": safe_file.read_text(encoding="utf-8")}

# ----------------------------------------------------------------------
# SSE Streaming Chat Endpoint
# ----------------------------------------------------------------------

class UIStreamChatRequest(BaseModel):
    message: str
    model: Optional[str] = None
    skill_name: Optional[str] = None
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None
    turn_id: Optional[str] = None

@app.post("/api/chat/stream")
async def handle_ui_chat_stream(req: UIStreamChatRequest):
    """SSE streaming chat endpoint — yields token deltas and tool events in real-time."""
    base_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(base_dir))
    sys.path.insert(0, str(base_dir / "mcp_server"))

    from ai_agent import AgenticLLMAgent

    conv_id = req.conversation_id or req.session_id or f"conv_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
    target_model = req.model or config.default_model
    turn_id = req.turn_id or f"turn_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"

    agent = ui_agent_sessions.get(conv_id)
    if agent is None or agent.model != target_model:
        if agent:
            await agent.close()
        agent = AgenticLLMAgent(
            gateway_url=f"http://localhost:{config.port}",
            agent_name="EverydayAssistant",
            caller_id="web_ui_user",
            model=target_model,
            session_id=conv_id
        )
        await agent.initialize()
        ui_agent_sessions[conv_id] = agent

    if req.skill_name:
        await agent.activate_skill(req.skill_name)
    else:
        agent.reset_skills()

    async def event_generator():
        event_queue = asyncio.Queue()

        def step_callback(event_type, data):
            event_queue.put_nowait({"type": event_type, "data": data})

        agent.on_step_callback = step_callback

        async def run_agent():
            try:
                result = await agent.run(req.message, caller_context={
                    "source": "streaming_web_ui",
                    "conversation_id": conv_id,
                    "turn_id": turn_id
                })
                await event_queue.put({
                    "type": "final_result",
                    "data": {
                        "response": result.response,
                        "tool_calls": result.tool_calls_executed,
                        "tokens": {
                            "prompt_tokens": result.total_prompt_tokens,
                            "completion_tokens": result.total_completion_tokens
                        },
                        "session_id": conv_id,
                        "conversation_id": conv_id,
                        "turn_id": result.turn_id or turn_id,
                        "active_skills": agent.active_skills
                    }
                })
            except Exception as e:
                await event_queue.put({"type": "error", "data": {"message": str(e)}})
            finally:
                await event_queue.put(None)

        task = asyncio.create_task(run_agent())

        while True:
            try:
                item = await asyncio.wait_for(event_queue.get(), timeout=1.5)
                if item is None:
                    break
                yield format_sse_event(item, event_type=item.get("type", "step"))
            except asyncio.TimeoutError:
                yield format_sse_keepalive()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )

# ----------------------------------------------------------------------
# HITL Safety Gate Endpoints
# ----------------------------------------------------------------------

@app.get("/api/hitl/pending")
async def list_hitl_pending():
    """List all pending HITL approval requests."""
    try:
        from mcp_server.hitl import hitl_registry
        return {"pending": hitl_registry.get_pending(), "count": len(hitl_registry.get_pending())}
    except ImportError:
        return {"pending": [], "count": 0}

@app.post("/api/hitl/approve/{request_id}")
async def approve_hitl(request_id: str):
    """Approve a pending HITL request."""
    try:
        from mcp_server.hitl import hitl_registry
        success = hitl_registry.approve(request_id, approved_by="web_ui_user")
        return {"success": success, "request_id": request_id, "action": "approved"}
    except ImportError:
        raise HTTPException(status_code=500, detail="HITL module not available")

@app.post("/api/hitl/deny/{request_id}")
async def deny_hitl(request_id: str):
    """Deny a pending HITL request."""
    try:
        from mcp_server.hitl import hitl_registry
        success = hitl_registry.deny(request_id, denied_by="web_ui_user")
        return {"success": success, "request_id": request_id, "action": "denied"}
    except ImportError:
        raise HTTPException(status_code=500, detail="HITL module not available")

@app.get("/api/hitl/rules")
async def list_hitl_rules():
    """List all registered HITL safety rules."""
    try:
        from mcp_server.hitl import hitl_registry
        return {"rules": hitl_registry.get_rules()}
    except ImportError:
        return {"rules": []}

@app.get("/api/hitl/history")
async def hitl_history(limit: int = 50):
    """Get recent HITL resolution history."""
    try:
        from mcp_server.hitl import hitl_registry
        return {"history": hitl_registry.get_history(limit=limit)}
    except ImportError:
        return {"history": []}

# ----------------------------------------------------------------------
# Multi-Agent Orchestrator Endpoints
# ----------------------------------------------------------------------

class OrchestratorRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    max_workers: Optional[int] = 4

@app.post("/api/orchestrator/run")
async def run_orchestrator(req: OrchestratorRequest):
    """Run a multi-agent orchestration for a complex prompt."""
    base_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(base_dir))

    from ai_agent.orchestrator import SupervisorAgent

    supervisor = SupervisorAgent(
        gateway_url=f"http://localhost:{config.port}",
        model=req.model or config.default_model,
        max_workers=req.max_workers or 4
    )

    result = await supervisor.run(req.prompt)
    return result.to_dict()

@app.post("/api/orchestrator/run-stream")
async def run_orchestrator_stream(req: OrchestratorRequest):
    """Stream real-time orchestration events as the DAG executes."""
    base_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(base_dir))

    from ai_agent.orchestrator import SupervisorAgent

    async def event_generator():
        queue = asyncio.Queue()

        async def callback(event: dict):
            await queue.put(event)

        supervisor = SupervisorAgent(
            gateway_url=f"http://localhost:{config.port}",
            model=req.model or config.default_model,
            max_workers=req.max_workers or 4,
            on_event_callback=callback
        )

        async def run_task():
            try:
                result = await supervisor.run(req.prompt)
                await queue.put({"type": "final_result", "result": result.to_dict()})
            except Exception as e:
                await queue.put({"type": "error", "message": str(e)})
            finally:
                await queue.put(None)

        task = asyncio.create_task(run_task())

        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=2.0)
                if item is None:
                    break
                yield format_sse_event(item, event_type=item.get("type", "event"))
            except asyncio.TimeoutError:
                yield format_sse_keepalive()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )

# ----------------------------------------------------------------------
# Memory Explorer Endpoints
# ----------------------------------------------------------------------

class MemoryStoreRequest(BaseModel):
    content: str
    namespace: str = "default"
    metadata: Optional[Dict[str, Any]] = None

@app.get("/api/memory/list")
async def list_memories(namespace: str = "default", limit: int = 50):
    """List stored memories in a namespace."""
    try:
        from mcp_server.tools.memory_tools import memory_list
        return memory_list(namespace=namespace, limit=limit)
    except ImportError:
        return {"status": "error", "message": "Memory module not available"}

@app.post("/api/memory/store")
async def store_memory(req: MemoryStoreRequest):
    """Store a new memory."""
    try:
        from mcp_server.tools.memory_tools import memory_store
        return memory_store(content=req.content, namespace=req.namespace, metadata=req.metadata)
    except ImportError:
        return {"status": "error", "message": "Memory module not available"}

class MemoryRecallRequest(BaseModel):
    query: str
    namespace: str = "default"
    top_k: int = 5

@app.post("/api/memory/recall")
async def recall_memories(req: MemoryRecallRequest):
    """Recall memories semantically similar to a query."""
    try:
        from mcp_server.tools.memory_tools import memory_recall
        return memory_recall(query=req.query, namespace=req.namespace, top_k=req.top_k)
    except ImportError:
        return {"status": "error", "message": "Memory module not available"}

@app.delete("/api/memory/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a specific memory."""
    try:
        from mcp_server.tools.memory_tools import memory_delete
        return memory_delete(memory_id=memory_id)
    except ImportError:
        return {"status": "error", "message": "Memory module not available"}

@app.get("/api/memory/namespaces")
async def list_memory_namespaces():
    """List all memory namespaces."""
    try:
        from mcp_server.memory_backend import memory_backend
        return {"namespaces": memory_backend.list_namespaces()}
    except ImportError:
        return {"namespaces": []}

# ----------------------------------------------------------------------
# Cost Tracking & Rate Limiting Endpoints
# ----------------------------------------------------------------------

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.host, port=config.port)
