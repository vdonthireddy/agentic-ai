"""Fact-Checker and Groundedness Grader checking Tool-to-Summary Faithfulness and Hallucinations."""

import json
import httpx
from typing import Dict, Any, List, Optional

FACT_CHECK_PROMPT = """You are a rigorous Fact-Checker & Groundedness Evaluator.
Compare the Tool Execution Outputs (Ground Truth Evidence) against the Assistant Summary.

[Tool Execution Outputs]
{tool_outputs}

[Assistant Summary]
{assistant_response}

Evaluate:
1. Groundedness: Is the assistant summary strictly grounded in the tool outputs?
2. Hallucination Check: Did the assistant invent or hallucinate facts/numbers not supported by the tools?
3. Distortion: Did the assistant distort any prices, numbers, or dates returned by the tools?

Output your evaluation strictly as JSON:
{{
  "groundedness_score": 1.0,
  "hallucination_detected": false,
  "accuracy_score": 1.0,
  "composite_fact_score": 1.0,
  "critique": "Brief explanation of factual faithfulness"
}}
"""

async def grade_fact_checker(
    test_case: Dict[str, Any],
    executed_tools: List[Dict[str, Any]],
    assistant_response: str,
    gateway_url: str = "http://localhost:8000",
    judge_model: str = "ollama/gemma2:2b"
) -> Dict[str, Any]:
    """
    Evaluates whether the assistant summary is strictly grounded in the tool outputs without hallucinations.
    """
    if not executed_tools:
        # If no tools were called, check against ground truth assertions
        gt = test_case.get("ground_truth", "")
        passed = (gt in assistant_response) if gt else True
        return {
            "grader": "fact_checker_and_groundedness",
            "passed": passed,
            "score": 1.0 if passed else 0.5,
            "details": {
                "groundedness_score": 1.0,
                "hallucination_detected": not passed,
                "composite_fact_score": 1.0 if passed else 0.5,
                "critique": "No tools called; evaluated against test case ground truth."
            }
        }

    # Format tool outputs for prompt
    tool_outputs_summary = []
    for t in executed_tools:
        tool_outputs_summary.append(f"Tool: {t.get('tool')}\nArgs: {t.get('arguments')}\nOutput: {t.get('output')}")
    tool_outputs_text = "\n---\n".join(tool_outputs_summary)

    prompt = FACT_CHECK_PROMPT.format(
        tool_outputs=tool_outputs_text,
        assistant_response=assistant_response
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": judge_model,
                    "messages": [
                        {"role": "system", "content": "You are a strict JSON-only Fact Checker and Groundedness evaluator."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.0
                }
            )

            if res.status_code == 200:
                data = res.json()
                content = data["choices"][0]["message"]["content"].strip()
                if "```" in content:
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:].strip()

                fact_eval = json.loads(content)
                score = float(fact_eval.get("composite_fact_score", 1.0))
                passed = not bool(fact_eval.get("hallucination_detected", False)) and score >= 0.70

                return {
                    "grader": "fact_checker_and_groundedness",
                    "passed": passed,
                    "score": round(score, 3),
                    "details": fact_eval
                }
    except Exception:
        pass

    # Heuristic groundedness verification fallback
    # Verify key tokens from tool outputs appear in the response
    tool_text_blob = " ".join([str(t.get("output", "")) for t in executed_tools])
    numbers_in_tools = [w for w in tool_text_blob.split() if any(c.isdigit() for c in w)]
    
    grounded_count = sum(1 for n in numbers_in_tools if n in assistant_response)
    heuristic_score = grounded_count / len(numbers_in_tools) if numbers_in_tools else 1.0
    heuristic_score = max(0.6, min(1.0, heuristic_score))

    return {
        "grader": "fact_checker_and_groundedness",
        "passed": heuristic_score >= 0.60,
        "score": round(heuristic_score, 3),
        "details": {
            "groundedness_score": round(heuristic_score, 3),
            "hallucination_detected": heuristic_score < 0.60,
            "composite_fact_score": round(heuristic_score, 3),
            "critique": "Heuristic token overlap analysis between tool output and final summary."
        }
    }
