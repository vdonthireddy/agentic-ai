"""Unit tests for datasets and report generation in evals-framework."""

import pytest
import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runner import EvalsRunner
from reporters import generate_markdown_report

def test_load_test_cases():
    runner = EvalsRunner()
    tests = runner.load_test_cases()
    assert len(tests) >= 8
    
    # Verify required schema fields
    for t in tests:
        assert "id" in t
        assert "name" in t
        assert "prompt" in t
        assert "category" in t

def test_generate_markdown_report():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_results = [
            {
                "id": "eval_1", "name": "Test Math", "category": "tool_calling",
                "tool_score": 1.0, "skill_score": 1.0, "correctness_score": 1.0,
                "composite_score": 1.0, "overall_passed": True,
                "prompt": "2+2", "executed_tools": ["calculate"], "response_snippet": "4"
            }
        ]
        perf = {"total_prompt_tokens": 50, "total_completion_tokens": 10, "total_tokens": 60, "avg_latency_ms": 500.0}
        
        report_file = generate_markdown_report(
            model_name="ollama/qwen2.5-coder:7b",
            test_results=test_results,
            performance_metrics=perf,
            output_dir=tmpdir
        )
        assert Path(report_file).exists()
        content = Path(report_file).read_text()
        assert "LLM Evaluation Benchmark Report" in content
        assert "Test Math" in content
