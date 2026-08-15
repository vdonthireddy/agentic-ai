"""Code reviewer skill definition and prompts."""

from typing import Dict, Any

CODE_REVIEW_SKILL_METADATA = {
    "name": "code_review_skill",
    "description": "Senior Software Architect skill for conducting security, performance, complexity, and idiomatic code reviews.",
    "version": "1.0.0",
    "recommended_tools": ["execute_python", "workspace_file_ops"]
}

def render_code_review_skill(code_snippet: str, language: str = "python", focus: str = "general") -> str:
    """
    Renders structured instructions for performing a senior code review.
    """
    return f"""# Skill: Senior Code Reviewer & Architect

## Target Language: {language}
## Primary Focus: {focus}

## Code Under Review:
```{language}
{code_snippet}
```

## Review Guidelines & Criteria:
1. **Security & Vulnerabilities**: Check for injection risks, unsafe deserialization, race conditions, path traversal, resource leaks.
2. **Correctness & Edge Cases**: Identify off-by-one errors, unhandled exceptions, null/none dereferencing, boundary condition failures.
3. **Performance & Complexity**: Analyze time/space complexity (Big-O), memory overhead, and unneeded nested loops.
4. **Clean Code & Idiomatic Best Practices**: Evaluate naming conventions, readability, modularity, and docstrings.
5. **Tool Usage**: If testing logic or reproducing a bug, use `execute_python` to verify behavior before finalizing conclusions.

## Output Format:
- **Review Summary**: High-level verdict (Approve / Needs Changes / Critical Fixes)
- **Strengths**: What is done well
- **Issues & Vulnerabilities**: Specific findings categorized by severity (Critical / High / Medium / Low) with line references
- **Refactored Code**: Complete, drop-in replacement with fixes applied
"""
