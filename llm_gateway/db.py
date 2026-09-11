"""SQLite storage and schema for LLM Gateway audit logs."""

import sqlite3
import json
import os
import uuid
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

DB_PATH = Path(os.environ.get("LLM_GATEWAY_DB_PATH", "./llm_gateway.db")).resolve()

def get_default_db_path() -> Path:
    """Dynamically resolve SQLite DB path honoring LLM_GATEWAY_DB_PATH env var."""
    env = os.environ.get("LLM_GATEWAY_DB_PATH")
    if env:
        return Path(env).resolve()
    return DB_PATH

def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Create a hardened SQLite connection with WAL journal mode and busy timeout."""
    target_path = Path(db_path).resolve() if db_path is not None else get_default_db_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path), timeout=30.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
    except Exception:
        pass
    return conn

def init_db(db_path: Optional[Path] = None):
    """Initialize SQLite tables for storing request/response audit logs."""
    target_path = Path(db_path).resolve() if db_path is not None else get_default_db_path()
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS llm_logs (
        id TEXT PRIMARY KEY,
        request_id TEXT,
        turn_id TEXT,
        conversation_id TEXT,
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
    
    # Auto-migrate existing databases to include hierarchical ID columns if missing
    cursor.execute("PRAGMA table_info(llm_logs)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "request_id" not in columns:
        cursor.execute("ALTER TABLE llm_logs ADD COLUMN request_id TEXT")
    if "turn_id" not in columns:
        cursor.execute("ALTER TABLE llm_logs ADD COLUMN turn_id TEXT")
    if "conversation_id" not in columns:
        cursor.execute("ALTER TABLE llm_logs ADD COLUMN conversation_id TEXT")
        # Backfill conversation_id with session_id if empty
        cursor.execute("UPDATE llm_logs SET conversation_id = session_id WHERE conversation_id IS NULL AND session_id IS NOT NULL")
    if "cost_usd" not in columns:
        cursor.execute("ALTER TABLE llm_logs ADD COLUMN cost_usd REAL DEFAULT 0.0")
    if "request_id" not in columns or True:
        cursor.execute("UPDATE llm_logs SET request_id = id WHERE request_id IS NULL AND id IS NOT NULL")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS gateway_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)
    
    conn.commit()
    conn.close()

    init_saved_pipelines(db_path)
    init_checkpoint_db(db_path)
    init_hitl_db(db_path)
    init_smart_router_db(db_path)

def save_gateway_setting(key: str, value: str, db_path: Path = DB_PATH):
    """Persist a runtime gateway configuration setting to SQLite."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO gateway_settings (key, value) VALUES (?, ?)
    ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (key, str(value)))
    conn.commit()
    conn.close()

def get_gateway_settings(db_path: Path = DB_PATH) -> Dict[str, str]:
    """Retrieve all persisted gateway configuration settings from SQLite."""
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS gateway_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        cursor.execute("SELECT key, value FROM gateway_settings")
        rows = cursor.fetchall()
        conn.close()
        return {r[0]: r[1] for r in rows}
    except Exception:
        return {}

