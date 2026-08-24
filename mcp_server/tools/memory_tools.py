"""Memory tools for the MCP Server — store, recall, list, and delete semantic memories."""

import json
from typing import Dict, Any, Optional

try:
    from mcp_server.memory_backend import memory_backend
except ImportError:
    from memory_backend import memory_backend  # type: ignore[import-not-found]


def memory_store(
    content: Any = "",
    text: Any = "",
    data: Any = "",
    payload: Any = "",
    info: Any = "",
    note: Any = "",
    value: Any = "",
    result: Any = "",
    message: Any = "",
    namespace: str = "default",
    ns: str = "",
    source: str = "",
    tags: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    **kwargs: Any
) -> Dict[str, Any]:
    """Store a new memory for long-term semantic recall.
    
    Args:
        content/text/data/payload/note: The content or structured data to remember.
        namespace/ns: Namespace for organizing memories (e.g., 'work', 'personal').
        source: Where this memory came from (e.g., 'conversation', 'tool_result').
        tags: Comma-separated tags for filtering.
        metadata: Additional key-value metadata.
    """
    candidates = [
        content, text, data, payload, info, note, value, result, message,
        kwargs.get("response"), kwargs.get("answer"), kwargs.get("input"),
        kwargs.get("query"), kwargs.get("details"), kwargs.get("statement"),
        kwargs.get("content"), kwargs.get("text"), kwargs.get("data"), kwargs.get("payload")
    ]
    actual_content = ""
    for c in candidates:
        if c is not None and c != "" and c != {}:
            if isinstance(c, (dict, list)):
                actual_content = json.dumps(c, indent=2)
            else:
                actual_content = str(c)
            break

    if not actual_content:
        return {"status": "error", "message": "No content provided to store."}
    
    actual_ns = namespace or ns or kwargs.get("namespace") or kwargs.get("ns") or "default"
    meta = metadata or {}
    if source:
        meta["source"] = source
    if tags:
        meta["tags"] = [t.strip() for t in tags.split(",") if t.strip()]

    try:
        memory_id = memory_backend.store(actual_content, meta, actual_ns)
        return {
            "status": "success",
            "memory_id": memory_id,
            "namespace": actual_ns,
            "content_preview": actual_content[:100] + ("..." if len(actual_content) > 100 else ""),
            "message": f"Memory stored successfully in namespace '{actual_ns}'."
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to store memory: {str(e)}"}


def memory_recall(
    query: str = "",
    search: str = "",
    question: str = "",
    namespace: str = "default",
    ns: str = "",
    top_k: int = 5,
    limit: int = 0
) -> Dict[str, Any]:
    """Recall memories semantically similar to the query.
    
    Args:
        query/search/question: The search query for semantic recall.
        namespace/ns: Namespace to search within.
        top_k/limit: Maximum number of memories to return.
    """
    actual_query = query or search or question
    if not actual_query:
        return {"status": "error", "message": "No query provided for recall."}
    
    actual_ns = namespace or ns or "default"
    actual_k = limit if limit > 0 else top_k

    try:
        memories = memory_backend.recall(actual_query, actual_ns, actual_k)
        return {
            "status": "success",
            "query": actual_query,
            "namespace": actual_ns,
            "count": len(memories),
            "memories": memories,
            "message": f"Found {len(memories)} relevant memories." if memories else "No matching memories found."
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to recall memories: {str(e)}"}


def memory_list(
    namespace: str = "default",
    ns: str = "",
    limit: int = 50
) -> Dict[str, Any]:
    """List all stored memories in a namespace.
    
    Args:
        namespace/ns: Namespace to list.
        limit: Maximum number of memories to return.
    """
    actual_ns = namespace or ns or "default"

    try:
        memories = memory_backend.list_memories(actual_ns, limit)
        namespaces = memory_backend.list_namespaces()
        return {
            "status": "success",
            "namespace": actual_ns,
            "count": len(memories),
            "available_namespaces": namespaces,
            "memories": memories
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to list memories: {str(e)}"}


def memory_delete(
    memory_id: str = "",
    id: str = ""
) -> Dict[str, Any]:
    """Delete a specific memory by its ID.
    
    Args:
        memory_id/id: The unique identifier of the memory to delete.
    """
    actual_id = memory_id or id
    if not actual_id:
        return {"status": "error", "message": "No memory_id provided."}

    try:
        deleted = memory_backend.delete(actual_id)
        if deleted:
            return {
                "status": "success",
                "memory_id": actual_id,
                "message": f"Memory '{actual_id}' deleted successfully."
            }
        else:
            return {
                "status": "error",
                "memory_id": actual_id,
                "message": f"Memory '{actual_id}' not found."
            }
    except Exception as e:
        return {"status": "error", "message": f"Failed to delete memory: {str(e)}"}
