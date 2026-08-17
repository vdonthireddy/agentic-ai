"""File system workspace operations tool for MCP Server."""

import os
from pathlib import Path
from typing import Dict, Any, List

WORKSPACE_ROOT = Path(os.environ.get("AGENT_WORKSPACE_DIR", "./workspace")).resolve()

def ensure_workspace():
    """Ensure workspace directory exists."""
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)

def _get_safe_path(rel_path: str) -> Path:
    """Resolve and enforce path staying within WORKSPACE_ROOT."""
    ensure_workspace()
    resolved = (WORKSPACE_ROOT / rel_path).resolve()
    if not str(resolved).startswith(str(WORKSPACE_ROOT)):
        raise ValueError(f"Access denied: path '{rel_path}' is outside the authorized workspace directory.")
    return resolved

def workspace_file_ops(
    action: str = "",
    operation: str = "",
    op: str = "",
    filepath: str = "",
    file_path: str = "",
    filename: str = "",
    file_name: str = "",
    path: str = "",
    content: str = "",
    text: str = "",
    data: str = "",
    **kwargs: Any
) -> Dict[str, Any]:
    """
    Perform workspace file operations: 'read', 'write', 'list', 'delete'.
    - 'read': returns the text content of the file.
    - 'write': writes or overwrites content into the file.
    - 'list': lists files in the workspace or subdirectory.
    - 'delete': deletes the specified file.
    """
    ensure_workspace()
    raw_act = (action or operation or op or ("write" if (content or text or data) else "read")).lower().strip()
    if raw_act in ("save", "store", "create", "overwrite", "write"):
        actual_action = "write"
    elif raw_act in ("read", "get", "load", "view", "open"):
        actual_action = "read"
    elif raw_act in ("list", "ls", "dir", "show"):
        actual_action = "list"
    elif raw_act in ("delete", "remove", "rm", "del"):
        actual_action = "delete"
    else:
        actual_action = raw_act

    target_path_str = filepath or file_path or filename or file_name or path or kwargs.get("name", "") or ""
    actual_content = content or text or data or kwargs.get("data", "") or ""

    
    try:
        if actual_action == "list":
            # If target path is a file or doesn't exist as directory, list workspace root or parent
            target_dir = WORKSPACE_ROOT
            if target_path_str and target_path_str not in (".", "/"):
                try:
                    candidate = _get_safe_path(target_path_str)
                    if candidate.exists() and candidate.is_dir():
                        target_dir = candidate
                    elif candidate.exists() and candidate.is_file():
                        target_dir = candidate.parent
                except Exception:
                    target_dir = WORKSPACE_ROOT

            items = []
            if target_dir.exists() and target_dir.is_dir():
                for item in target_dir.iterdir():
                    try:
                        rel = item.relative_to(WORKSPACE_ROOT)
                        items.append({
                            "name": item.name,
                            "path": str(rel),
                            "is_dir": item.is_dir(),
                            "size_bytes": item.stat().st_size if item.is_file() else 0
                        })
                    except Exception:
                        continue

            return {"success": True, "action": "list", "directory": str(target_dir.relative_to(WORKSPACE_ROOT) if target_dir != WORKSPACE_ROOT else "."), "items": items}

        elif actual_action == "read":
            if not target_path_str:
                return {"success": False, "error": "filepath is required for 'read' action"}
            target_file = _get_safe_path(target_path_str)
            if not target_file.exists() or not target_file.is_file():
                return {"success": False, "error": f"File '{target_path_str}' not found."}
            text = target_file.read_text(encoding="utf-8")
            return {"success": True, "action": "read", "filepath": target_path_str, "content": text, "bytes": len(text)}

        elif actual_action == "write":
            if not target_path_str:
                return {"success": False, "error": "filepath is required for 'write' action"}
            target_file = _get_safe_path(target_path_str)
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(actual_content, encoding="utf-8")
            return {"success": True, "action": "write", "filepath": target_path_str, "bytes_written": len(actual_content)}

        elif actual_action == "delete":
            if not target_path_str:
                return {"success": False, "error": "filepath is required for 'delete' action"}
            target_file = _get_safe_path(target_path_str)
            if target_file.exists() and target_file.is_file():
                target_file.unlink()
                return {"success": True, "action": "delete", "filepath": target_path_str}
            return {"success": False, "error": f"File '{target_path_str}' not found"}

        else:
            return {"success": False, "error": f"Unknown action '{actual_action}'. Allowed: read, write, list, delete"}

    except Exception as e:
        return {"success": False, "action": action, "error": str(e)}
