"""
Python Sandbox Code Interpreter Tool for MCP Server.
Executes Python code in a constrained environment and generates structured Plotly charts & tables.
"""

import sys
import io
import json
import ast
import traceback
import types
from typing import Dict, Any, Optional, Set

# Whitelisted standard built-in functions and types for safe execution
SAFE_BUILTIN_NAMES: Set[str] = {
    "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes",
    "chr", "complex", "dict", "divmod", "enumerate", "filter", "float",
    "format", "frozenset", "hash", "hex", "int", "isinstance", "issubclass",
    "iter", "len", "list", "map", "max", "min", "next", "oct", "ord",
    "pow", "range", "repr", "reversed", "round", "set", "slice",
    "sorted", "str", "sum", "tuple", "type", "zip",
    "ArithmeticError", "AssertionError", "AttributeError", "BaseException",
    "Exception", "IndexError", "KeyError", "LookupError", "NameError",
    "OverflowError", "RuntimeError", "StopIteration", "TypeError",
    "ValueError", "ZeroDivisionError", "True", "False", "None"
}

ALLOWED_IMPORT_PACKAGES: Set[str] = {
    "math", "statistics", "json", "datetime", "random", "re",
    "collections", "itertools", "decimal", "fractions", "plotly"
}

DISALLOWED_ATTRIBUTES: Set[str] = {
    "__subclasses__", "__bases__", "__globals__", "__builtins__",
    "__code__", "__closure__", "__class__", "gi_frame", "f_globals"
}

DISALLOWED_CALLS: Set[str] = {
    "eval", "exec", "compile", "open", "breakpoint", "exit", "quit", "input", "__import__"
}


