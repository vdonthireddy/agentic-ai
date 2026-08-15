"""Evaluator for factual, numerical, and logic correctness against ground truth."""

from typing import List, Dict, Any

def evaluate_correctness(
    test_case: Dict[str, Any],
    response_text: str,
    executed_tools: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Checks if the expected numerical or factual ground-truth answers appear in final answer or tool outputs.
    """
    ground_truth = test_case.get("ground_truth")
    ground_truth_contains = test_case.get("ground_truth_contains", [])
    
    if not ground_truth and not ground_truth_contains:
        return {"score": 1.0, "passed": True, "details": "No ground truth assertions defined."}

    # Aggregate text from response and tool outputs
    corpus = response_text
    for t in executed_tools:
        corpus += "\n" + str(t.get("output", ""))

    corpus_lower = corpus.lower()
    matches = 0
    total_checks = 0

    if ground_truth:
        total_checks += 1
        if str(ground_truth).lower() in corpus_lower:
            matches += 1

    for gt in ground_truth_contains:
        total_checks += 1
        if str(gt).lower() in corpus_lower:
            matches += 1

    score = (matches / total_checks) if total_checks > 0 else 1.0

    return {
        "score": round(score, 2),
        "passed": score >= 0.9,
        "ground_truth_target": ground_truth or ground_truth_contains,
        "matches": matches,
        "total_checks": total_checks
    }
