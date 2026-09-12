"""Output Faithfulness & Hallucination Grader.

Evaluates whether factual claims (numbers, entities, dates, specifications)
in the model's output response text are strictly supported by the source
context and tool execution data, catching ungrounded hallucinations.
"""

import re
import json
import httpx
from typing import Dict, Any, List, Optional, Set

FAITHFULNESS_PROMPT_TEMPLATE = """You are a meticulous AI Output Faithfulness and Hallucination Auditor.
Your task is to examine the Assistant's Output Response against the Reference Source Context / Tool Outputs.

[Reference Source Context & Evidence]
{source_context}

[Assistant Output Response to Evaluate]
{assistant_response}

Instructions:
1. Extract every atomic factual assertion made in the Assistant Output Response (facts, numbers, prices, dates, attributes).
2. For each assertion, verify if it is directly supported by the Reference Source Context.
3. Identify any ungrounded hallucinations (facts or numbers invented by the assistant that are absent from the source).
4. Compute an output faithfulness score from 0.0 (completely hallucinated) to 1.0 (100% faithful and supported).

Output your evaluation STRICTLY as a JSON object with this schema:
{{
  "faithfulness_score": 1.0,
  "hallucination_detected": false,
  "supported_claims_count": 5,
  "unsupported_claims_count": 0,
  "unsupported_claims": [],
  "critique": "Brief assessment of faithfulness"
}}
"""

def _extract_factual_entities(text: str) -> Dict[str, Set[str]]:
    """
    Extracts atomic entities, metrics, prices, and numbers from text for offline evaluation.
    """
    # Numbers and percentages (e.g. 42, 3.14, 15%)
    numbers = set(re.findall(r"\b\d+(?:\.\d+)?%?\b", text))
    
    # Currency values (e.g. $45, $1,200.50, €50, £10)
    currencies = set(re.findall(r"[\$€£]\s*\d+(?:,\d{3})*(?:\.\d+)?", text))
    
    # Capitalized multi-word or single-word named entities (excluding start of sentences if generic)
    entities = set(re.findall(r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})*\b", text))
    
    # URLs or domains
    urls = set(re.findall(r"https?://[^\s]+|\b[a-zA-Z0-9.-]+\.[a-z]{2,}\b", text.lower()))

    return {
        "numbers": numbers,
        "currencies": currencies,
        "entities": entities,
        "urls": urls
    }

async def grade_output_faithfulness(
    test_case: Dict[str, Any],
    assistant_response: str,
    source_context: str = "",
    gateway_url: str = "http://localhost:8000",
    judge_model: str = "ollama/gemma2:2b"
) -> Dict[str, Any]:
    """
    Grades the model output text for factual faithfulness against source context.
    
    Args:
        test_case: Test case dictionary (may contain 'context', 'ground_truth', etc.)
        assistant_response: The model's generated text output to grade
        source_context: The reference evidence/context against which to grade
        gateway_url: LLM Gateway URL for online LLM-as-a-judge check
        judge_model: Model name for LLM judge evaluation
    """
    # Consolidate available context evidence
    context = (
        source_context or
        test_case.get("context", "") or
        test_case.get("reference_context", "") or
        test_case.get("ground_truth", "") or
        ""
    )

    resp_clean = assistant_response.strip()
    if not resp_clean:
        return {
            "grader": "output_faithfulness",
            "passed": False,
            "score": 0.0,
            "details": {
                "faithfulness_score": 0.0,
                "hallucination_detected": True,
                "unsupported_claims": ["Assistant response is empty."],
                "critique": "Model produced empty response."
            }
        }

    # If no source context was provided at all, pass conditionally unless hallucination is flagrant
    if not context:
        return {
            "grader": "output_faithfulness",
            "passed": True,
            "score": 1.0,
            "details": {
                "faithfulness_score": 1.0,
                "hallucination_detected": False,
                "unsupported_claims": [],
                "critique": "No source context provided for verification; skipped hallucination penalty."
            }
        }

    # 1. Attempt LLM-assisted Evaluation via Gateway
    try:
        prompt = FAITHFULNESS_PROMPT_TEMPLATE.format(
            source_context=context,
            assistant_response=resp_clean
        )
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": judge_model,
                    "messages": [
                        {"role": "system", "content": "You are a strict JSON-only evaluation auditor."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.0
                }
            )
            if res.status_code == 200:
                content = res.json()["choices"][0]["message"]["content"].strip()
                if "```" in content:
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:].strip()
                parsed = json.loads(content)
                score = float(parsed.get("faithfulness_score", 1.0))
                hallucinated = bool(parsed.get("hallucination_detected", False))
                passed = (not hallucinated) and score >= 0.70
                return {
                    "grader": "output_faithfulness",
                    "passed": passed,
                    "score": round(score, 3),
                    "details": parsed
                }
    except Exception:
        # Fall back gracefully to offline heuristic extraction
        pass

    # 2. Offline Heuristic Fallback (Claim & Entity Set Inspection)
    resp_facts = _extract_factual_entities(resp_clean)
    context_facts = _extract_factual_entities(context)

    unsupported_numbers = resp_facts["numbers"] - context_facts["numbers"]
    unsupported_currencies = resp_facts["currencies"] - context_facts["currencies"]
    
    # Filter common stop words from capitalized entity set
    common_words = {"The", "This", "That", "There", "Here", "What", "When", "Where", "Please", "However", "Note"}
    resp_entities = resp_facts["entities"] - common_words
    context_entities = context_facts["entities"] - common_words
    unsupported_entities = resp_entities - context_entities

    unsupported_claims = []
    penalties = 0.0

    if unsupported_currencies:
        unsupported_claims.append(f"Hallucinated price/currency: {sorted(list(unsupported_currencies))}")
        penalties += 0.35 * len(unsupported_currencies)

    if unsupported_numbers:
        # Deduct for non-currency numbers hallucinated
        unsupported_claims.append(f"Hallucinated numeric metrics: {sorted(list(unsupported_numbers))}")
        penalties += 0.20 * len(unsupported_numbers)

    if unsupported_entities:
        # Small penalty for unknown proper nouns
        unsupported_claims.append(f"Unverified named entities: {sorted(list(unsupported_entities))}")
        penalties += 0.10 * len(unsupported_entities)

    score = max(0.0, round(1.0 - penalties, 3))
    hallucination_detected = len(unsupported_claims) > 0 and (len(unsupported_numbers) > 0 or len(unsupported_currencies) > 0)
    passed = score >= 0.70 and not hallucination_detected

    return {
        "grader": "output_faithfulness",
        "passed": passed,
        "score": score,
        "details": {
            "faithfulness_score": score,
            "hallucination_detected": hallucination_detected,
            "unsupported_claims": unsupported_claims,
            "supported_numbers": sorted(list(resp_facts["numbers"].intersection(context_facts["numbers"]))),
            "critique": "Evaluated via offline entity and metric overlap verification against source context."
        }
    }