def validate_python_code_ast(code: str) -> Optional[str]:
    """
    Statically analyzes code AST to block dangerous syntax, unsafe attribute access,
    and unauthorized imports prior to execution.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"Syntax error in Python code: {str(e)}"

    for node in ast.walk(tree):
        # 1. Check imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                pkg = alias.name.split(".")[0]
                if pkg not in ALLOWED_IMPORT_PACKAGES:
                    return f"Security restriction: Execution of 'import {alias.name}' is disallowed in Python sandbox."
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                pkg = node.module.split(".")[0]
                if pkg not in ALLOWED_IMPORT_PACKAGES:
                    return f"Security restriction: Execution of 'from {node.module}' is disallowed in Python sandbox."

        # 2. Check attribute access (e.g. obj.__class__, obj.__subclasses__)
        elif isinstance(node, ast.Attribute):
            if node.attr in DISALLOWED_ATTRIBUTES:
                return f"Security restriction: Access to '{node.attr}' is disallowed in Python sandbox."

        # 3. Check calls to dangerous builtins (e.g. open(), eval(), exec())
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in DISALLOWED_CALLS:
                return f"Security restriction: Execution of '{node.func.id}' is disallowed in Python sandbox."

    return None


def execute_python_sandbox(
    code: str = "",
    script: str = "",
    python_code: str = "",
    timeout_seconds: float = 5.0,
    **kwargs: Any
) -> Dict[str, Any]:
    """
    Execute Python code in a hardened AST-validated sandbox, capturing stdout,
    return values, and Plotly figure JSON specs.
    """
    actual_code = (code or script or python_code or "").strip()
    if not actual_code:
        return {"status": "error", "message": "No Python code provided for execution."}

    # Clean markdown fences if model passed code block
    if actual_code.startswith("```python"):
        actual_code = actual_code[9:]
    elif actual_code.startswith("```"):
        actual_code = actual_code[3:]
    if actual_code.endswith("```"):
        actual_code = actual_code[:-3]
    actual_code = actual_code.strip()

    # Block destructive terms (regex / string match backward-compatibility)
    blocked_terms = ["os.system", "subprocess.Popen", "shutil.rmtree", "pty.spawn", "__import__('os').system"]
    for term in blocked_terms:
        if term in actual_code:
            return {
                "status": "error",
                "message": f"Security restriction: Execution of '{term}' is disallowed in Python sandbox."
            }

    # Static AST security inspection
    ast_error = validate_python_code_ast(actual_code)
    if ast_error:
        return {
            "status": "error",
            "message": ast_error
        }

    # Prepare standard execution environment with math, json, and plotly
    stdout_capture = io.StringIO()
    old_stdout = sys.stdout

    # Sandbox namespace
    plotly_figs = []
    
    class FigureHook:
        def __init__(self, fig):
            self.fig = fig
            try:
                plotly_figs.append(fig.to_dict())
            except Exception:
                pass
        def show(self, *args, **kwargs):
            try:
                plotly_figs.append(self.fig.to_dict())
            except Exception:
                pass

    # Construct safe builtins dictionary
    raw_builtins = __builtins__ if isinstance(__builtins__, dict) else vars(__builtins__)
    safe_builtins = {k: raw_builtins[k] for k in SAFE_BUILTIN_NAMES if k in raw_builtins}
    safe_builtins["print"] = lambda *a, **kw: print(*a, file=stdout_capture, **kw)

    def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
        base_pkg = name.split(".")[0]
        if base_pkg not in ALLOWED_IMPORT_PACKAGES:
            raise ImportError(f"Security restriction: Execution of import '{name}' is disallowed in Python sandbox.")
        return __import__(name, globals, locals, fromlist, level)

    safe_builtins["__import__"] = safe_import

    safe_globals = {
        "__builtins__": safe_builtins,
        "print": safe_builtins["print"],
        "json": json,
    }

    try:
        import math
        safe_globals["math"] = math
    except ImportError:
        pass

    try:
        import statistics
        safe_globals["statistics"] = statistics
    except ImportError:
        pass

    try:
        import importlib
        go = importlib.import_module("plotly.graph_objects")
        px = importlib.import_module("plotly.express")
        plotly_mod = importlib.import_module("plotly")
        safe_globals["go"] = go
        safe_globals["px"] = px
        safe_globals["plotly"] = plotly_mod
    except (ImportError, ModuleNotFoundError):
        import types

        class MockPlotlyFigure:
            def __init__(self, data=None, layout=None, **kwargs):
                self.data = data or []
                self.layout = layout or {}
            def to_dict(self):
                return {"data": self.data, "layout": self.layout}
            def show(self):
                pass

        mock_plotly = types.ModuleType("plotly")
        mock_go = types.ModuleType("plotly.graph_objects")
        mock_px = types.ModuleType("plotly.express")

        setattr(mock_go, "Figure", MockPlotlyFigure)
        setattr(mock_go, "Bar", lambda *a, **kw: {"type": "bar", **kw})
        setattr(mock_go, "Scatter", lambda *a, **kw: {"type": "scatter", **kw})
        setattr(mock_go, "Line", lambda *a, **kw: {"type": "line", **kw})
        setattr(mock_go, "Pie", lambda *a, **kw: {"type": "pie", **kw})

        setattr(mock_px, "bar", lambda *a, **kw: MockPlotlyFigure(data=[{"type": "bar", **kw}]))
        setattr(mock_px, "scatter", lambda *a, **kw: MockPlotlyFigure(data=[{"type": "scatter", **kw}]))

        setattr(mock_plotly, "graph_objects", mock_go)
        setattr(mock_plotly, "express", mock_px)

        safe_globals["go"] = mock_go
        safe_globals["px"] = mock_px
        safe_globals["plotly"] = mock_plotly
        sys.modules["plotly"] = mock_plotly
        sys.modules["plotly.graph_objects"] = mock_go
        sys.modules["plotly.express"] = mock_px

    local_vars = {}
    success = False
    error_msg = None

    try:
        sys.stdout = stdout_capture
        # Execute code with timeout
        import time
        start_time = time.time()
        def trace_calls(frame, event, arg):
            if time.time() - start_time > timeout_seconds:
                raise TimeoutError(f"Execution exceeded timeout of {timeout_seconds} seconds")
            return trace_calls
        old_trace = sys.gettrace()
        sys.settrace(trace_calls)
        try:
            exec(actual_code, safe_globals, local_vars)
        finally:
            sys.settrace(old_trace)
        success = True
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
    finally:
        sys.stdout = old_stdout

    output_text = stdout_capture.getvalue()

    # Scan for any Plotly figure variables created in local scope
    try:
        for k, v in local_vars.items():
            if hasattr(v, "to_dict") and callable(getattr(v, "to_dict")):
                fig_dict = v.to_dict()
                if isinstance(fig_dict, dict) and "data" in fig_dict and fig_dict not in plotly_figs:
                    plotly_figs.append(fig_dict)
    except Exception:
        pass

    result_data = {
        "status": "success" if success else "error",
        "output": output_text.strip(),
        "error": error_msg,
        "figures_count": len(plotly_figs),
        "plotly_figures": plotly_figs,
        "result_variables": {
            k: str(v)[:200] for k, v in local_vars.items()
            if not k.startswith("_") and not callable(v) and not hasattr(v, "__module__")
        }
    }
    return result_data
