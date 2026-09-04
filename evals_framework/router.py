"""
Evals Framework FastAPI Router.
Provides benchmark execution, candidate model & judge registries, streaming evals,
side-by-side model comparison, and markdown report endpoints.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["evals_framework"])

DEFAULT_GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "ollama/gemma2:2b")
DEFAULT_JUDGE = os.environ.get("DEFAULT_JUDGE", "ollama/gemma2:2b")


# ==============================================================================
# Pydantic Request Models
# ==============================================================================

class RegisterAgentRequest(BaseModel):
    adapter_id: str
    name: str
    type: Optional[str] = "mcp"
    endpoint_url: Optional[str] = None
    description: Optional[str] = ""
    model: Optional[str] = None


class RegisterModelRequest(BaseModel):
    model_id: str
    name: str
    provider: str
    api_base: Optional[str] = None
    description: Optional[str] = ""


class RegisterJudgeRequest(BaseModel):
    judge_id: str
    name: str
    model: str
    rubric_description: Optional[str] = ""


class UIEvalRequest(BaseModel):
    model: Optional[str] = None
    judge_model: Optional[str] = None
    agent_id: Optional[str] = None
    categories: Optional[List[str]] = None
    iterations: Optional[int] = 1


# ==============================================================================
# Registries Endpoints
# ==============================================================================

@router.get("/api/evals/agents")
async def list_eval_agents():
    """List all registered agent adapters."""
    from evals_framework import agent_registry
    return {"agents": agent_registry.list_all()}


@router.post("/api/evals/agents")
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
            model=req.model or DEFAULT_MODEL,
            gateway_url=DEFAULT_GATEWAY_URL
        )
    agent_registry.register(adapter)
    return {"success": True, "agent": adapter.to_dict()}


@router.delete("/api/evals/agents/{agent_id}")
async def unregister_eval_agent(agent_id: str):
    """Unregister an Agent Adapter."""
    from evals_framework import agent_registry
    removed = agent_registry.unregister(agent_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"success": True, "removed": agent_id}


@router.get("/api/evals/models")
async def list_eval_models():
    """List all registered candidate benchmark models."""
    from evals_framework import model_registry
    return {"models": model_registry.list_all()}


@router.post("/api/evals/models")
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


@router.delete("/api/evals/models/{model_id:path}")
async def unregister_eval_model(model_id: str):
    """Unregister a candidate model."""
    from evals_framework import model_registry
    removed = model_registry.unregister(model_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"success": True, "removed": model_id}


@router.get("/api/evals/judges")
async def list_eval_judges():
    """List all registered LLM-as-a-Judge evaluators."""
    from evals_framework import judge_registry
    return {"judges": judge_registry.list_all()}


@router.post("/api/evals/judges")
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


@router.delete("/api/evals/judges/{judge_id}")
async def unregister_eval_judge(judge_id: str):
    """Unregister an LLM Judge specification."""
    from evals_framework import judge_registry
    removed = judge_registry.unregister(judge_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Judge not found")
    return {"success": True, "removed": judge_id}


# ==============================================================================
# Benchmark Runner & Streaming Endpoints
# ==============================================================================

@router.post("/api/evals/run")
async def run_ui_evals(req: UIEvalRequest):
    """Run Evals Framework benchmark evaluation with selected Agent Adapter, Model, Judge, and Iterations."""
    from evals_framework import EvalsRunner

    target_model = req.model or DEFAULT_MODEL
    target_judge = req.judge_model or DEFAULT_JUDGE
    target_agent = req.agent_id or "mcp_default"
    num_iter = max(1, req.iterations or 1)

    runner = EvalsRunner(
        agent_adapter=target_agent,
        model=target_model,
        judge_model=target_judge,
        gateway_url=DEFAULT_GATEWAY_URL
    )

    results = await runner.run_suite(categories=req.categories, iterations=num_iter)
    return results


@router.get("/api/evals/run-stream")
@router.post("/api/evals/run-stream")
async def run_ui_evals_stream(
    model: Optional[str] = None,
    judge_model: Optional[str] = None,
    agent_id: Optional[str] = None,
    categories: Optional[str] = None,
    iterations: Optional[int] = 1
):
    """Stream real-time log events and grader scores during benchmark suite execution."""
    cats = [c.strip() for c in categories.split(",")] if categories else None
    target_model = model or DEFAULT_MODEL
    target_judge = judge_model or DEFAULT_JUDGE
    target_agent = agent_id or "mcp_default"
    num_iter = max(1, iterations or 1)

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
                gateway_url=DEFAULT_GATEWAY_URL
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


@router.get("/api/evals/compare-models-stream")
@router.post("/api/evals/compare-models-stream")
async def run_ui_compare_models_stream(
    models: Optional[str] = None,
    judge_model: Optional[str] = None,
    agent_id: Optional[str] = None,
    categories: Optional[str] = None,
    iterations: Optional[int] = 1
):
    """Stream real-time log events and comparison results across multiple models."""
    cats = [c.strip() for c in categories.split(",")] if categories else None
    target_judge = judge_model or DEFAULT_JUDGE
    target_agent = agent_id or "mcp_default"
    model_list = [m.strip() for m in models.split(",") if m.strip()] if models else [DEFAULT_MODEL]
    num_iter = max(1, iterations or 1)

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
                        gateway_url=DEFAULT_GATEWAY_URL
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


# ==============================================================================
# Historical Runs & Reports Endpoints
# ==============================================================================

@router.get("/api/evals/runs")
async def list_eval_runs(limit: int = 50):
    """List all historical benchmark evaluation runs with summary scores."""
    from evals_framework import history_engine
    runs = history_engine.list_runs(limit=limit)
    return {"runs": runs, "total": len(runs)}


@router.get("/api/evals/runs/{run_id}")
async def get_eval_run_detail(run_id: str):
    """Fetch full metrics, scorecard, and individual test cases for a specific run."""
    from evals_framework import history_engine
    run = history_engine.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/api/evals/compare")
async def compare_eval_runs(runs: str):
    """Compare multiple benchmark runs side-by-side (runs is comma-separated run IDs)."""
    from evals_framework import history_engine
    run_ids = [r.strip() for r in runs.split(",") if r.strip()]
    if not run_ids:
        raise HTTPException(status_code=400, detail="Must provide at least one run ID")
    comparison = history_engine.compare_runs(run_ids)
    return comparison


@router.get("/api/evals/reports")
async def list_eval_reports():
    """List generated evaluation markdown reports."""
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for f in sorted(reports_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
        files.append({
            "filename": f.name,
            "size_bytes": f.stat().st_size,
            "modified_time": f.stat().st_mtime
        })
    return {"reports": files}


@router.get("/api/evals/reports/{filename}")
async def get_eval_report(filename: str):
    """Fetch content of a specific evaluation markdown report."""
    reports_dir = Path(__file__).parent / "reports"
    safe_file = (reports_dir / filename).resolve()
    if not safe_file.exists() or not str(safe_file).startswith(str(reports_dir.resolve())):
        raise HTTPException(status_code=404, detail="Report not found")
    return {"filename": filename, "content": safe_file.read_text(encoding="utf-8")}
