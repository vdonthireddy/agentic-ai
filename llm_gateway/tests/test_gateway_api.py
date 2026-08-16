"""Unit tests for FastAPI endpoints in LLM Gateway."""

import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app

client = TestClient(app)

def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "default_model" in data

def test_models_endpoint():
    res = client.get("/v1/models")
    assert res.status_code == 200
    data = res.json()
    assert "data" in data
    assert len(data["data"]) > 0

def test_logs_endpoint():
    res = client.get("/v1/logs?limit=5")
    assert res.status_code == 200
    data = res.json()
    assert "logs" in data
    assert "count" in data

def test_stats_endpoint():
    res = client.get("/v1/stats")
    assert res.status_code == 200
    data = res.json()
    assert "total_calls" in data
    assert "token_usage" in data

def test_dashboard_static_endpoint():
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]

def test_chat_clear_endpoint():
    res = client.post("/api/chat/clear", json={"session_id": "test_session_123"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["session_id"] == "test_session_123"

def test_chat_missing_message_validation():
    res = client.post("/api/chat", json={"session_id": "test_session"})
    assert res.status_code == 422
