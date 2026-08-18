"""Unit tests for Generic Evals Framework: Adapters, Registries, and Historical Comparison."""

import pytest
import asyncio
import sys
from pathlib import Path

# Add project root and evals root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from evals_framework.adapters import (
        BaseAgentAdapter,
        AgentRunOutput,
        CallableAgentAdapter,
        HTTPAgentAdapter,
        MCPAgentAdapter,
        AgentRegistry
    )
    from evals_framework.registries import (
        ModelSpec,
        ModelRegistry,
        JudgeSpec,
        JudgeRegistry
    )
    from evals_framework.history import HistoryEngine
except (ImportError, ValueError):
    from adapters import (  # type: ignore[import-not-found]
        BaseAgentAdapter,
        AgentRunOutput,
        CallableAgentAdapter,
        HTTPAgentAdapter,
        MCPAgentAdapter,
        AgentRegistry
    )
    from registries import (  # type: ignore[import-not-found]
        ModelSpec,
        ModelRegistry,
        JudgeSpec,
        JudgeRegistry
    )
    from history import HistoryEngine  # type: ignore[import-not-found]


@pytest.mark.asyncio
async def test_callable_agent_adapter():
    """Verify CallableAgentAdapter wraps Python functions correctly."""
    async def sample_agent_fn(prompt: str, session_id: str = "", model: str = "", **kwargs):
        return {
            "response": f"Processed: {prompt}",
            "tool_calls_executed": [{"tool": "test_tool", "output": "ok"}],
            "total_prompt_tokens": 15,
            "total_completion_tokens": 10
        }

    adapter = CallableAgentAdapter(
        adapter_id="test_callable",
        name="Test Callable Agent",
        agent_fn=sample_agent_fn,
        model="ollama/llama3.2"
    )

    res = await adapter.run("Hello test")
    assert isinstance(res, AgentRunOutput)
    assert res.response == "Processed: Hello test"
    assert len(res.tool_calls_executed) == 1
    assert res.total_prompt_tokens == 15
    assert res.latency_ms >= 0


def test_agent_registry():
    """Verify dynamic registration and lookup in AgentRegistry."""
    registry = AgentRegistry()
    
    # Check default MCP agent is registered
    default_agent = registry.get("mcp_default")
    assert default_agent is not None
    assert default_agent.adapter_id == "mcp_default"

    # Register custom adapter
    custom_adapter = MCPAgentAdapter(
        adapter_id="custom_agent_1",
        name="Custom Agent",
        model="ollama/mistral:latest"
    )
    registry.register(custom_adapter)
    
    retrieved = registry.get("custom_agent_1")
    assert retrieved is not None
    assert retrieved.name == "Custom Agent"

    # List all
    all_adapters = registry.list_all()
    assert any(a["id"] == "custom_agent_1" for a in all_adapters)

    # Unregister
    removed = registry.unregister("custom_agent_1")
    assert removed is not None
    assert registry.get("custom_agent_1") is None


def test_model_registry():
    """Verify ModelRegistry candidate model management."""
    reg = ModelRegistry()
    models = reg.list_all()
    assert len(models) >= 3

    # Register new model
    new_spec = ModelSpec(
        model_id="custom/my-model:7b",
        name="My Custom Model",
        provider="custom"
    )
    reg.register(new_spec)

    found = reg.get("custom/my-model:7b")
    assert found is not None
    assert found.name == "My Custom Model"


def test_judge_registry():
    """Verify JudgeRegistry LLM-as-a-Judge management."""
    reg = JudgeRegistry()
    judges = reg.list_all()
    assert len(judges) >= 2

    # Register custom judge
    new_judge = JudgeSpec(
        judge_id="judge_custom_eval",
        name="Custom Accuracy Judge",
        model="ollama/qwen2.5-coder:7b",
        rubric_description="Focuses on exact numerical outputs."
    )
    reg.register(new_judge)

    found = reg.get("judge_custom_eval")
    assert found is not None
    assert found.model == "ollama/qwen2.5-coder:7b"


