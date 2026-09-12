"""Unit tests for Durability & State enhancements.

Tests:
1. Agent session and turn persistence in SQLite.
2. Agent session rehydration across agent instance restarts.
3. Tool execution idempotency token caching.
4. Swarm Orchestrator persistence into workflow_runs and node_checkpoints.
5. HITL approval hydration from SQLite.
"""

import pytest
import json
import uuid
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

from llm_gateway.db import (
    init_db,
    save_agent_session,
    get_agent_session,
    save_agent_turn,
    get_agent_turns,
    save_tool_execution,
    get_tool_execution,
    get_workflow_run,
    get_node_checkpoints
)
from ai_agent.agent import AgenticLLMAgent, AgentRunResult
from ai_agent.orchestrator import SupervisorAgent
from ai_agent.task_planner import TaskDAG, SubTask
from mcp_server.hitl import HITLRegistry, HITLRule, RiskLevel


@pytest.mark.asyncio
async def test_agent_session_and_turn_crud(tmp_path, monkeypatch):
    """Test creating, updating, and querying agent sessions and turns in SQLite."""
    test_db = tmp_path / "test_state.db"
    init_db(test_db)

    sess_id = "sess_test_123"
    saved_sess = save_agent_session({
        "session_id": sess_id,
        "agent_name": "TestAgent",
        "model": "ollama/gemma2:2b",
        "status": "ACTIVE",
        "system_prompt": "You are a test assistant.",
        "active_skills": ["data_analysis_skill"]
    }, db_path=test_db)

    assert saved_sess["session_id"] == sess_id

    fetched_sess = get_agent_session(sess_id, db_path=test_db)
    assert fetched_sess is not None
    assert fetched_sess["agent_name"] == "TestAgent"
    assert fetched_sess["model"] == "ollama/gemma2:2b"
    assert fetched_sess["active_skills"] == ["data_analysis_skill"]

    # Save turns
    turn_id = "turn_test_001"
    saved_turn = save_agent_turn({
        "turn_id": turn_id,
        "session_id": sess_id,
        "turn_index": 1,
        "user_prompt": "Hello",
        "messages": [
            {"role": "system", "content": "You are a test assistant."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ],
        "tool_calls": [],
        "status": "COMPLETED",
        "prompt_tokens": 15,
        "completion_tokens": 5
    }, db_path=test_db)

    assert saved_turn["turn_id"] == turn_id

    turns = get_agent_turns(sess_id, db_path=test_db)
    assert len(turns) == 1
    assert turns[0]["turn_id"] == turn_id
    assert turns[0]["user_prompt"] == "Hello"
    assert len(turns[0]["messages"]) == 3


@pytest.mark.asyncio
async def test_tool_idempotency_cache(tmp_path):
    """Test saving and retrieving tool executions by idempotency key."""
    test_db = tmp_path / "test_idempotency.db"
    init_db(test_db)

    key = "idem_key_abc_123"
    tool_name = "workspace_file_ops"
    args = {"action": "read", "filename": "test.txt"}
    output = "file content sample"

    # Initially not present
    assert get_tool_execution(key, db_path=test_db) is None

    # Save
    save_tool_execution(key, tool_name, args, output, db_path=test_db)

    # Fetch
    cached = get_tool_execution(key, db_path=test_db)
    assert cached is not None
    assert cached["tool_name"] == tool_name
    assert cached["output"] == output
    assert cached["arguments"] == args


@pytest.mark.asyncio
async def test_agent_rehydration_across_instances(tmp_path, monkeypatch):
    """Test that a second agent instance rehydrates message history from a durable session."""
    test_db = tmp_path / "test_rehydration.db"
    monkeypatch.setenv("LLM_GATEWAY_DB_PATH", str(test_db))
    from llm_gateway.config import config as gw_config
    gw_config.db_path = test_db
    init_db(test_db)

    sess_id = f"sess_rehydrate_{uuid.uuid4().hex[:6]}"

    # Simulate Turn 1 executed by Agent Instance 1
    save_agent_session({
        "session_id": sess_id,
        "agent_name": "AgentInstance1",
        "model": "ollama/gemma2:2b",
        "status": "IDLE",
        "system_prompt": "You are a persistent assistant.",
        "active_skills": ["travel_planner_skill"]
    }, db_path=test_db)

    save_agent_turn({
        "turn_id": "turn_1001",
        "session_id": sess_id,
        "turn_index": 1,
        "user_prompt": "My budget is $500",
        "messages": [
            {"role": "system", "content": "You are a persistent assistant."},
            {"role": "user", "content": "My budget is $500"},
            {"role": "assistant", "content": "Got it, budget is $500."}
        ],
        "tool_calls": [],
        "status": "COMPLETED"
    }, db_path=test_db)

    # Spawn Agent Instance 2 with the same session_id (simulating server reboot)
    agent2 = AgenticLLMAgent(
        gateway_url="http://localhost:8000",
        session_id=sess_id
    )

    # Verify agent2 rehydrated state
    assert agent2.session_id == sess_id
    assert "travel_planner_skill" in agent2.active_skills
    assert len(agent2.messages) == 3
    assert agent2.messages[1]["content"] == "My budget is $500"
    assert agent2.messages[2]["content"] == "Got it, budget is $500."


@pytest.mark.asyncio
async def test_swarm_orchestrator_durable_persistence(tmp_path, monkeypatch):
    """Test that SupervisorAgent writes swarm runs and worker checkpoints into SQLite."""
    test_db = tmp_path / "test_swarm.db"
    monkeypatch.setenv("LLM_GATEWAY_DB_PATH", str(test_db))
    from llm_gateway.config import config as gw_config
    gw_config.db_path = test_db
    init_db(test_db)

    supervisor = SupervisorAgent(
        gateway_url="http://localhost:8000",
        model="ollama/gemma2:2b"
    )

    # Mock decompose, _execute_worker, and _synthesize to run offline deterministically
    mock_dag = TaskDAG(
        dag_id="test_dag_1",
        original_prompt="Plan a trip to Paris",
        tasks=[
            SubTask(task_id="t1", description="Find flights", skill="travel", depends_on=[]),
            SubTask(task_id="t2", description="Find hotels", skill="travel", depends_on=["t1"])
        ]
    )

    async def mock_decompose(prompt):
        return mock_dag

    async def mock_execute_worker(task, dag, sem):
        task.status = "completed"
        task.result = f"Completed {task.description}"
        from llm_gateway.db import save_node_checkpoint
        save_node_checkpoint({
            "run_id": getattr(supervisor, "_current_run_id", "test_run"),
            "node_id": task.task_id,
            "stage": 1,
            "node_type": "agent",
            "label": f"Worker-{task.skill}",
            "status": "COMPLETED",
            "step_input": task.description,
            "output": task.result,
            "duration_ms": 10.0
        })
        return {
            "task_id": task.task_id,
            "worker_id": f"Worker-{task.skill}",
            "status": "completed",
            "response": task.result,
            "prompt_tokens": 10,
            "completion_tokens": 5
        }

    async def mock_synthesize(dag, worker_results):
        return "Complete Paris trip plan."

    monkeypatch.setattr(supervisor, "decompose", mock_decompose)
    monkeypatch.setattr(supervisor, "_execute_worker", mock_execute_worker)
    monkeypatch.setattr(supervisor, "_synthesize", mock_synthesize)

    result = await supervisor.run("Plan a trip to Paris")
    assert result is not None
    assert result.status == "completed"
    run_id = result.run_id

    # Verify run persisted to SQLite workflow_runs
    db_run = get_workflow_run(run_id)
    assert db_run is not None
    assert db_run["status"] == "completed"
    assert db_run["final_output"] == "Complete Paris trip plan."

    # Verify node checkpoints in SQLite
    checkpoints = get_node_checkpoints(run_id)
    assert len(checkpoints) == 2
    assert {c["node_id"] for c in checkpoints} == {"t1", "t2"}

    # Verify get_run and list_runs query the DB
    supervisor._runs.clear()  # Clear in-memory cache to test DB fallback
    retrieved_run = supervisor.get_run(run_id)
    assert retrieved_run is not None
    assert retrieved_run.run_id == run_id
    assert retrieved_run.synthesized_response == "Complete Paris trip plan."

    runs_list = supervisor.list_runs(limit=10)
    assert any(r["run_id"] == run_id for r in runs_list)


@pytest.mark.asyncio
async def test_hitl_fallback_db_hydration(tmp_path, monkeypatch):
    """Test that HITL registry automatically hydrates pending requests from SQLite."""
    test_db = tmp_path / "test_hitl_hydrate.db"
    monkeypatch.setenv("LLM_GATEWAY_DB_PATH", str(test_db))
    from llm_gateway.config import config as gw_config
    gw_config.db_path = test_db
    init_db(test_db)

    from llm_gateway.db import save_hitl_request

    req_id = f"hitl_saved_{uuid.uuid4().hex[:6]}"
    save_hitl_request({
        "request_id": req_id,
        "tool_name": "workspace_file_ops",
        "arguments": {"action": "delete", "filename": "important.txt"},
        "risk_level": "high",
        "description": "File deletion approval",
        "created_at": time.time(),
        "timeout_seconds": 600.0,
        "status": "pending"
    })

    # Fresh registry without pre-loaded memory
    registry = HITLRegistry(hydrate_from_db=False)
    assert req_id not in registry._pending

    # Trigger hydrate_from_db
    registry.hydrate_from_db()
    assert req_id in registry._pending

    # Approving resolves it and updates DB
    approved = registry.approve(req_id, approved_by="unit_tester")
    assert approved is True
    assert registry._pending[req_id].status == "approved"
    assert len(registry.get_pending()) == 0

    from llm_gateway.db import get_hitl_requests
    history = get_hitl_requests()
    resolved_row = next((r for r in history if r["request_id"] == req_id), None)
    assert resolved_row is not None
    assert resolved_row["status"] == "approved"
    assert resolved_row["resolved_by"] == "unit_tester"
