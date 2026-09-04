"""
MCP Server FastAPI Router.
Exposes Model Context Protocol tools, domain skills, workspace files,
semantic vector memory, GraphRAG knowledge graph, and HITL safety endpoints.
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["mcp_server"])

# In-memory custom user skills
custom_user_skills: Dict[str, Dict[str, Any]] = {}


# ==============================================================================
# Pydantic Request Models
# ==============================================================================

class ToolExecutionRequest(BaseModel):
    tool: str
    args: Optional[Dict[str, Any]] = None


class CustomSkillRequest(BaseModel):
    id: str
    name: str
    category: Optional[str] = "Custom Skills"
    description: str
    recommended_tools: Optional[List[str]] = []
    system_prompt: str
    default_params: Optional[Dict[str, Any]] = {}


class WorkspaceFileSaveRequest(BaseModel):
    filename: str
    content: str


class MemoryStoreRequest(BaseModel):
    content: str
    namespace: str = "default"
    metadata: Optional[Dict[str, Any]] = None


class MemoryRecallRequest(BaseModel):
    query: str
    namespace: str = "default"
    top_k: int = 5


class GraphAddRelationRequest(BaseModel):
    source_entity: str
    relation_type: str
    target_entity: str
    metadata: Optional[Dict[str, Any]] = None
    weight: float = 1.0


# ==============================================================================
# MCP Tools Explorer & Execution Endpoints
# ==============================================================================

@router.get("/api/tools")
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


@router.post("/api/tools/execute")
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
                filename=str(args.get("filename") or args.get("filepath") or args.get("file_path") or args.get("path") or ""),
                content=str(args.get("content") or args.get("text") or args.get("data") or "")
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


# ==============================================================================
# Domain Skills Hub Endpoints
# ==============================================================================

@router.get("/api/skills")
async def list_available_skills():
    """List all built-in and user-registered domain skills."""
    from mcp_server.skills import ALL_SKILLS
    skills_list = list(ALL_SKILLS.values())
    for s in custom_user_skills.values():
        skills_list.append(s)
    return {"skills": skills_list, "total": len(skills_list)}


@router.post("/api/skills/custom")
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


@router.delete("/api/skills/custom/{skill_id}")
async def delete_custom_skill(skill_id: str):
    """Delete a custom skill."""
    if skill_id in custom_user_skills:
        del custom_user_skills[skill_id]
        return {"success": True, "deleted": skill_id}
    raise HTTPException(status_code=404, detail="Custom skill not found")


# ==============================================================================
# Workspace Files Endpoints
# ==============================================================================

@router.get("/api/workspace/files")
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


@router.get("/api/workspace/files/{filename:path}")
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


@router.post("/api/workspace/files")
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


@router.delete("/api/workspace/files/{filename:path}")
async def delete_workspace_file(filename: str):
    """Delete a file from the workspace directory."""
    ws_dir = (Path(__file__).parent.parent / "workspace").resolve()
    target = (ws_dir / filename).resolve()
    if not str(target).startswith(str(ws_dir)) or not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    target.unlink()
    return {"success": True, "deleted": filename}


# ==============================================================================
# HITL Safety Gate Endpoints
# ==============================================================================

@router.get("/api/hitl/pending")
async def list_hitl_pending():
    """List all pending HITL approval requests."""
    try:
        from mcp_server.hitl import hitl_registry
        return {"pending": hitl_registry.get_pending(), "count": len(hitl_registry.get_pending())}
    except ImportError:
        return {"pending": [], "count": 0}


@router.post("/api/hitl/approve/{request_id}")
async def approve_hitl(request_id: str):
    """Approve a pending HITL request."""
    try:
        from mcp_server.hitl import hitl_registry
        success = hitl_registry.approve(request_id, approved_by="web_ui_user")
        return {"success": success, "request_id": request_id, "action": "approved"}
    except ImportError:
        raise HTTPException(status_code=500, detail="HITL module not available")


@router.post("/api/hitl/deny/{request_id}")
async def deny_hitl(request_id: str):
    """Deny a pending HITL request."""
    try:
        from mcp_server.hitl import hitl_registry
        success = hitl_registry.deny(request_id, denied_by="web_ui_user")
        return {"success": success, "request_id": request_id, "action": "denied"}
    except ImportError:
        raise HTTPException(status_code=500, detail="HITL module not available")


@router.get("/api/hitl/rules")
async def list_hitl_rules():
    """List all registered HITL safety rules."""
    try:
        from mcp_server.hitl import hitl_registry
        return {"rules": hitl_registry.get_rules()}
    except ImportError:
        return {"rules": []}


@router.get("/api/hitl/history")
async def hitl_history(limit: int = 50):
    """Get recent HITL resolution history."""
    try:
        from mcp_server.hitl import hitl_registry
        return {"history": hitl_registry.get_history(limit=limit)}
    except ImportError:
        return {"history": []}


# ==============================================================================
# Semantic Memory Explorer Endpoints
# ==============================================================================

@router.get("/api/memory/list")
async def list_memories(namespace: str = "default", limit: int = 50):
    """List stored memories in a namespace."""
    try:
        from mcp_server.tools.memory_tools import memory_list
        return memory_list(namespace=namespace, limit=limit)
    except ImportError:
        return {"status": "error", "message": "Memory module not available"}


@router.post("/api/memory/store")
async def store_memory(req: MemoryStoreRequest):
    """Store a new memory."""
    try:
        from mcp_server.tools.memory_tools import memory_store
        return memory_store(content=req.content, namespace=req.namespace, metadata=req.metadata)
    except ImportError:
        return {"status": "error", "message": "Memory module not available"}


@router.post("/api/memory/recall")
async def recall_memories(req: MemoryRecallRequest):
    """Recall memories semantically similar to a query."""
    try:
        from mcp_server.tools.memory_tools import memory_recall
        return memory_recall(query=req.query, namespace=req.namespace, top_k=req.top_k)
    except ImportError:
        return {"status": "error", "message": "Memory module not available"}


@router.delete("/api/memory/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a specific memory."""
    try:
        from mcp_server.tools.memory_tools import memory_delete
        return memory_delete(memory_id=memory_id)
    except ImportError:
        return {"status": "error", "message": "Memory module not available"}


@router.get("/api/memory/namespaces")
async def list_memory_namespaces():
    """List all memory namespaces."""
    try:
        from mcp_server.memory_backend import memory_backend
        return {"namespaces": memory_backend.list_namespaces()}
    except ImportError:
        return {"namespaces": []}


# ==============================================================================
# GraphRAG Knowledge Graph Endpoints
# ==============================================================================

@router.post("/api/graph/relation")
async def graph_add_relation_api(req: GraphAddRelationRequest):
    """Add a relation edge into the GraphRAG Knowledge Graph."""
    from mcp_server.graph_memory import get_graph_memory
    gm = get_graph_memory()
    return gm.add_relation(req.source_entity, req.relation_type, req.target_entity, req.metadata, req.weight)


@router.get("/api/graph/relations")
async def graph_query_relations_api(entity: str, direction: str = "both"):
    """Query connected relations for an entity."""
    from mcp_server.graph_memory import get_graph_memory
    gm = get_graph_memory()
    return {"entity": entity, "relations": gm.query_relations(entity, direction)}


@router.get("/api/graph/path")
async def graph_find_path_api(start: str, end: str, max_depth: int = 4):
    """Find multi-hop relational path connecting two entities."""
    from mcp_server.graph_memory import get_graph_memory
    gm = get_graph_memory()
    return gm.find_multi_hop_path(start, end, max_depth)