def test_history_engine_and_comparison(tmp_path: Path):
    """Verify HistoryEngine lists runs and computes comparative delta matrices."""
    import json
    
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True)

    # Create 2 mock historical JSON runs
    run1 = {
        "run_id": "run_model_qwen",
        "timestamp": "2026-08-16T00:00:00Z",
        "agent_name": "MCP Agent",
        "model": "ollama/qwen2.5-coder:7b",
        "judge_model": "ollama/llama3.2",
        "total_tests": 2,
        "passed_tests": 2,
        "pass_rate_pct": 100.0,
        "average_score_pct": 95.0,
        "avg_latency_ms": 120.5,
        "total_tokens": 800,
        "grader_averages": {
            "deterministic": 98.0,
            "efficiency": 94.0,
            "llm_judge": 96.0,
            "fact_checker": 92.0
        },
        "results": [
            {"id": "test_1", "name": "Math Test", "overall_score": 0.96, "passed": True, "latency_ms": 100},
            {"id": "test_2", "name": "Weather Test", "overall_score": 0.94, "passed": True, "latency_ms": 141}
        ]
    }

    run2 = {
        "run_id": "run_model_llama",
        "timestamp": "2026-08-16T00:05:00Z",
        "agent_name": "MCP Agent",
        "model": "ollama/llama3.2",
        "judge_model": "ollama/llama3.2",
        "total_tests": 2,
        "passed_tests": 1,
        "pass_rate_pct": 50.0,
        "average_score_pct": 72.0,
        "avg_latency_ms": 95.0,
        "total_tokens": 650,
        "grader_averages": {
            "deterministic": 70.0,
            "efficiency": 85.0,
            "llm_judge": 75.0,
            "fact_checker": 60.0
        },
        "results": [
            {"id": "test_1", "name": "Math Test", "overall_score": 0.90, "passed": True, "latency_ms": 90},
            {"id": "test_2", "name": "Weather Test", "overall_score": 0.54, "passed": False, "latency_ms": 100}
        ]
    }

    (reports_dir / "eval_run_run_model_qwen.json").write_text(json.dumps(run1))
    (reports_dir / "eval_run_run_model_llama.json").write_text(json.dumps(run2))

    engine = HistoryEngine(reports_dir=reports_dir)
    runs = engine.list_runs()
    assert len(runs) == 2

    # Compare runs
    comparison = engine.compare_runs(["run_model_qwen", "run_model_llama"])
    assert comparison["total_runs_compared"] == 2
    assert len(comparison["runs"]) == 2
    assert len(comparison["matrix"]) == 2

    # Verify score lookup in matrix
    test1_row = next(row for row in comparison["matrix"] if row["test_id"] == "test_1")
    assert test1_row["scores"]["run_model_qwen"]["passed"] is True
    assert test1_row["scores"]["run_model_llama"]["passed"] is True


@pytest.mark.asyncio
async def test_runner_multi_run_averaging(tmp_path: Path):
    """Verify EvalsRunner runs multiple iterations and averages scores accurately."""
    from evals_framework.runner import EvalsRunner

    run_counts = {"count": 0}

    async def mock_agent_fn(prompt: str, session_id: str = "", **kwargs):
        run_counts["count"] += 1
        # Alternate output to test score averaging across runs
        if run_counts["count"] % 2 == 1:
            return {
                "response": "The temperature in Tokyo is 22°C with clear skies.",
                "tool_calls_executed": [{"tool": "get_weather", "arguments": {"city": "Tokyo"}, "output": "22C"}],
                "total_prompt_tokens": 50,
                "total_completion_tokens": 30
            }
        else:
            return {
                "response": "Tokyo weather is 22 degrees Celsius.",
                "tool_calls_executed": [{"tool": "get_weather", "arguments": {"city": "Tokyo"}, "output": "22C"}],
                "total_prompt_tokens": 40,
                "total_completion_tokens": 20
            }

    custom_adapter = CallableAgentAdapter(
        adapter_id="mock_test_agent",
        name="Mock Test Agent",
        agent_fn=mock_agent_fn
    )

    runner = EvalsRunner(
        agent_adapter=custom_adapter,
        model="mock/test-model",
        reports_dir=tmp_path / "reports"
    )

    # Mock loading a single test case for fast testing
    runner.load_test_cases = lambda categories=None: [{
        "id": "mock_weather_test",
        "name": "Tokyo Weather Lookup",
        "category": "tool_calling",
        "prompt": "What's the weather in Tokyo?",
        "expected_tools": ["get_weather"],
        "expected_keywords": ["Tokyo", "22"]
    }]

    events = []
    async def capture_event(ev):
        events.append(ev)

    # Run 3 iterations
    res = await runner.run_suite(on_event=capture_event, iterations=3)

    assert res["iterations"] == 3
    assert res["is_averaged"] is True
    assert run_counts["count"] == 3

    test_res = res["results"][0]
    assert test_res["id"] == "mock_weather_test"
    assert test_res["total_runs"] == 3
    assert len(test_res["iteration_runs"]) == 3

    # Check composite score is an average
    expected_avg = round(sum(r["composite_score"] for r in test_res["iteration_runs"]) / 3, 2)
    assert test_res["composite_score"] == expected_avg

    # Check start event and complete event included iterations metadata
    start_ev = next(e for e in events if e["type"] == "start")
    assert start_ev["iterations"] == 3
    assert start_ev["is_averaged"] is True

    complete_ev = next(e for e in events if e["type"] == "complete")
    assert complete_ev["iterations"] == 3
    assert complete_ev["is_averaged"] is True


@pytest.mark.asyncio
async def test_progressive_disclosure_eval_flow():
    """Verify that the agent correctly parses and executes progressive skill discovery tools."""
    from ai_agent.agent import AgenticLLMAgent
    from mcp_server.server import tool_discover_skills, tool_load_skill

    # Verify discovery catalog
    raw_catalog = tool_discover_skills()
    assert "travel_planner_skill" in raw_catalog
    assert "code_review_skill" in raw_catalog

    # Verify dynamic load tool
    loaded_raw = tool_load_skill(skill_name="travel_planner_skill", parameters={"destination": "Kyoto"})
    assert "Kyoto" in loaded_raw
    assert "Vacation" in loaded_raw

    # Verify agent state tracking
    agent = AgenticLLMAgent()
    assert len(agent.active_skills) == 0
    # Simulate dynamic load step
    agent.active_skills.append("travel_planner_skill")
    assert "travel_planner_skill" in agent.active_skills


