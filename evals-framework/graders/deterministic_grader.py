"""Deterministic Grader for Tool Calling Order, Argument Schema, and Keyword Assertions."""

import re
from typing import Dict, Any, List, Optional

def grade_deterministic(
    test_case: Dict[str, Any],
    executed_tools: List[Dict[str, Any]],
    assistant_response: str
) -> Dict[str, Any]:
    """
    Evaluates:
    1. Tool presence, precision, and recall.
    2. Tool invocation sequential order.
    3. Tool argument schema and exact argument value assertions.
    4. Keyword and regex substring matches in final response.
    5. Section header compliance for active domain skills.
    """
    expected_tools = test_case.get("expected_tools", [])
    expected_order = test_case.get("expected_tool_order", [])
    required_args = test_case.get("required_args", [])
    expected_args_values = test_case.get("expected_args_values", {})
    ground_truth = str(test_case.get("ground_truth", "")).strip()
    ground_truth_contains = test_case.get("ground_truth_contains", [])
    required_sections = test_case.get("required_sections", [])

    called_tool_names = [t.get("tool") for t in executed_tools if t.get("tool")]

    # 1. Tool Presence (Precision & Recall)
    if expected_tools:
        matched_tools = set(called_tool_names).intersection(set(expected_tools))
        precision = len(matched_tools) / len(called_tool_names) if called_tool_names else 0.0
        recall = len(matched_tools) / len(expected_tools)
        tool_presence_score = (precision + recall) / 2.0 if (precision + recall) > 0 else 0.0
    else:
        tool_presence_score = 1.0
        precision = 1.0
        recall = 1.0

    # 2. Tool Execution Order
    order_passed = True
    order_score = 1.0
    if expected_order:
        # Filter called tools to only those in expected_order
        relevant_calls = [name for name in called_tool_names if name in expected_order]
        if relevant_calls[:len(expected_order)] == expected_order:
            order_score = 1.0
            order_passed = True
        else:
            order_passed = False
            # Partial match calculation
            correct_positions = sum(1 for i, name in enumerate(relevant_calls) if i < len(expected_order) and name == expected_order[i])
            order_score = correct_positions / len(expected_order) if expected_order else 0.0

    # 3. Argument Schema & Exact Value Matching
    arg_score = 1.0
    missing_args = []
    mismatched_arg_values = []
    
    if executed_tools and (required_args or expected_args_values):
        total_arg_checks = 0
        passed_arg_checks = 0
        
        for tool_call in executed_tools:
            args = tool_call.get("arguments", {})
            if isinstance(args, str):
                try:
                    import json
                    args = json.loads(args)
                except Exception:
                    args = {}
                    
            for req in required_args:
                total_arg_checks += 1
                if req in args:
                    passed_arg_checks += 1
                else:
                    missing_args.append(req)
                    
            for key, expected_val in expected_args_values.items():
                total_arg_checks += 1
                actual_val = str(args.get(key, "")).lower()
                if str(expected_val).lower() in actual_val:
                    passed_arg_checks += 1
                else:
                    mismatched_arg_values.append(f"{key}: expected '{expected_val}', got '{actual_val}'")
                    
        if total_arg_checks > 0:
            arg_score = passed_arg_checks / total_arg_checks

    # 4. Keyword & Substring Matching
    keyword_score = 1.0
    missing_keywords = []
    
    if ground_truth and ground_truth not in assistant_response:
        # Check normalized float or integer match
        try:
            gt_num = float(ground_truth)
            numbers_in_resp = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", assistant_response)]
            if not any(abs(n - gt_num) < 0.01 for n in numbers_in_resp):
                missing_keywords.append(ground_truth)
                keyword_score -= 0.5
        except ValueError:
            missing_keywords.append(ground_truth)
            keyword_score -= 0.5

    if ground_truth_contains:
        for kw in ground_truth_contains:
            if kw.lower() not in assistant_response.lower():
                missing_keywords.append(kw)
        keyword_score = (len(ground_truth_contains) - len(missing_keywords)) / len(ground_truth_contains) if ground_truth_contains else 1.0

    keyword_score = max(0.0, min(1.0, keyword_score))

    # 5. Section Header Compliance
    section_score = 1.0
    missing_sections = []
    if required_sections:
        for sec in required_sections:
            pattern = re.compile(rf"(#+|\*\*|__)?\s*{re.escape(sec)}", re.IGNORECASE)
            if not pattern.search(assistant_response):
                missing_sections.append(sec)
        section_score = (len(required_sections) - len(missing_sections)) / len(required_sections)

    # Composite Deterministic Score
    composite_deterministic = (
        (tool_presence_score * 0.25) +
        (order_score * 0.20) +
        (arg_score * 0.20) +
        (keyword_score * 0.20) +
        (section_score * 0.15)
    )

    passed = (
        composite_deterministic >= 0.70 and
        (len(missing_keywords) == 0 if ground_truth else True) and
        order_passed
    )

    return {
        "grader": "deterministic",
        "passed": passed,
        "score": round(composite_deterministic, 3),
        "details": {
            "tool_presence_score": round(tool_presence_score, 3),
            "order_score": round(order_score, 3),
            "order_passed": order_passed,
            "arg_score": round(arg_score, 3),
            "missing_args": missing_args,
            "mismatched_arg_values": mismatched_arg_values,
            "keyword_score": round(keyword_score, 3),
            "missing_keywords": missing_keywords,
            "section_score": round(section_score, 3),
            "missing_sections": missing_sections
        }
    }
