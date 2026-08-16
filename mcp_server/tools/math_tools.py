"""Mathematical and code evaluation tools for MCP Server."""

import ast
import operator
import sys
import io
import contextlib
import traceback
from typing import Any, Dict

# Allowed operators for safe mathematical evaluation
SAFE_BIN_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

SAFE_UNARY_OPERATORS = {
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
        if op_type in SAFE_BIN_OPERATORS:
            left = safe_eval_math(node.left)
            right = safe_eval_math(node.right)
            return SAFE_BIN_OPERATORS[op_type](left, right)
        raise ValueError(f"Unsupported binary operator: {op_type.__name__}")
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type in SAFE_UNARY_OPERATORS:
            operand = safe_eval_math(node.operand)
            return SAFE_UNARY_OPERATORS[op_type](operand)
        raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
    else:
        raise ValueError(f"Unsupported expression node: {type(node).__name__}")

def calculate(
    expression: str = "",
    formula: str = "",
    tip: str = "",
    total: str = "",
    math_expr: str = ""
) -> Dict[str, Any]:
    """
    Evaluates arithmetic expression(s) safely using AST parser.
    Supports single expression, formula, tip, total, or combined expressions.
    """
    expr_to_eval = expression or formula or math_expr
    if not expr_to_eval:
        if tip and total:
            expr_to_eval = f"({total}) + ({tip})"
        elif total:
            expr_to_eval = total
        elif tip:
            expr_to_eval = tip

    if expr_to_eval:
        try:
            parsed = ast.parse(expr_to_eval.strip(), mode="eval")
            result = safe_eval_math(parsed)
            return {
                "success": True,
                "expression": expr_to_eval,
                "result": result,
                "type": type(result).__name__
            }
        except Exception as e:
            return {
                "success": False,
                "expression": expr_to_eval,
                "error": str(e)
            }

    return {
        "success": False,
        "error": "No mathematical expression provided to calculate."
    }

def calculate_tip_and_split(
    total: Any = None,
    bill: Any = None,
    amount: Any = None,
    total_bill: Any = None,
    bill_total: Any = None,
    total_amount: Any = None,
    bill_amount: Any = None,
    cost: Any = None,
    price: Any = None,
    tip_percentage: Any = None,
    tip_percent: Any = None,
    tip: Any = None,
    tip_rate: Any = None,
    num_people: Any = None,
    number_of_people: Any = None,
    num_diners: Any = None,
    people_count: Any = None,
    split: Any = None,
    people: Any = None,
    diners: Any = None,
    count: Any = None,
    **kwargs: Any
) -> Dict[str, Any]:
    """Calculate tip and split bill evenly among multiple people with robust parameter mapping."""
    try:
        # Resolve bill amount across any LLM parameter naming
        bill_candidates = [total_bill, bill_total, total_amount, bill_amount, total, bill, amount, cost, price, kwargs.get("total_bill"), kwargs.get("bill"), kwargs.get("total")]
        valid_bills = [float(c) for c in bill_candidates if c is not None and c != "" and float(c or 0) > 0]
        resolved_bill = valid_bills[0] if valid_bills else 0.0
        
        # Resolve tip percentage
        tip_candidates = [tip_percentage, tip_percent, tip, tip_rate, kwargs.get("tip_percentage"), kwargs.get("tip_percent"), kwargs.get("tip")]
        valid_tips = [float(t) for t in tip_candidates if t is not None and t != "" and float(t or 0) > 0]
        raw_tip_val = valid_tips[0] if valid_tips else 0.18
        if raw_tip_val > 1.0:
            raw_tip_val = raw_tip_val / 100.0
            
        tip_amount = round(resolved_bill * raw_tip_val, 2)
        total_with_tip = round(resolved_bill + tip_amount, 2)
        
        # Resolve number of people (prioritize values > 1 over single diner default 1)
        people_candidates = [number_of_people, num_people, num_diners, people_count, split, people, diners, count, kwargs.get("number_of_people"), kwargs.get("num_people"), kwargs.get("split")]
        valid_people = [int(p) for p in people_candidates if p is not None and p != "" and str(p).isdigit() and int(p) > 0]
        n_people = next((p for p in valid_people if p > 1), (valid_people[0] if valid_people else 1))
        per_person = round(total_with_tip / n_people, 2)
        
        return {
            "success": True,
            "bill": resolved_bill,
            "tip_percentage": f"{int(raw_tip_val * 100)}%",
            "tip_amount": tip_amount,
            "total_with_tip": total_with_tip,
            "num_people": n_people,
            "per_person": per_person,
            "result": per_person
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

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
