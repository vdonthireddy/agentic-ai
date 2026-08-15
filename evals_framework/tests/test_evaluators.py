"""Unit tests for Evaluation metric scorers."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluators import (
    evaluate_tool_accuracy,
    evaluate_skill_adherence,
    evaluate_correctness,
    evaluate_performance
)

def test_tool_accuracy_perfect_match():
    tc = {"expected_tools": ["calculate"], "required_args": ["expression"]}
    executed = [{"tool": "calculate", "arguments": {"expression": "2+2"}}]
    
    res = evaluate_tool_accuracy(tc, executed)
    assert res["passed"] is True
    assert res["score"] == 1.0
    assert res["precision"] == 1.0
    assert res["recall"] == 1.0

def test_tool_accuracy_missing_tool():
    tc = {"expected_tools": ["calculate", "execute_python"]}
    executed = [{"tool": "calculate", "arguments": {"expression": "2+2"}}]
    
    res = evaluate_tool_accuracy(tc, executed)
    assert res["recall"] == 0.5
    assert res["score"] < 1.0

def test_skill_adherence():
    tc = {"required_sections": ["Executive Summary", "Statistical Findings", "Recommendations"]}
    response = "# Executive Summary\nRevenue grew.\n## Statistical Findings\nMean: 100.\n## Recommendations\nScale up."
    
    res = evaluate_skill_adherence(tc, response)
    assert res["passed"] is True
    assert res["score"] == 1.0
    assert len(res["missing_sections"]) == 0

def test_correctness():
    tc = {"ground_truth": "41905", "ground_truth_contains": ["prime", "sum"]}
    response = "The result of the multiplication is 41905 and the prime sum is calculated."
    
    res = evaluate_correctness(tc, response, [])
    assert res["passed"] is True
    assert res["score"] == 1.0

def test_performance_evaluation():
    metrics = [
        {"latency_ms": 1000.0, "prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        {"latency_ms": 2000.0, "prompt_tokens": 200, "completion_tokens": 50, "total_tokens": 250}
    ]
    perf = evaluate_performance(metrics)
    assert perf["avg_latency_ms"] == 1500.0
    assert perf["total_prompt_tokens"] == 300
    assert perf["total_completion_tokens"] == 100
    assert perf["total_tokens"] == 400
    assert perf["tokens_per_second"] > 0