def save_log_entry(entry: Dict[str, Any], db_path: Path = DB_PATH):
    """Insert a detailed audit log entry into SQLite."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    req_id = entry.get("request_id") or entry.get("id")
    conv_id = entry.get("conversation_id") or entry.get("session_id")
    turn_id = entry.get("turn_id")
    
    cursor.execute("""
    INSERT INTO llm_logs (
        id, request_id, turn_id, conversation_id, timestamp, caller_id, agent_name, session_id, caller_context,
        model, skill_names, tool_names, request_messages, request_tools, request_params,
        response_content, response_tool_calls, prompt_tokens, completion_tokens,
        total_tokens, latency_ms, status, error_message
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        req_id,
        req_id,
        turn_id,
        conv_id,
        entry.get("timestamp", datetime.now(timezone.utc).isoformat()),
        entry.get("caller_id"),
        entry.get("agent_name"),
        conv_id,
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
    conversation_id: Optional[str] = None,
    session_id: Optional[str] = None,
    turn_id: Optional[str] = None,
    request_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    model: Optional[str] = None,
    db_path: Path = DB_PATH
) -> List[Dict[str, Any]]:
    """Query logs with optional hierarchical filters."""
    conn = get_db_connection(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM llm_logs WHERE 1=1"
    params: List[Any] = []
    
    resolved_conv = conversation_id or session_id
    if resolved_conv:
        query += " AND (conversation_id = ? OR session_id = ? OR COALESCE(conversation_id, session_id, 'conv_default') = ?)"
        params.extend([resolved_conv, resolved_conv, resolved_conv])
    if turn_id:
        query += " AND turn_id = ?"
        params.append(turn_id)
    if request_id:
        query += " AND (request_id = ? OR id = ?)"
        params.extend([request_id, request_id])
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
        # Ensure fallback aliases
        item["request_id"] = item.get("request_id") or item.get("id")
        item["conversation_id"] = item.get("conversation_id") or item.get("session_id")
        item["session_id"] = item["conversation_id"]
        
        for json_col in ["caller_context", "skill_names", "tool_names", "request_messages", "request_tools", "request_params", "response_tool_calls"]:
            if item.get(json_col):
                try:
                    item[json_col] = json.loads(item[json_col])
                except Exception:
                    pass
        results.append(item)
        
    conn.close()
    return results

def query_hierarchical_logs(
    conversation_id: Optional[str] = None,
    limit_conversations: int = 20,
    db_path: Path = DB_PATH
) -> List[Dict[str, Any]]:
    """
    Returns interaction logs organized in a 3-tier hierarchy:
    Conversation ID -> Turn ID -> Requests (LLM Calls).
    """
    conn = get_db_connection(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Fetch unique conversations ordered by most recent activity
    query_convs = """
    SELECT 
        COALESCE(conversation_id, session_id, 'conv_default') as conv_id,
        MIN(timestamp) as started_at,
        MAX(timestamp) as last_activity,
        COUNT(*) as total_requests,
        SUM(prompt_tokens) as total_prompt_tokens,
        SUM(completion_tokens) as total_completion_tokens,
        SUM(total_tokens) as total_tokens,
        MAX(agent_name) as agent_name,
        MAX(model) as model
    FROM llm_logs
    """
    params_convs: List[Any] = []
    if conversation_id:
        query_convs += " WHERE (conversation_id = ? OR session_id = ? OR COALESCE(conversation_id, session_id, 'conv_default') = ?)"
        params_convs.extend([conversation_id, conversation_id, conversation_id])
    
    query_convs += " GROUP BY conv_id ORDER BY last_activity DESC LIMIT ?"
    params_convs.append(limit_conversations)
    
    cursor.execute(query_convs, params_convs)
    conv_rows = cursor.fetchall()
    
    hierarchical_tree = []
    
    for c_row in conv_rows:
        conv_dict = dict(c_row)
        cid = conv_dict["conv_id"]
        
        # 2. Fetch turns for this conversation
        cursor.execute("""
        SELECT 
            COALESCE(turn_id, 'turn_legacy_' || id) as t_id,
            MIN(timestamp) as turn_started_at,
            MAX(timestamp) as turn_ended_at,
            COUNT(*) as request_count,
            SUM(prompt_tokens) as turn_prompt_tokens,
            SUM(completion_tokens) as turn_completion_tokens,
            SUM(total_tokens) as turn_total_tokens,
            SUM(latency_ms) as turn_total_latency_ms,
            MAX(agent_name) as agent_name,
            MAX(model) as model
        FROM llm_logs
        WHERE (conversation_id = ? OR session_id = ? OR COALESCE(conversation_id, session_id, 'conv_default') = ?)
        GROUP BY t_id
        ORDER BY turn_started_at ASC
        """, (cid, cid, cid))
        turn_rows = cursor.fetchall()
        
        turns_list = []
        for t_row in turn_rows:
            turn_dict = dict(t_row)
            tid = turn_dict["t_id"]
            
            # 3. Fetch requests for this turn
            cursor.execute("""
            SELECT * FROM llm_logs 
            WHERE (conversation_id = ? OR session_id = ? OR COALESCE(conversation_id, session_id, 'conv_default') = ?) 
              AND (turn_id = ? OR (turn_id IS NULL AND 'turn_legacy_' || id = ?))
            ORDER BY timestamp ASC
            """, (cid, cid, cid, tid, tid))
            req_rows = cursor.fetchall()
            
            requests_list = []
            for r in req_rows:
                r_item = dict(r)
                r_item["request_id"] = r_item.get("request_id") or r_item.get("id")
                r_item["conversation_id"] = r_item.get("conversation_id") or r_item.get("session_id")
                r_item["turn_id"] = r_item.get("turn_id") or tid
                for json_col in ["caller_context", "skill_names", "tool_names", "request_messages", "request_tools", "request_params", "response_tool_calls"]:
                    if r_item.get(json_col):
                        try:
                            r_item[json_col] = json.loads(r_item[json_col])
                        except Exception:
                            pass
                requests_list.append(r_item)
                
            turn_dict["requests"] = requests_list
            turns_list.append(turn_dict)
            
        conv_dict["turns"] = turns_list
        hierarchical_tree.append(conv_dict)
        
    conn.close()
    return hierarchical_tree

def get_stats(db_path: Path = DB_PATH) -> Dict[str, Any]:
    """Calculate aggregate statistics of LLM usage and tool/skill utilization."""
    conn = get_db_connection(db_path)
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
                
    # Fetch all latencies for percentiles
    cursor.execute("SELECT latency_ms FROM llm_logs WHERE latency_ms IS NOT NULL AND latency_ms > 0 ORDER BY latency_ms ASC")
    lat_rows = cursor.fetchall()
    latencies = [r[0] for r in lat_rows]
    
    if latencies:
        n = len(latencies)
        p50 = latencies[int(n * 0.50)]
        p90 = latencies[min(int(n * 0.90), n - 1)]
        p99 = latencies[min(int(n * 0.99), n - 1)]
        min_lat = latencies[0]
        max_lat = latencies[-1]
    else:
        p50 = p90 = p99 = min_lat = max_lat = 0.0

    avg_lat = row[6] or 0.0
    threshold_latency = max(2000.0, avg_lat * 2.5) if avg_lat > 0 else 3000.0
    cursor.execute("""
        SELECT id, request_id, conversation_id, turn_id, model, latency_ms, total_tokens, status, error_message, timestamp
        FROM llm_logs
        WHERE status = 'ERROR' OR latency_ms >= ? OR total_tokens >= 4000
        ORDER BY timestamp DESC
        LIMIT 10
    """, (threshold_latency,))
    anomaly_rows = cursor.fetchall()
    anomalies = []
    for a in anomaly_rows:
        reasons = []
        if a[7] == "ERROR":
            reasons.append(f"Error: {a[8] or 'Invocation failed'}")
        if a[5] and a[5] >= threshold_latency:
            reasons.append(f"High Latency ({round(a[5], 1)}ms)")
        if a[6] and a[6] >= 4000:
            reasons.append(f"Token Surge ({a[6]} tokens)")
        anomalies.append({
            "id": a[0] or a[1],
            "request_id": a[1] or a[0],
            "conversation_id": a[2],
            "turn_id": a[3],
            "model": a[4],
            "latency_ms": round(a[5] or 0, 1),
            "total_tokens": a[6] or 0,
            "status": a[7],
            "reason": ", ".join(reasons) if reasons else "Anomaly detected",
            "timestamp": a[9]
        })

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
        "percentiles": {
            "p50_latency_ms": round(p50, 2),
            "p90_latency_ms": round(p90, 2),
            "p99_latency_ms": round(p99, 2),
            "min_latency_ms": round(min_lat, 2),
            "max_latency_ms": round(max_lat, 2),
        },
        "anomalies": anomalies,
        "models_usage": models_breakdown,
        "tools_usage_frequency": tool_counts,
        "skills_usage_frequency": skill_counts
    }


def query_logs_for_export(
    limit: int = 500,
    conversation_id: Optional[str] = None,
    model: Optional[str] = None,
    status: Optional[str] = None,
    db_path: Path = DB_PATH
) -> List[Dict[str, Any]]:
    """Query flat audit logs formatted for CSV or JSON export."""
    conn = get_db_connection(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM llm_logs WHERE 1=1"
    params: List[Any] = []
    
    if conversation_id:
        query += " AND (conversation_id = ? OR session_id = ?)"
        params.extend([conversation_id, conversation_id])
    if model:
        query += " AND model = ?"
        params.append(model)
    if status:
        query += " AND status = ?"
        params.append(status)
        
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    results = []
    for r in rows:
        item = dict(r)
        item["request_id"] = item.get("request_id") or item.get("id")
        item["conversation_id"] = item.get("conversation_id") or item.get("session_id")
        results.append(item)
        
    conn.close()
    return results


def init_saved_pipelines(db_path: Path = DB_PATH):
    """Initialize SQLite table for saving visual DAG workflows."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS saved_pipelines (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        nodes TEXT NOT NULL,
        edges TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()


def save_dag_pipeline(pipeline_data: Dict[str, Any], db_path: Path = DB_PATH) -> Dict[str, Any]:
    """Insert or update a saved DAG workflow."""
    init_saved_pipelines(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    p_id = pipeline_data.get("id") or f"pipe_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    name = pipeline_data.get("name", "Untitled Pipeline")
    description = pipeline_data.get("description", "")
    nodes_json = json.dumps(pipeline_data.get("nodes", []))
    edges_json = json.dumps(pipeline_data.get("edges", []))
    now = datetime.now(timezone.utc).isoformat()
    
    cursor.execute("""
    INSERT INTO saved_pipelines (id, name, description, nodes, edges, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        name = excluded.name,
        description = excluded.description,
        nodes = excluded.nodes,
        edges = excluded.edges,
        updated_at = excluded.updated_at
    """, (p_id, name, description, nodes_json, edges_json, now, now))
    
    conn.commit()
    conn.close()
    return {
        "id": p_id,
        "name": name,
        "description": description,
        "nodes": pipeline_data.get("nodes", []),
        "edges": pipeline_data.get("edges", []),
        "updated_at": now
    }


def get_saved_dag_pipelines(db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    """Retrieve all saved visual DAG workflows."""
    init_saved_pipelines(db_path)
    conn = get_db_connection(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM saved_pipelines ORDER BY updated_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "name": r["name"],
            "description": r["description"],
            "nodes": json.loads(r["nodes"]) if r["nodes"] else [],
            "edges": json.loads(r["edges"]) if r["edges"] else [],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"]
        })
    return results


def delete_saved_dag_pipeline(pipeline_id: str, db_path: Path = DB_PATH) -> bool:
    """Delete a saved DAG workflow by ID."""
    init_saved_pipelines(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM saved_pipelines WHERE id = ?", (pipeline_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# ==============================================================================
# Phase 3: Durable State Machine, Checkpointing & Execution Trace Storage
# ==============================================================================

def init_checkpoint_db(db_path: Optional[Path] = None):
    """Initialize SQLite tables for durable workflow DAG execution runs and node checkpoints."""
    target_path = Path(db_path).resolve() if db_path is not None else get_default_db_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS workflow_runs (
        run_id TEXT PRIMARY KEY,
        pipeline_id TEXT,
        workflow_name TEXT NOT NULL,
        status TEXT NOT NULL,
        initial_input TEXT,
        target_model TEXT,
        current_stage INTEGER DEFAULT 0,
        total_stages INTEGER DEFAULT 0,
        nodes TEXT NOT NULL,
        edges TEXT NOT NULL,
        stages TEXT NOT NULL,
        node_outputs TEXT NOT NULL,
        final_output TEXT,
        duration_ms REAL DEFAULT 0.0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS node_checkpoints (
        id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        node_id TEXT NOT NULL,
        stage INTEGER NOT NULL,
        node_type TEXT NOT NULL,
        label TEXT,
        status TEXT NOT NULL,
        step_input TEXT,
        output TEXT,
        duration_ms REAL DEFAULT 0.0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(run_id) REFERENCES workflow_runs(run_id) ON DELETE CASCADE
    )
    """)
    conn.commit()
    conn.close()


def create_workflow_run(run_data: Dict[str, Any], db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Create a new durable workflow run in SQLite."""
    target_path = Path(db_path).resolve() if db_path is not None else get_default_db_path()
    init_checkpoint_db(target_path)
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    
    run_id = run_data.get("run_id") or f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    now = datetime.now(timezone.utc).isoformat()
    
    nodes_json = json.dumps(run_data.get("nodes", [])) if not isinstance(run_data.get("nodes"), str) else run_data.get("nodes")
    edges_json = json.dumps(run_data.get("edges", [])) if not isinstance(run_data.get("edges"), str) else run_data.get("edges")
    stages_json = json.dumps(run_data.get("stages", [])) if not isinstance(run_data.get("stages"), str) else run_data.get("stages")
    outputs_json = json.dumps(run_data.get("node_outputs", {})) if not isinstance(run_data.get("node_outputs"), str) else run_data.get("node_outputs")
    
    cursor.execute("""
    INSERT INTO workflow_runs (
        run_id, pipeline_id, workflow_name, status, initial_input, target_model,
        current_stage, total_stages, nodes, edges, stages, node_outputs,
        final_output, duration_ms, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(run_id) DO UPDATE SET
        status = excluded.status,
        current_stage = excluded.current_stage,
        total_stages = excluded.total_stages,
        nodes = excluded.nodes,
        edges = excluded.edges,
        stages = excluded.stages,
        node_outputs = excluded.node_outputs,
        final_output = excluded.final_output,
        duration_ms = excluded.duration_ms,
        updated_at = excluded.updated_at
    """, (
        run_id,
        run_data.get("pipeline_id"),
        run_data.get("workflow_name", "Untitled Workflow"),
        run_data.get("status", "running"),
        run_data.get("initial_input", ""),
        run_data.get("target_model", ""),
        run_data.get("current_stage", 0),
        run_data.get("total_stages", 0),
        nodes_json,
        edges_json,
        stages_json,
        outputs_json,
        run_data.get("final_output", ""),
        run_data.get("duration_ms", 0.0),
        now,
        now
    ))
    conn.commit()
    conn.close()
    
    result = dict(run_data)
    result["run_id"] = run_id
    result["created_at"] = now
    result["updated_at"] = now
    return result


def update_workflow_run(run_id: str, updates: Dict[str, Any], db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Update fields of an active or paused workflow run."""
    target_path = Path(db_path).resolve() if db_path is not None else get_default_db_path()
    init_checkpoint_db(target_path)
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    
    now = datetime.now(timezone.utc).isoformat()
    fields = []
    values = []
    
    for k, v in updates.items():
        if k in ("nodes", "edges", "stages", "node_outputs") and not isinstance(v, str):
            v = json.dumps(v)
        fields.append(f"{k} = ?")
        values.append(v)
        
    fields.append("updated_at = ?")
    values.append(now)
    values.append(run_id)
    
    query = f"UPDATE workflow_runs SET {', '.join(fields)} WHERE run_id = ?"
    cursor.execute(query, tuple(values))
    conn.commit()
    conn.close()
    return get_workflow_run(run_id, target_path)


def get_workflow_run(run_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieve a single workflow run by ID, deserializing JSON fields."""
    target_path = Path(db_path).resolve() if db_path is not None else get_default_db_path()
    init_checkpoint_db(target_path)
    conn = get_db_connection(target_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM workflow_runs WHERE run_id = ?", (run_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
        
    d = dict(row)
    for json_col in ("nodes", "edges", "stages", "node_outputs"):
        if d.get(json_col):
            try:
                d[json_col] = json.loads(d[json_col])
            except Exception:
                pass
    return d


def get_workflow_runs(limit: int = 50, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieve recent workflow runs ordered by updated_at DESC."""
    target_path = Path(db_path).resolve() if db_path is not None else get_default_db_path()
    init_checkpoint_db(target_path)
    conn = get_db_connection(target_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM workflow_runs ORDER BY updated_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        d = dict(r)
        for json_col in ("nodes", "edges", "stages", "node_outputs"):
            if d.get(json_col):
                try:
                    d[json_col] = json.loads(d[json_col])
                except Exception:
                    pass
        results.append(d)
    return results


def save_node_checkpoint(checkpoint: Dict[str, Any], db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Persist a node execution checkpoint to SQLite."""
    target_path = Path(db_path).resolve() if db_path is not None else get_default_db_path()
    init_checkpoint_db(target_path)
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    
    run_id = checkpoint["run_id"]
    node_id = checkpoint["node_id"]
    chk_id = checkpoint.get("id") or f"chk_{run_id}_{node_id}"
    now = datetime.now(timezone.utc).isoformat()
    
    cursor.execute("""
    INSERT INTO node_checkpoints (
        id, run_id, node_id, stage, node_type, label, status,
        step_input, output, duration_ms, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        status = excluded.status,
        step_input = excluded.step_input,
        output = excluded.output,
        duration_ms = excluded.duration_ms,
        updated_at = excluded.updated_at
    """, (
        chk_id,
        run_id,
        node_id,
        checkpoint.get("stage", 1),
        checkpoint.get("node_type", "agent"),
        checkpoint.get("label", node_id),
        checkpoint.get("status", "COMPLETED"),
        checkpoint.get("step_input", ""),
        checkpoint.get("output", ""),
        checkpoint.get("duration_ms", 0.0),
        checkpoint.get("created_at", now),
        now
    ))
    conn.commit()
    conn.close()
    
    res = dict(checkpoint)
    res["id"] = chk_id
    res["updated_at"] = now
    return res


def get_node_checkpoints(run_id: str, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieve all node checkpoints for a workflow run ordered by stage and creation."""
    target_path = Path(db_path).resolve() if db_path is not None else get_default_db_path()
    init_checkpoint_db(target_path)
    conn = get_db_connection(target_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM node_checkpoints WHERE run_id = ? ORDER BY stage ASC, created_at ASC
    """, (run_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==============================================================================
# Persistent HITL Approval Storage
# ==============================================================================

def init_hitl_db(db_path: Optional[Path] = None):
    """Initialize SQLite tables for persistent HITL approval requests."""
    target_path = Path(db_path).resolve() if db_path is not None else get_default_db_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hitl_requests (
        request_id TEXT PRIMARY KEY,
        tool_name TEXT NOT NULL,
        arguments TEXT NOT NULL,
        risk_level TEXT NOT NULL,
        description TEXT,
        status TEXT NOT NULL,
        created_at REAL NOT NULL,
        timeout_seconds REAL NOT NULL,
        resolved_at REAL,
        resolved_by TEXT
    )
    """)
    conn.commit()
    conn.close()


def save_hitl_request(req_data: Dict[str, Any], db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Insert or update a HITL approval request in SQLite."""
    target_path = Path(db_path).resolve() if db_path is not None else get_default_db_path()
    init_hitl_db(target_path)
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    
    args_json = json.dumps(req_data.get("arguments", {})) if not isinstance(req_data.get("arguments"), str) else req_data.get("arguments")
    
    cursor.execute("""
    INSERT INTO hitl_requests (
        request_id, tool_name, arguments, risk_level, description,
        status, created_at, timeout_seconds, resolved_at, resolved_by
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(request_id) DO UPDATE SET
        status = excluded.status,
        resolved_at = excluded.resolved_at,
        resolved_by = excluded.resolved_by
    """, (
        req_data["request_id"],
        req_data.get("tool_name", ""),
        args_json,
        req_data.get("risk_level", "medium"),
        req_data.get("description", ""),
        req_data.get("status", "pending"),
        req_data.get("created_at", time.time()),
        req_data.get("timeout_seconds", 60.0),
        req_data.get("resolved_at"),
        req_data.get("resolved_by")
    ))
    conn.commit()
    conn.close()
    return req_data


def get_hitl_requests(status_filter: Optional[str] = None, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieve persisted HITL requests from SQLite."""
    target_path = Path(db_path).resolve() if db_path is not None else get_default_db_path()
    init_hitl_db(target_path)
    conn = get_db_connection(target_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if status_filter:
        cursor.execute("SELECT * FROM hitl_requests WHERE status = ? ORDER BY created_at DESC", (status_filter,))
    else:
        cursor.execute("SELECT * FROM hitl_requests ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        d = dict(r)
        if d.get("arguments"):
            try:
                d["arguments"] = json.loads(d["arguments"])
            except Exception:
                pass
        results.append(d)
    return results


def update_hitl_status(
    request_id: str, 
    status: str, 
    resolved_by: Optional[str] = None, 
    resolved_at: Optional[float] = None, 
    db_path: Optional[Path] = None,
    **kwargs: Any
) -> bool:
    """Update status of a HITL request in SQLite."""
    target_path = Path(db_path).resolve() if db_path is not None else get_default_db_path()
    init_hitl_db(target_path)
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    res_time = resolved_at if resolved_at is not None else time.time()
    resolver = resolved_by or kwargs.get("approved_by") or kwargs.get("denied_by")
    cursor.execute("""
    UPDATE hitl_requests SET status = ?, resolved_by = ?, resolved_at = ? WHERE request_id = ?
    """, (status, resolver, res_time, request_id))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


# ==============================================================================
# Smart Router Storage & Traces
# ==============================================================================

def init_smart_router_db(db_path: Optional[Path] = None):
    """Initialize SQLite tables for Smart Router call logs and traces."""
    target_path = Path(db_path).resolve() if db_path is not None else get_default_db_path()
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS smart_router_logs (
        id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        prompt TEXT NOT NULL,
        reasoning_model TEXT NOT NULL,
        reasoning_raw_response TEXT,
        routing_decision TEXT,
        category TEXT,
        confidence REAL,
        threshold REAL,
        threshold_met INTEGER DEFAULT 1,
        selected_model TEXT NOT NULL,
        target_model TEXT NOT NULL,
        target_prompt TEXT NOT NULL,
        target_response TEXT,
        stage1_latency_ms REAL DEFAULT 0.0,
        stage2_latency_ms REAL DEFAULT 0.0,
        total_latency_ms REAL DEFAULT 0.0,
        prompt_tokens INTEGER DEFAULT 0,
        completion_tokens INTEGER DEFAULT 0,
        total_tokens INTEGER DEFAULT 0,
        status TEXT DEFAULT 'SUCCESS',
        error_message TEXT
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_smart_router_ts ON smart_router_logs(timestamp DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_smart_router_cat ON smart_router_logs(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_smart_router_target ON smart_router_logs(target_model)")
    conn.commit()
    conn.close()


def save_smart_router_log(record: Dict[str, Any], db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Persist a complete 2-stage Smart Router call trace to SQLite."""
    target_path = Path(db_path).resolve() if db_path is not None else get_default_db_path()
    init_smart_router_db(target_path)
    conn = get_db_connection(target_path)
    cursor = conn.cursor()

    log_id = record.get("id") or f"sr_{uuid.uuid4().hex[:12]}"
    record["id"] = log_id
    if "timestamp" not in record:
        record["timestamp"] = datetime.now(timezone.utc).isoformat()

    decision_json = record.get("routing_decision")
    if isinstance(decision_json, (dict, list)):
        decision_str = json.dumps(decision_json)
    else:
        decision_str = str(decision_json) if decision_json else "{}"

    cursor.execute("""
    INSERT INTO smart_router_logs (
        id, timestamp, prompt, reasoning_model, reasoning_raw_response,
        routing_decision, category, confidence, threshold, threshold_met,
        selected_model, target_model, target_prompt, target_response,
        stage1_latency_ms, stage2_latency_ms, total_latency_ms,
        prompt_tokens, completion_tokens, total_tokens,
        status, error_message
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        log_id,
        record.get("timestamp"),
        record.get("prompt", ""),
        record.get("reasoning_model", ""),
        record.get("reasoning_raw_response", ""),
        decision_str,
        record.get("category", "general_qa"),
        record.get("confidence", 1.0),
        record.get("threshold", 0.7),
        1 if record.get("threshold_met", True) else 0,
        record.get("selected_model", ""),
        record.get("target_model", ""),
        record.get("target_prompt", ""),
        record.get("target_response", ""),
        record.get("stage1_latency_ms", 0.0),
        record.get("stage2_latency_ms", 0.0),
        record.get("total_latency_ms", 0.0),
        record.get("prompt_tokens", 0),
        record.get("completion_tokens", 0),
        record.get("total_tokens", 0),
        record.get("status", "SUCCESS"),
        record.get("error_message")
    ))
    conn.commit()
    conn.close()
    return record


def query_smart_router_logs(
    limit: int = 50,
    offset: int = 0,
    category: Optional[str] = None,
    model: Optional[str] = None,
    search: Optional[str] = None,
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Retrieve filtered and paginated Smart Router traces."""
    target_path = Path(db_path).resolve() if db_path is not None else get_default_db_path()
    init_smart_router_db(target_path)
    conn = get_db_connection(target_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    conditions = []
    params = []

    if category:
        conditions.append("category = ?")
        params.append(category)
    if model:
        conditions.append("(target_model = ? OR reasoning_model = ?)")
        params.extend([model, model])
    if search:
        conditions.append("(prompt LIKE ? OR target_response LIKE ? OR category LIKE ?)")
        wildcard = f"%{search}%"
        params.extend([wildcard, wildcard, wildcard])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Count total
    cursor.execute(f"SELECT COUNT(*) FROM smart_router_logs {where_clause}", params)
    total = cursor.fetchone()[0]

    # Fetch rows
    query = f"SELECT * FROM smart_router_logs {where_clause} ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    cursor.execute(query, params + [limit, offset])
    rows = cursor.fetchall()
    conn.close()

    logs = []
    for r in rows:
        d = dict(r)
        d["threshold_met"] = bool(d.get("threshold_met", 1))
        if d.get("routing_decision"):
            try:
                d["routing_decision"] = json.loads(d["routing_decision"])
            except Exception:
                pass
        logs.append(d)

    return {
        "logs": logs,
        "total": total,
        "limit": limit,
        "offset": offset
    }


def get_smart_router_log(log_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieve a single Smart Router trace by ID."""
    target_path = Path(db_path).resolve() if db_path is not None else get_default_db_path()
    init_smart_router_db(target_path)
    conn = get_db_connection(target_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM smart_router_logs WHERE id = ?", (log_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["threshold_met"] = bool(d.get("threshold_met", 1))
    if d.get("routing_decision"):
        try:
            d["routing_decision"] = json.loads(d["routing_decision"])
        except Exception:
            pass
    return d


def clear_smart_router_logs(db_path: Optional[Path] = None) -> int:
    """Clear all Smart Router call traces."""
    target_path = Path(db_path).resolve() if db_path is not None else get_default_db_path()
    init_smart_router_db(target_path)
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM smart_router_logs")
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


