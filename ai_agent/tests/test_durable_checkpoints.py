"""Unit tests for Phase 3: Durable State Machine & Step Checkpointing."""

import pytest
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient
from fastapi import FastAPI

from ai_agent.router import router as agent_router, CanvasExecuteRequest
from llm_gateway.db import (
    init_checkpoint_db, get_workflow_run, get_node_checkpoints,
    get_workflow_runs, create_workflow_run, update_workflow_run
)
from mcp_server.hitl import hitl_registry, HITLRule, RiskLevel


@pytest.fixture
def test_app(tmp_path, monkeypatch):
    """Create test FastAPI application configured with temporary SQLite DB."""
    db_file = tmp_path / "test_checkpoints.db"
    monkeypatch.setenv("LLM_GATEWAY_DB_PATH", str(db_file))
    
    app = FastAPI()
    app.include_router(agent_router)
    init_checkpoint_db(db_file)
    return app


@pytest.mark.asyncio
async def test_durable_dag_execution_checkpoints(test_app, tmp_path):
    """Test that canvas DAG execution records workflow run and individual node checkpoints."""
    client = TestClient(test_app)
    
    payload = {
        "workflow_name": "Test Financial Pipeline",
        "initial_input": "Calculate quarterly revenue: 100 * 5",
        "nodes": [
            {
                "id": "node-calc",
                "type": "tool",
                "label": "Calculator Node",
                "config": {"tool": "calculate", "expression": "100 * 5"}
            },
            {
                "id": "node-agent",
                "type": "agent",
                "label": "Analyst Agent",
                "config": {"role": "financial_auditor"}
            }
        ],
        "edges": [
            {"source": "node-calc", "target": "node-agent"}
        ]
    }
    
    response = client.post("/api/canvas/execute", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "run_id" in data
    run_id = data["run_id"]
    
    # Verify in DB
    run = get_workflow_run(run_id)
    assert run is not None
    assert run["workflow_name"] == "Test Financial Pipeline"
    assert run["status"] == "completed"
    assert run["total_stages"] == 2
    assert run["current_stage"] == 2
    assert "node-calc" in run["node_outputs"]
    
    # Verify node checkpoints
    checkpoints = get_node_checkpoints(run_id)
    assert len(checkpoints) == 2
    node_ids = [c["node_id"] for c in checkpoints]
    assert "node-calc" in node_ids
    assert "node-agent" in node_ids
    for c in checkpoints:
        assert c["status"] == "COMPLETED"
        assert len(c["output"]) > 0


@pytest.mark.asyncio
async def test_durable_dag_resume_skips_completed_nodes(test_app, tmp_path):
    """Test that resuming an incomplete workflow skips already-completed nodes."""
    client = TestClient(test_app)
    
    # 1. Create a simulated interrupted run at stage 1
    run_id = "run_test_resume_001"
    create_workflow_run({
        "run_id": run_id,
        "workflow_name": "Resumable Workflow",
        "status": "running",
        "initial_input": "Initial task input",
        "target_model": "ollama/gemma2:2b",
        "current_stage": 1,
        "total_stages": 2,
        "nodes": [
            {
                "id": "node-stage1",
                "type": "tool",
                "label": "Stage 1 Tool",
                "config": {"tool": "calculate", "expression": "50 + 50"}
            },
            {
                "id": "node-stage2",
                "type": "tool",
                "label": "Stage 2 Tool",
                "config": {"tool": "weather", "city": "Paris"}
            }
        ],
        "edges": [
            {"source": "node-stage1", "target": "node-stage2"}
        ],
        "stages": [["node-stage1"], ["node-stage2"]],
        "node_outputs": {"node-stage1": "Calculator Result (50 + 50): 100"},
        "final_output": "",
        "duration_ms": 150.0
    })
    
    # Save checkpoint for node-stage1
    from llm_gateway.db import save_node_checkpoint
    save_node_checkpoint({
        "run_id": run_id,
        "node_id": "node-stage1",
        "stage": 1,
        "node_type": "tool",
        "label": "Stage 1 Tool",
        "status": "COMPLETED",
        "step_input": "Initial task input",
        "output": "Calculator Result (50 + 50): 100",
        "duration_ms": 12.5
    })
    
    # 2. Call resume endpoint
    resume_resp = client.post(f"/api/canvas/resume/{run_id}")
    assert resume_resp.status_code == 200
    res_data = resume_resp.json()
    assert res_data["status"] == "success"
    assert res_data["resumed"] is True
    
    # Verify trace includes cached node-stage1 and freshly executed node-stage2
    trace = res_data["execution_trace"]
    assert len(trace) >= 2
    stage1_trace = next(t for t in trace if t["node_id"] == "node-stage1")
    assert stage1_trace.get("cached") is True
    
    stage2_trace = next(t for t in trace if t["node_id"] == "node-stage2")
    assert stage2_trace["status"] == "COMPLETED"
    
    # Verify DB reflects completed status
    updated_run = get_workflow_run(run_id)
    assert updated_run["status"] == "completed"
    assert "node-stage2" in updated_run["node_outputs"]


@pytest.mark.asyncio
async def test_canvas_runs_query_endpoints(test_app, tmp_path):
    """Test GET /api/canvas/runs and GET /api/canvas/runs/{id}."""
    client = TestClient(test_app)
    
    # Run a quick 1-node DAG
    payload = {
        "workflow_name": "Quick Weather Pipeline",
        "initial_input": "Weather in Tokyo",
        "nodes": [
            {
                "id": "node-tokyo",
                "type": "tool",
                "label": "Tokyo Weather",
                "config": {"tool": "weather", "city": "Tokyo"}
            }
        ],
        "edges": []
    }
    resp = client.post("/api/canvas/execute", json=payload)
    assert resp.status_code == 200
    run_id = resp.json()["run_id"]
    
    # Query all runs
    list_resp = client.get("/api/canvas/runs")
    assert list_resp.status_code == 200
    runs_data = list_resp.json()
    assert runs_data["count"] >= 1
    matching = [r for r in runs_data["runs"] if r["run_id"] == run_id]
    assert len(matching) == 1
    assert matching[0]["workflow_name"] == "Quick Weather Pipeline"
    
    # Query run details
    detail_resp = client.get(f"/api/canvas/runs/{run_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["run"]["run_id"] == run_id
    assert len(detail["checkpoints"]) == 1
    assert detail["checkpoints"][0]["node_id"] == "node-tokyo"


@pytest.mark.asyncio
async def test_hitl_sqlite_durability(test_app, tmp_path):
    """Test that HITL requests are written to SQLite and can be reloaded."""
    from llm_gateway.db import get_hitl_requests
    
    rule = HITLRule(
        tool_name="test_sensitive_transfer",
        risk_level=RiskLevel.HIGH,
        description="Approval required for financial wire transfer",
        timeout_seconds=30.0
    )
    
    # Create request
    hitl_req = hitl_registry.create_request(
        tool_name="test_sensitive_transfer",
        arguments={"account": "ACME-101", "amount": 50000},
        rule=rule
    )
    
    # Verify in DB
    db_reqs = get_hitl_requests()
    matching = [r for r in db_reqs if r["request_id"] == hitl_req.request_id]
    assert len(matching) == 1
    assert matching[0]["status"] == "pending"
    assert matching[0]["arguments"]["amount"] == 50000
    
    # Approve and check DB update
    approved = hitl_registry.approve(hitl_req.request_id, approved_by="admin_user")
    assert approved is True
    
    updated_db_reqs = get_hitl_requests()
    approved_req = next(r for r in updated_db_reqs if r["request_id"] == hitl_req.request_id)
    assert approved_req["status"] == "approved"
    assert approved_req["resolved_by"] == "admin_user"
