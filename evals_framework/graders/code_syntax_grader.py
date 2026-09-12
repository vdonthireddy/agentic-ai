"""Code Output Syntax & Quality Grader.

Extracts generated code snippets from the model's output response text
and validates AST syntax (Python, SQL, JSON), catching syntax errors,
unclosed quotes/brackets, and dangerous execution patterns.
"""

import ast
import json
import re
from typing import Dict, Any, List, Optional

def _validate_sql_syntax(sql_text: str) -> List[str]:
    """Basic structural validation of SQL statement without external DB driver."""
    errors = []
    clean = sql_text.strip().rstrip(";")
    if not clean:
        return ["SQL code block is empty."]

    # Check for balanced parentheses
    if clean.count("(") != clean.count(")"):
        errors.append(f"Unbalanced parentheses in SQL: {clean.count('(')} open vs {clean.count(')')} closed.")

    # Check for unclosed single quotes
    single_quotes = len(re.findall(r"(?<!\\)'", clean))
    if single_quotes % 2 != 0:
        errors.append("Unclosed single quote in SQL string literal.")

    # Check for valid beginning statement
    first_word = re.split(r"\s+", clean)[0].upper()
    valid_starters = {"SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "WITH", "EXPLAIN", "PRAGMA"}
    if first_word not in valid_starters:
        errors.append(f"SQL statement does not begin with standard DDL/DML keyword (found '{first_word}').")

    return errors

def grade_code_syntax(
    test_case: Dict[str, Any],
    assistant_response: str
) -> Dict[str, Any]:
    """
    Extracts code blocks from model output and validates syntactic correctness.
    
    Zero-dependency, offline deterministic execution.
    """
    text = assistant_response or ""
    expected_lang = test_case.get("code_language", test_case.get("expected_language", "")).lower()
    require_code = test_case.get("require_code", bool(expected_lang))

    # Extract all markdown code blocks with language tags
    code_block_pattern = r"```([a-zA-Z0-9_-]*)\n([\s\S]*?)```"
    blocks = re.findall(code_block_pattern, text)

    if not blocks:
        if require_code:
            return {
                "grader": "code_syntax",
                "passed": False,
                "score": 0.0,
                "details": {
                    "syntax_valid": False,
                    "blocks_evaluated": 0,
                    "violations": ["No code blocks found in response, but code was required."],
                    "critique": "Expected a markdown code block but output contained none."
                }
            }
        return {
            "grader": "code_syntax",
            "passed": True,
            "score": 1.0,
            "details": {
                "syntax_valid": True,
                "blocks_evaluated": 0,
                "violations": [],
                "critique": "No code required and none found; skipped."
            }
        }

    violations: List[str] = []
    blocks_evaluated = 0

    for lang_tag, code_body in blocks:
        code_str = code_body.strip()
        if not code_str:
            continue

        lang = (lang_tag.lower() or expected_lang or "python").strip()
        blocks_evaluated += 1

        # 1. Python Syntax Validation via AST
        if lang in ("python", "py"):
            try:
                tree = ast.parse(code_str)
                # Check for dangerous calls if forbidden
                if test_case.get("forbid_dangerous_calls", True):
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                            if node.func.id in ("eval", "exec", "__import__"):
                                violations.append(f"Dangerous call '{node.func.id}()' found in Python code block.")
            except SyntaxError as e:
                violations.append(f"Python SyntaxError at line {e.lineno}, col {e.offset}: {e.msg}")

        # 2. JSON Syntax Validation
        elif lang in ("json", "jsonc"):
            try:
                json.loads(code_str)
            except Exception as e:
                violations.append(f"JSON SyntaxError in code block: {str(e)}")

        # 3. SQL Syntax Validation
        elif lang in ("sql", "sqlite", "postgres", "mysql"):
            sql_errs = _validate_sql_syntax(code_str)
            violations.extend(sql_errs)

    passed = len(violations) == 0
    score = 1.0 if passed else max(0.0, 1.0 - (0.40 * len(violations)))

    return {
        "grader": "code_syntax",
        "passed": passed,
        "score": round(score, 3),
        "details": {
            "syntax_valid": passed,
            "blocks_evaluated": blocks_evaluated,
            "violations": violations,
            "critique": "All code blocks parsed without syntax errors." if passed else f"Syntax violations detected: {'; '.join(violations)}"
        }
    }
