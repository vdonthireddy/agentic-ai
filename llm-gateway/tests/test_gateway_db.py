"""Unit tests for SQLite database and query logic in LLM Gateway."""

import pytest
import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db import init_db, save_log_entry, query_logs, get_stats

@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    init_db(db_path)
    yield db_path
    if db_path.exists():
        db_path.unlink()

def test_db_save_and_query(temp_db):
    entry = {
        "id": "call_unit_1",
        "caller_id": "test_caller",
        "agent_name": "TestAgent",
        "session_id": "sess_1",
        "caller_context": {"env": "unit_test"},
        "model": "ollama/qwen2.5-coder:7b",
        "skill_names": ["data_analysis_skill"],
        "tool_names": ["calculate", "execute_python"],
        "request_messages": [{"role": "user", "content": "What is 2+2?"}],
        "response_content": "4",
        "prompt_tokens": 50,
        "completion_tokens": 10,
        "total_tokens": 60,
        "latency_ms": 150.0,
        "status": "SUCCESS"
    }
    save_log_entry(entry, db_path=temp_db)

    logs = query_logs(session_id="sess_1", db_path=temp_db)
    assert len(logs) == 1
    assert logs[0]["id"] == "call_unit_1"
    assert logs[0]["agent_name"] == "TestAgent"
    assert logs[0]["total_tokens"] == 60
    assert logs[0]["tool_names"] == ["calculate", "execute_python"]

def test_db_get_stats(temp_db):
    entry1 = {
        "id": "call_1", "model": "ollama/llama3.2", "prompt_tokens": 100,
        "completion_tokens": 20, "total_tokens": 120, "latency_ms": 200.0,
        "status": "SUCCESS", "tool_names": ["calculate"], "skill_names": ["data_analysis_skill"]
    }
    entry2 = {
        "id": "call_2", "model": "ollama/llama3.2", "prompt_tokens": 50,
        "completion_tokens": 10, "total_tokens": 60, "latency_ms": 100.0,
        "status": "ERROR", "tool_names": ["execute_python"], "skill_names": []
    }
    save_log_entry(entry1, db_path=temp_db)
    save_log_entry(entry2, db_path=temp_db)

    stats = get_stats(db_path=temp_db)
    assert stats["total_calls"] == 2
    assert stats["successful_calls"] == 1
    assert stats["error_calls"] == 1
    assert stats["token_usage"]["total_tokens"] == 180
    assert stats["tools_usage_frequency"]["calculate"] == 1
    assert stats["tools_usage_frequency"]["execute_python"] == 1
