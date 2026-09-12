import pytest
from evals_framework.runner import EvalsRunner

def test_load_test_cases():
    runner = EvalsRunner()
    tests = runner.load_test_cases()
    assert len(tests) >= 6
    assert tests[0]["id"] == "multi_turn_eval_001"
    assert "expected_tools" in tests[0]

def test_load_test_cases_category_filter():
    runner = EvalsRunner()
    tests = runner.load_test_cases(categories=["reasoning"])
    assert len(tests) >= 2
    for t in tests:
        assert t["category"] == "reasoning"
        
def test_load_multi_turn_test_cases():
    runner = EvalsRunner()
    tests = runner.load_test_cases(categories=["reasoning"])
    multi_turn_tests = [t for t in tests if "turns" in t and len(t["turns"]) > 1]
    assert len(multi_turn_tests) >= 2
    for t in multi_turn_tests:
        assert isinstance(t["turns"], list)
        assert len(t["turns"]) >= 2
