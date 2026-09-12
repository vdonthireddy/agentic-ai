"""Answer Relevance & Conciseness Grader.

Evaluates the model's generated output text for directness, query alignment,
absence of conversational fluff/pleasantries, and high Signal-to-Noise Ratio (SNR).
"""

import re
from typing import Dict, Any, List

FLUFF_PATTERNS = [
    r"^(?:sure|certainly|absolutely|of course|great question|i would be happy to help|thank you for (?:asking|reaching out))[!.,]?\s*",
    r"^(?:as an ai(?: language model)?,?|i am here to help,?)\s*",
    r"(?:hope this helps|let me know if you have any (?:other )?questions|feel free to reach out|have a (?:great|wonderful) day)[!.]?\s*$",
    r"(?:is there anything else (?:i can|you would like me to) (?:help|assist) (?:you )?with\??)\s*$"
]

COMMON_STOP_WORDS = {
    "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
    "this", "that", "these", "those", "is", "are", "was", "were", "be", "been", "being",
    "the", "a", "an", "for", "to", "in", "on", "at", "by", "of", "and", "or", "but",
    "can", "could", "would", "should", "will", "do", "does", "did", "please", "you",
    "your", "me", "my", "we", "our", "it", "its", "with", "from", "as", "about"
}

def grade_answer_relevance(
    test_case: Dict[str, Any],
    assistant_response: str
) -> Dict[str, Any]:
    """
    Grades model output text for relevance, directness, and informational density.
    
    Zero-dependency, offline deterministic execution.
    """
    prompt = test_case.get("prompt", "")
    text = assistant_response.strip()
    if not text:
        return {
            "grader": "answer_relevance",
            "passed": False,
            "score": 0.0,
            "details": {
                "query_alignment_score": 0.0,
                "fluff_ratio": 0.0,
                "violations": ["Response is empty."],
                "critique": "Model output is empty."
            }
        }

    violations: List[str] = []
    fluff_chars = 0

    # 1. Preamble & Postamble Fluff Detection
    for pat in FLUFF_PATTERNS:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            fluff_chars += len(match.group(0))
            violations.append(f"Conversational fluff detected: '{match.group(0).strip()}'")

    fluff_ratio = min(1.0, fluff_chars / max(1, len(text)))

    # 2. Query Entity Alignment (Lexical overlap of meaningful question terms)
    query_tokens = [
        w.lower() for w in re.findall(r"\b[A-Za-z0-9_-]+\b", prompt)
        if w.lower() not in COMMON_STOP_WORDS and len(w) > 2
    ]
    response_tokens = set(w.lower() for w in re.findall(r"\b[A-Za-z0-9_-]+\b", text))

    if query_tokens:
        matched_tokens = [tok for tok in query_tokens if tok in response_tokens]
        alignment_score = len(matched_tokens) / len(query_tokens)
    else:
        alignment_score = 1.0

    # 3. Conciseness / Verbosity Penalty if marked as concise
    verbosity_penalty = 0.0
    if test_case.get("concise_expected", False) or test_case.get("tone") == "concise":
        word_count = len(re.findall(r"\b\w+\b", text))
        if word_count > 60:
            excess = word_count - 60
            verbosity_penalty = min(0.35, 0.10 + (excess * 0.005))
            violations.append(f"Response too verbose for concise query: {word_count} words")

    # 4. Composite Score
    base_score = (0.60 * alignment_score) + (0.40 * (1.0 - fluff_ratio)) - verbosity_penalty
    final_score = max(0.0, round(min(1.0, base_score), 3))
    passed = final_score >= 0.70 and alignment_score >= 0.40

    return {
        "grader": "answer_relevance",
        "passed": passed,
        "score": final_score,
        "details": {
            "query_alignment_score": round(alignment_score, 3),
            "fluff_ratio": round(fluff_ratio, 3),
            "violations": violations,
            "matched_query_terms": list(set(query_tokens).intersection(response_tokens)),
            "missing_query_terms": list(set(query_tokens) - response_tokens),
            "critique": "Direct, relevant, and concise answer." if passed else f"Relevance issues: {'; '.join(violations) if violations else 'Low query alignment'}"
        }
    }
