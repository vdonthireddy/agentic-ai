"""Evaluator for Skill Prompt compliance and structured output adherence."""

from typing import List, Dict, Any

def evaluate_skill_adherence(
    test_case: Dict[str, Any],
    response_text: str
) -> Dict[str, Any]:
    """
    Evaluates whether the agent adhered to required structure and criteria specified by the Skill.
    """
    required_sections = test_case.get("required_sections", [])
    if not required_sections:
        return {"score": 1.0, "passed": True, "details": "No required sections specified."}

    text_lower = response_text.lower()
    matched_sections = []
    missing_sections = []

    for sec in required_sections:
        # Check if section title exists in response
        sec_clean = sec.lower().replace("&", "").strip()
        words = sec_clean.split()
        if all(w in text_lower for w in words):
            matched_sections.append(sec)
        else:
            missing_sections.append(sec)

    score = len(matched_sections) / len(required_sections) if required_sections else 1.0

    return {
        "score": round(score, 2),
        "passed": score >= 0.65,
        "matched_sections": matched_sections,
        "missing_sections": missing_sections
    }
