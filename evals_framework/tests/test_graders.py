"""Unit tests for the 4 Evaluation Graders in evals-framework."""

import pytest
from graders.deterministic_grader import grade_deterministic
from graders.efficiency_grader import grade_cost_and_efficiency
from graders.llm_judge_grader import grade_llm_judge
from graders.fact_checker_grader import grade_fact_checker

def test_deterministic_grader_success():
    test_case = {
        "id": "test_weather_math",
        "expected_tools": ["weather", "calculator"],
        "expected_tool_order": ["weather", "calculator"],
        "ground_truth_contains": ["72°F", "Paris", "$46.12"],
        "required_sections": ["Weather", "Bill Split"]
    }
    executed_tools = [
        {"tool": "weather", "arguments": {"location": "Paris"}},
        {"tool": "calculator", "arguments": {"expression": "184.5 / 4"}}
    ]
    response = "## Weather\nIt is 72°F in Paris.\n\n## Bill Split\nEach person pays $46.12."

    result = grade_deterministic(test_case, executed_tools, response)
    assert result["passed"] is True
    assert result["score"] >= 0.85
    assert result["details"]["order_passed"] is True
    assert len(result["details"]["missing_keywords"]) == 0

def test_deterministic_grader_out_of_order_penalty():
    test_case = {
        "id": "test_order",
        "expected_tools": ["weather", "calculator"],
        "expected_tool_order": ["weather", "calculator"]
    }
    # Called in reverse order
    executed_tools = [
        {"tool": "calculator", "arguments": {}},
        {"tool": "weather", "arguments": {}}
    ]
    response = "Done"

    result = grade_deterministic(test_case, executed_tools, response)
    assert result["details"]["order_passed"] is False

def test_efficiency_grader_under_budget():
    test_case = {
        "max_total_tokens": 2000,
        "max_completion_tokens": 500,
        "max_tool_calls_budget": 3,
        "latency_sla_ms": 5000.0
    }
    executed_tools = [
        {"tool": "weather", "arguments": {"location": "Tokyo"}}
    ]
    tokens_used = {"prompt_tokens": 400, "completion_tokens": 60, "total_tokens": 460}
    latency_ms = 1200.0

    result = grade_cost_and_efficiency(test_case, executed_tools, tokens_used, latency_ms)
    assert result["passed"] is True
    assert result["score"] >= 0.90
    assert result["details"]["duplicate_calls"] == 0

def test_efficiency_grader_duplicate_loop_penalty():
    test_case = {
        "max_total_tokens": 2000,
        "max_tool_calls_budget": 2
    }
    executed_tools = [
        {"tool": "calculator", "arguments": {"expression": "2+2"}},
        {"tool": "calculator", "arguments": {"expression": "2+2"}},
        {"tool": "calculator", "arguments": {"expression": "2+2"}}
    ]
    tokens_used = {"prompt_tokens": 3000, "completion_tokens": 800, "total_tokens": 3800}
    latency_ms = 8000.0

    result = grade_cost_and_efficiency(test_case, executed_tools, tokens_used, latency_ms)
    assert result["details"]["duplicate_calls"] == 2
    assert result["score"] < 0.70

@pytest.mark.asyncio
async def test_llm_judge_safe_and_helpful():
    test_case = {"prompt": "Give me packing tips for a rainy day in Seattle."}
    response = "Bring a waterproof rain jacket, a sturdy travel umbrella, and water-resistant walking shoes."

    result = await grade_llm_judge(test_case, response)
    assert result["passed"] is True
    assert result["score"] >= 0.70
    assert result["details"]["safe"] is True

@pytest.mark.asyncio
async def test_fact_checker_grounded_response():
    test_case = {"prompt": "What is the weather in Paris?"}
    executed_tools = [
        {"tool": "weather", "arguments": {"location": "Paris"}, "output": '{"temperature_f": 68, "condition": "Partly Cloudy"}'}
    ]
    response = "The weather in Paris is currently 68°F and Partly Cloudy."

    result = await grade_fact_checker(test_case, executed_tools, response)
    assert result["passed"] is True
    assert result["score"] >= 0.60
    assert result["details"]["hallucination_detected"] is False
