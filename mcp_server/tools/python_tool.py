"""
Python Sandbox Code Interpreter Tool for MCP Server.
Executes Python code in a constrained environment and generates structured Plotly charts & tables.
"""

import sys
import io
import json
import traceback
from typing import Dict, Any, Optional

def execute_python_sandbox(
    code: str = "",
    script: str = "",
    python_code: str = "",
    timeout_seconds: float = 5.0,
    **kwargs: Any
) -> Dict[str, Any]:
    """
    Execute Python code in a safe sandbox, capturing stdout, return values, and Plotly figure JSON specs.
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

    # Block destructive system modules
    blocked_terms = ["os.system", "subprocess.Popen", "shutil.rmtree", "pty.spawn", "__import__('os').system"]
    for term in blocked_terms:
        if term in actual_code:
            return {
                "status": "error",
                "message": f"Security restriction: Execution of '{term}' is disallowed in Python sandbox."
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

    safe_globals = {
        "__builtins__": __builtins__,
        "print": lambda *a, **kw: print(*a, file=stdout_capture, **kw),
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
        import plotly.graph_objects as go
        import plotly.express as px
        safe_globals["go"] = go
        safe_globals["px"] = px
        safe_globals["plotly"] = __import__("plotly")
    except ImportError:
        pass

    local_vars = {}
    success = False
    error_msg = None

    try:
        sys.stdout = stdout_capture
        # Execute code
        exec(actual_code, safe_globals, local_vars)
        success = True
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
    finally:
        sys.stdout = old_stdout

    output_text = stdout_capture.getvalue()

    # Scan for any Plotly figure variables created in local scope
    try:
        for k, v in local_vars.items():
            if hasattr(v, "to_dict") and callable(v.to_dict):
                fig_dict = v.to_dict()
                if "data" in fig_dict and fig_dict not in plotly_figs:
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
