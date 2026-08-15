"""Performance and latency benchmark evaluator."""

from typing import List, Dict, Any
import statistics

def evaluate_performance(metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes summary latency, token counts, and throughput.
    """
    if not metrics_list:
        return {}

    latencies = [m.get("latency_ms", 0.0) for m in metrics_list]
    prompt_tokens = [m.get("prompt_tokens", 0) for m in metrics_list]
    completion_tokens = [m.get("completion_tokens", 0) for m in metrics_list]
    total_tokens = [m.get("total_tokens", 0) for m in metrics_list]

    avg_latency = statistics.mean(latencies) if latencies else 0.0
    p50_latency = statistics.median(latencies) if latencies else 0.0
    p95_latency = statistics.quantiles(latencies, n=20)[-1] if len(latencies) >= 20 else max(latencies or [0.0])

    tot_comp_tokens = sum(completion_tokens)
    tot_latency_sec = sum(latencies) / 1000.0
    tokens_per_second = round(tot_comp_tokens / tot_latency_sec, 2) if tot_latency_sec > 0 else 0.0

    return {
        "avg_latency_ms": round(avg_latency, 2),
        "p50_latency_ms": round(p50_latency, 2),
        "p95_latency_ms": round(p95_latency, 2),
        "total_prompt_tokens": sum(prompt_tokens),
        "total_completion_tokens": tot_comp_tokens,
        "total_tokens": sum(total_tokens),
        "tokens_per_second": tokens_per_second
    }
