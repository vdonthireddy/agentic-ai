"""SQLite storage and schema for LLM Gateway audit logs."""

import sqlite3
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

DB_PATH = Path(os.environ.get("LLM_GATEWAY_DB_PATH", "./llm_gateway.db")).resolve()

def init_db(db_path: Path = DB_PATH):
    """Initialize SQLite tables for storing request/response audit logs."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS llm_logs (
        id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        caller_id TEXT,
        agent_name TEXT,
        session_id TEXT,
        caller_context TEXT,
        model TEXT NOT NULL,
        skill_names TEXT,
        tool_names TEXT,
        request_messages TEXT NOT NULL,
        request_tools TEXT,
        request_params TEXT,
        response_content TEXT,
        response_tool_calls TEXT,
        prompt_tokens INTEGER,
        completion_tokens INTEGER,
        total_tokens INTEGER,
        latency_ms REAL,
        status TEXT,
        error_message TEXT
    )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON llm_logs(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_session ON llm_logs(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_agent ON llm_logs(agent_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_model ON llm_logs(model)")
    
    conn.commit()
    conn.close()

def save_log_entry(entry: Dict[str, Any], db_path: Path = DB_PATH):
    """Insert a detailed audit log entry into SQLite."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("""
    INSERT INTO llm_logs (
        id, timestamp, caller_id, agent_name, session_id, caller_context,
        model, skill_names, tool_names, request_messages, request_tools, request_params,
        response_content, response_tool_calls, prompt_tokens, completion_tokens,
        total_tokens, latency_ms, status, error_message
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        entry.get("id"),
        entry.get("timestamp", datetime.now(timezone.utc).isoformat()),
        entry.get("caller_id"),
        entry.get("agent_name"),
        entry.get("session_id"),
        json.dumps(entry.get("caller_context", {})) if isinstance(entry.get("caller_context"), (dict, list)) else entry.get("caller_context"),
        entry.get("model"),
        json.dumps(entry.get("skill_names", [])) if isinstance(entry.get("skill_names"), list) else entry.get("skill_names"),
        json.dumps(entry.get("tool_names", [])) if isinstance(entry.get("tool_names"), list) else entry.get("tool_names"),
        json.dumps(entry.get("request_messages", [])) if not isinstance(entry.get("request_messages"), str) else entry.get("request_messages"),
        json.dumps(entry.get("request_tools", [])) if not isinstance(entry.get("request_tools"), str) else entry.get("request_tools"),
        json.dumps(entry.get("request_params", {})) if not isinstance(entry.get("request_params"), str) else entry.get("request_params"),
        entry.get("response_content"),
        json.dumps(entry.get("response_tool_calls", [])) if isinstance(entry.get("response_tool_calls"), list) else entry.get("response_tool_calls"),
        entry.get("prompt_tokens", 0),
        entry.get("completion_tokens", 0),
        entry.get("total_tokens", 0),
        entry.get("latency_ms", 0.0),
        entry.get("status", "SUCCESS"),
        entry.get("error_message")
    ))
    
    conn.commit()
    conn.close()

def query_logs(
    limit: int = 50,
    offset: int = 0,
    session_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    model: Optional[str] = None,
    db_path: Path = DB_PATH
) -> List[Dict[str, Any]]:
    """Query logs with optional filters."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM llm_logs WHERE 1=1"
    params: List[Any] = []
    
    if session_id:
        query += " AND session_id = ?"
        params.append(session_id)
    if agent_name:
        query += " AND agent_name = ?"
        params.append(agent_name)
    if model:
        query += " AND model = ?"
        params.append(model)
        
    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    results = []
    for row in rows:
        item = dict(row)
        for json_col in ["caller_context", "skill_names", "tool_names", "request_messages", "request_tools", "request_params", "response_tool_calls"]:
            if item.get(json_col):
                try:
                    item[json_col] = json.loads(item[json_col])
                except Exception:
                    pass
        results.append(item)
        
    conn.close()
    return results

def get_stats(db_path: Path = DB_PATH) -> Dict[str, Any]:
    """Calculate aggregate statistics of LLM usage and tool/skill utilization."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT 
        COUNT(*) as total_calls,
        SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful_calls,
        SUM(CASE WHEN status = 'ERROR' THEN 1 ELSE 0 END) as error_calls,
        COALESCE(SUM(prompt_tokens), 0) as total_prompt_tokens,
        COALESCE(SUM(completion_tokens), 0) as total_completion_tokens,
        COALESCE(SUM(total_tokens), 0) as total_tokens,
        COALESCE(AVG(latency_ms), 0.0) as avg_latency_ms
    FROM llm_logs
    """)
    row = cursor.fetchone()
    
    # Models breakdown
    cursor.execute("SELECT model, COUNT(*) FROM llm_logs GROUP BY model")
    models_breakdown = dict(cursor.fetchall())
    
    # Tools and skills aggregation
    cursor.execute("SELECT tool_names, skill_names FROM llm_logs")
    all_rows = cursor.fetchall()
    
    tool_counts: Dict[str, int] = {}
    skill_counts: Dict[str, int] = {}
    
    for tool_str, skill_str in all_rows:
        if tool_str:
            try:
                tools = json.loads(tool_str)
                for t in tools:
                    tool_counts[t] = tool_counts.get(t, 0) + 1
            except Exception:
                pass
        if skill_str:
            try:
                skills = json.loads(skill_str)
                for s in skills:
                    skill_counts[s] = skill_counts.get(s, 0) + 1
            except Exception:
                pass
                
    conn.close()
    
    return {
        "total_calls": row[0],
        "successful_calls": row[1],
        "error_calls": row[2],
        "token_usage": {
            "prompt_tokens": row[3],
            "completion_tokens": row[4],
            "total_tokens": row[5]
        },
        "average_latency_ms": round(row[6], 2),
        "models_usage": models_breakdown,
        "tools_usage_frequency": tool_counts,
        "skills_usage_frequency": skill_counts
    }
