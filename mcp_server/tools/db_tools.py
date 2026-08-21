"""Database exploration tool for executing safe read-only SQL queries against SQLite databases in the workspace."""

import sqlite3
import json
from typing import Dict, Any, Optional
from pathlib import Path

def execute_readonly_sql(
    query: str = "",
    sql: str = "",
    statement: str = "",
    db_path: str = "./workspace/company.db",
    database: str = "",
    path: str = "",
    max_rows: int = 25,
    limit: int = 25,
    **kwargs: Any
) -> Dict[str, Any]:
    """
    Execute safe read-only SQL queries (SELECT, PRAGMA, EXPLAIN) against SQLite database.
    """
    actual_query = (query or sql or statement or "").strip()
    if not actual_query:
        return {"status": "error", "message": "No SQL query provided."}

    target_db = database or path or db_path or "./workspace/company.db"
    row_limit = max_rows or limit or 25

    # Enforce read-only constraint
    clean_sql = actual_query.strip().upper()
    allowed_prefixes = ("SELECT", "PRAGMA", "EXPLAIN", "WITH")
    if not any(clean_sql.startswith(prefix) for prefix in allowed_prefixes):
        return {
            "status": "error",
            "message": "Only read-only queries (SELECT, PRAGMA, EXPLAIN, WITH) are permitted."
        }

    # Block destructive keywords inside CTEs or comments
    disallowed_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "ATTACH", "DETACH", "REINDEX", "VACUUM"]
    for kw in disallowed_keywords:
        # Simple word boundary check
        tokens = [t.strip(",;()") for t in clean_sql.split()]
        if kw in tokens:
            return {
                "status": "error",
                "message": f"Destructive keyword '{kw}' is not allowed in read-only SQL tool."
            }

    db_file = Path(target_db).resolve()
    if not db_file.exists():
        # Auto-create a sample workspace database if pointing to default company.db
        if "company.db" in str(db_file):
            db_file.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    department TEXT NOT NULL,
                    salary INTEGER NOT NULL,
                    hired_date TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY,
                    project_name TEXT NOT NULL,
                    budget INTEGER NOT NULL,
                    lead_id INTEGER,
                    status TEXT NOT NULL
                )
            """)
            cursor.execute("SELECT count(*) FROM employees")
            if cursor.fetchone()[0] == 0:
                cursor.executemany("""
                    INSERT INTO employees (name, role, department, salary, hired_date) VALUES (?, ?, ?, ?, ?)
                """, [
                    ("Sarah Connor", "VP Engineering", "Engineering", 195000, "2022-03-15"),
                    ("Alex Chen", "Staff AI Engineer", "AI/ML", 175000, "2023-01-10"),
                    ("Elena Rostova", "Lead Product Designer", "Design", 145000, "2022-08-01"),
                    ("Marcus Brody", "Senior DevOps Architect", "Infrastructure", 160000, "2021-11-20"),
                    ("Priya Patel", "Senior Legal Counsel", "Legal", 180000, "2023-05-12")
                ])
                cursor.executemany("""
                    INSERT INTO projects (project_name, budget, lead_id, status) VALUES (?, ?, ?, ?)
                """, [
                    ("Project Apollo Agent Swarm", 250000, 2, "Active"),
                    ("Cloud Migration 2026", 180000, 4, "In Progress"),
                    ("Design System 3.0", 85000, 3, "Completed")
                ])
                conn.commit()
            conn.close()
        else:
            db_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        conn = sqlite3.connect(str(db_file))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(actual_query)
        rows = [dict(r) for r in cursor.fetchmany(row_limit)]
        conn.close()
        return {
            "status": "success",
            "database": str(target_db),
            "query": actual_query,
            "row_count": len(rows),
            "rows": rows
        }
    except Exception as e:
        return {"status": "error", "message": f"SQL Execution Failed: {str(e)}"}
