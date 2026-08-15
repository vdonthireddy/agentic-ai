"""Mathematical and code evaluation tools for MCP Server."""

import ast
import operator
import sys
import io
import contextlib
import traceback
from typing import Any, Dict

# Allowed operators for safe mathematical evaluation
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

def safe_eval_math(node: ast.AST) -> Any:
    """Safely evaluate an AST expression consisting only of numbers and arithmetic."""
    if isinstance(node, ast.Expression):
        return safe_eval_math(node.body)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, complex)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value)}")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            left = safe_eval_math(node.left)
            right = safe_eval_math(node.right)
            return SAFE_OPERATORS[op_type](left, right)
        raise ValueError(f"Unsupported binary operator: {op_type.__name__}")
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            operand = safe_eval_math(node.operand)
            return SAFE_OPERATORS[op_type](operand)
        raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
    else:
        raise ValueError(f"Unsupported expression node: {type(node).__name__}")

def calculate(expression: str) -> Dict[str, Any]:
    """
    Evaluates an arithmetic expression safely using AST parser.
    Supports operations: +, -, *, /, //, %, **
    """
    try:
        parsed = ast.parse(expression.strip(), mode="eval")
        result = safe_eval_math(parsed)
        return {
            "success": True,
            "expression": expression,
            "result": result,
            "type": type(result).__name__
        }
    except Exception as e:
        return {
            "success": False,
            "expression": expression,
            "error": str(e)
        }

def _sanitize_python_code(code_str: str) -> str:
    """Fixes common LLM formatting artifacts such as unescaped newlines in single-quoted strings."""
    try:
        compile(code_str, "<string>", "exec")
        return code_str
    except SyntaxError:
        pass

    lines = code_str.split("\n")
    repaired = []
    accum = ""
    for line in lines:
        if not accum:
            accum = line
        else:
            accum += "\\n" + line
        
        # Check if quotes are balanced
        sq = accum.count("\x27") - accum.count("\\\x27")
        dq = accum.count("\x22") - accum.count("\\\x22")
        if sq % 2 == 0 and dq % 2 == 0:
            repaired.append(accum)
            accum = ""
    if accum:
        repaired.append(accum)
    
    return "\n".join(repaired)

def execute_python_code(
    code: str = "",
    code_snippet: str = "",
    script: str = "",
    python_code: str = "",
    timeout_seconds: int = 5
) -> Dict[str, Any]:
    """
    Executes a Python code snippet in a controlled environment and captures stdout/stderr and returned variables.
    """
    actual_code = code or code_snippet or script or python_code or ""
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    # Restrict builtins for basic safety
    allowed_builtins = {
        "print": print, "range": range, "len": len, "sum": sum, "min": min, "max": max,
        "abs": abs, "round": round, "sorted": sorted, "enumerate": enumerate, "zip": zip,
        "map": map, "filter": filter, "list": list, "dict": dict, "set": set, "tuple": tuple,
        "str": str, "int": int, "float": float, "bool": bool, "any": any, "all": all,
        "isinstance": isinstance, "issubclass": issubclass, "math": __import__("math"),
        "json": __import__("json"), "re": __import__("re"), "datetime": __import__("datetime"),
        "statistics": __import__("statistics"), "collections": __import__("collections"),
        "itertools": __import__("itertools"), "__import__": __import__
    }
    
    scope = {"__builtins__": allowed_builtins}
    
    # Attempt execution with original code, then fallback to sanitized code if syntax error occurs
    for code_to_run in [actual_code, _sanitize_python_code(actual_code)]:
        try:
            with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                exec(code_to_run, scope)
            
            # Filter serializable outputs from scope
            safe_locals = {}
            for k, v in scope.items():
                if not k.startswith("_") and k not in allowed_builtins:
                    try:
                        safe_locals[k] = repr(v)
                    except Exception:
                        pass
            
            return {
                "success": True,
                "stdout": stdout_capture.getvalue(),
                "stderr": stderr_capture.getvalue(),
                "variables": safe_locals
            }
        except SyntaxError as syn_err:
            if code_to_run == code:
                # try sanitized version
                stdout_capture = io.StringIO()
                stderr_capture = io.StringIO()
                continue
            return {
                "success": False,
                "error": str(syn_err),
                "traceback": traceback.format_exc(),
                "stdout": stdout_capture.getvalue(),
                "stderr": stderr_capture.getvalue()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "stdout": stdout_capture.getvalue(),
                "stderr": stderr_capture.getvalue()
            }
