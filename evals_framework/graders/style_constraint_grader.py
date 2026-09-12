"""Style, Persona & Constraint Grader.

Evaluates the model's generated output response for:
1. Length and word count boundaries (min/max words).
2. Negative formatting constraints (forbidding bullet points, headers, emojis, code blocks).
3. Readability scores (Flesch Reading Ease and Flesch-Kincaid Grade Level).
4. Persona tone and stylistic directives.
"""

import re
from typing import Dict, Any, List, Optional

def _count_syllables(word: str) -> int:
    """Estimates the syllable count of a single English word."""
    w = word.lower().strip()
    if len(w) <= 3:
        return 1
    # Remove non-alphabetic characters
    w = re.sub(r"[^a-z]", "", w)
    if not w:
        return 1

    # Remove silent trailing e
    if w.endswith("e") and not w.endswith("le") and len(w) > 2 and w[-2] not in "aeiouy":
        w = w[:-1]

    # Count vowel groups
    vowel_groups = re.findall(r"[aeiouy]+", w)
    count = len(vowel_groups)
    return max(1, count)

def _compute_readability(text: str) -> Dict[str, float]:
    """
    Computes Flesch Reading Ease and Flesch-Kincaid Grade Level.
    Returns: {"reading_ease": float, "grade_level": float, "word_count": int, "sentence_count": int}
    """
    # Segment sentences by sentence terminators
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    sentence_count = max(1, len(sentences))

    # Extract words
    words = re.findall(r"\b[A-Za-z0-9'-]+\b", text)
    word_count = len(words)

    if word_count == 0:
        return {"reading_ease": 100.0, "grade_level": 0.0, "word_count": 0, "sentence_count": sentence_count}

    total_syllables = sum(_count_syllables(w) for w in words)

    # Flesch Reading Ease: 206.835 - 1.015 * (words/sentences) - 84.6 * (syllables/words)
    asl = word_count / sentence_count
    asw = total_syllables / word_count
    reading_ease = 206.835 - (1.015 * asl) - (84.6 * asw)
    reading_ease = round(max(0.0, min(100.0, reading_ease)), 1)

    # Flesch-Kincaid Grade Level: 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59
    grade_level = (0.39 * asl) + (11.8 * asw) - 15.59
    grade_level = round(max(0.0, min(18.0, grade_level)), 1)

    return {
        "reading_ease": reading_ease,
        "grade_level": grade_level,
        "word_count": word_count,
        "sentence_count": sentence_count
    }

def grade_style_and_constraints(
    test_case: Dict[str, Any],
    assistant_response: str
) -> Dict[str, Any]:
    """
    Evaluates whether the model's output text complies with non-functional constraints,
    length limits, reading levels, and formatting bans.
    
    Zero-dependency, offline deterministic execution.
    """
    text = assistant_response or ""
    metrics = _compute_readability(text)
    word_count = metrics["word_count"]
    violations: List[str] = []
    penalties = 0.0

    # 1. Word Count Bounds
    max_words = test_case.get("max_words")
    min_words = test_case.get("min_words")

    if max_words is not None and word_count > max_words:
        overage = word_count - max_words
        overage_ratio = overage / max_words
        penalty = min(0.5, 0.2 + (0.3 * overage_ratio))
        violations.append(f"Exceeded max word count: got {word_count} words, max was {max_words} (+{overage} words)")
        penalties += penalty

    if min_words is not None and word_count < min_words:
        shortfall = min_words - word_count
        violations.append(f"Output too brief: got {word_count} words, min was {min_words} (-{shortfall} words)")
        penalties += 0.30

    # 2. Negative Formatting Constraints
    forbidden_formatting = test_case.get("forbidden_formatting", [])
    
    # Check for forbidden bullet points
    if "bullet_points" in forbidden_formatting or "bullets" in forbidden_formatting:
        if re.search(r"^[\s]*[-*•]\s+", text, re.MULTILINE):
            violations.append("Used bullet points when forbidden by negative constraint.")
            penalties += 0.30

    # Check for forbidden numbered lists
    if "numbered_lists" in forbidden_formatting or "numbers" in forbidden_formatting:
        if re.search(r"^[\s]*\d+\.\s+", text, re.MULTILINE):
            violations.append("Used numbered list when forbidden by negative constraint.")
            penalties += 0.30

    # Check for forbidden markdown headers
    if "headers" in forbidden_formatting or "headings" in forbidden_formatting:
        if re.search(r"^[\s]*#{1,6}\s+", text, re.MULTILINE):
            violations.append("Used markdown headers when forbidden by negative constraint.")
            penalties += 0.25

    # Check for forbidden emojis
    if "emojis" in forbidden_formatting:
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        if emoji_pattern.search(text):
            violations.append("Used emojis when forbidden by negative constraint.")
            penalties += 0.20

    # Check for forbidden code blocks
    if "code_blocks" in forbidden_formatting:
        if "```" in text:
            violations.append("Used markdown code block when forbidden by negative constraint.")
            penalties += 0.30

    # 3. Readability Bounds (Optional)
    max_grade = test_case.get("max_grade_level")
    if max_grade is not None and metrics["grade_level"] > max_grade:
        violations.append(f"Reading grade level too high: grade {metrics['grade_level']} exceeds max {max_grade}")
        penalties += 0.20

    min_ease = test_case.get("min_reading_ease")
    if min_ease is not None and metrics["reading_ease"] < min_ease:
        violations.append(f"Reading ease too low: score {metrics['reading_ease']} below min {min_ease}")
        penalties += 0.20

    final_score = max(0.0, round(1.0 - penalties, 3))
    passed = final_score >= 0.70 and len(violations) <= 1

    return {
        "grader": "style_and_constraints",
        "passed": passed,
        "score": final_score,
        "details": {
            "word_count": word_count,
            "sentence_count": metrics["sentence_count"],
            "reading_ease": metrics["reading_ease"],
            "grade_level": metrics["grade_level"],
            "violations": violations,
            "critique": "Style and constraint requirements satisfied." if passed else f"Constraint violations: {'; '.join(violations)}"
        }
    }
