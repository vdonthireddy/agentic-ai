"""Cost and Efficiency Grader evaluating Token Budgets, Tool Call Overhead, and Latency SLAs."""

from typing import Dict, Any, List

def grade_cost_and_efficiency(
    test_case: Dict[str, Any],
    executed_tools: List[Dict[str, Any]],
    tokens_used: Dict[str, int],
    latency_ms: float
) -> Dict[str, Any]:
    """
    Evaluates:
    1. Token Budget Compliance: Are prompt and completion tokens within budget limits?
    2. Tool Overhead & Redundancy: Are there unnecessary repeat calls or infinite loop iterations?
    3. Latency SLA: Did the response finish within the target duration?
    """
    # Default SLA thresholds
    max_total_tokens = test_case.get("max_total_tokens", 3500)
    max_completion_tokens = test_case.get("max_completion_tokens", 800)
    max_tool_calls = test_case.get("max_tool_calls_budget", 4)
    latency_sla_ms = test_case.get("latency_sla_ms", 15000.0)

    total_tokens = tokens_used.get("total_tokens", 0)
    completion_tokens = tokens_used.get("completion_tokens", 0)
    tool_call_count = len(executed_tools)

    # 1. Token Budget Score
    token_score = 1.0
    if total_tokens > max_total_tokens:
        overage = (total_tokens - max_total_tokens) / max_total_tokens
        token_score -= min(0.6, overage * 0.5)
    if completion_tokens > max_completion_tokens:
        token_score -= 0.2
    token_score = max(0.0, token_score)

    # 2. Tool Loop & Redundancy Check
    tool_efficiency_score = 1.0
    duplicate_calls = 0
    seen_calls = set()
    for t in executed_tools:
        call_sig = f"{t.get('tool')}:{str(t.get('arguments'))}"
        if call_sig in seen_calls:
            duplicate_calls += 1
        seen_calls.add(call_sig)

    if duplicate_calls > 0:
        tool_efficiency_score -= (duplicate_calls * 0.25)
    if tool_call_count > max_tool_calls:
        tool_efficiency_score -= ((tool_call_count - max_tool_calls) * 0.15)
    tool_efficiency_score = max(0.0, tool_efficiency_score)

    # 3. Latency SLA Score
    latency_score = 1.0
    if latency_ms > latency_sla_ms:
        latency_overage = (latency_ms - latency_sla_ms) / latency_sla_ms
        latency_score -= min(0.5, latency_overage * 0.3)
    latency_score = max(0.0, latency_score)

    # Composite Efficiency Score
    composite_efficiency = (
        (token_score * 0.45) +
        (tool_efficiency_score * 0.35) +
        (latency_score * 0.20)
    )

    passed = composite_efficiency >= 0.70 and duplicate_calls <= 1

    return {
        "grader": "cost_and_efficiency",
        "passed": passed,
        "score": round(composite_efficiency, 3),
        "details": {
            "token_score": round(token_score, 3),
            "total_tokens_used": total_tokens,
            "max_tokens_budget": max_total_tokens,
            "tool_efficiency_score": round(tool_efficiency_score, 3),
            "tool_call_count": tool_call_count,
            "duplicate_calls": duplicate_calls,
            "latency_score": round(latency_score, 3),
            "latency_ms": round(latency_ms, 1),
            "latency_sla_ms": latency_sla_ms
        }
    }
