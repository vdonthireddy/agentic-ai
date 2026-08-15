"""Evaluator for tool calling accuracy and argument validity."""

from typing import List, Dict, Any

def evaluate_tool_accuracy(
    test_case: Dict[str, Any],
    executed_tools: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Scores tool selection and argument correctness.
    Score = 1.0 if all expected tools are called with valid arguments.
    """
    expected_tools = set(test_case.get("expected_tools", []))
    if not expected_tools:
        return {"score": 1.0, "details": "No tools required for this test case."}

    actual_tool_names = [t.get("tool") for t in executed_tools]
    actual_tool_set = set(actual_tool_names)

    # Intersection of expected vs actual
    matched_tools = expected_tools.intersection(actual_tool_set)
    precision = len(matched_tools) / len(actual_tool_set) if actual_tool_set else 0.0
    recall = len(matched_tools) / len(expected_tools)

    # Argument validation
    valid_args = True
    arg_errors = []
    required_args = test_case.get("required_args", [])
    
    if required_args and executed_tools:
        for tool_call in executed_tools:
            tool_name = tool_call.get("tool")
            args = tool_call.get("arguments", {})
            if tool_name in expected_tools:
                # check if any of the required args or aliases exist
                has_any_arg = any(k in args for k in required_args) if isinstance(args, dict) else False
                if not has_any_arg and required_args:
                    valid_args = False
                    arg_errors.append(f"Tool {tool_name} missing required argument from {required_args}")

    # Compute F1/Accuracy composite score
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    if not valid_args:
        f1 *= 0.5

    return {
        "score": round(f1, 2),
        "passed": f1 >= 0.75,
        "expected": list(expected_tools),
        "actual": actual_tool_names,
        "precision": round(precision, 2),
        "recall": round(recall, 2),
        "arg_errors": arg_errors
    }
