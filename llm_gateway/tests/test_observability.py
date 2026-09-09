"""Unit tests for advanced observability, Prometheus metrics, log exports, and SSE streaming."""

import pytest
import sys
import json
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from llm_gateway.app import app
from llm_gateway.logger import audit_logger
from llm_gateway.config import config
from llm_gateway.db import save_log_entry, get_stats, query_logs_for_export

client = TestClient(app)

def test_prometheus_metrics_endpoint():
    """Verify Prometheus scrape endpoint returns valid text format metrics."""
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "text/plain" in res.headers.get("content-type", "")
    content = res.text

    # Verify standard metric names exist
    assert "llm_gateway_requests_total" in content
    assert "llm_gateway_tokens_total" in content
    assert "llm_gateway_latency_ms_avg" in content
    assert "llm_gateway_latency_ms_p50" in content
    assert "llm_gateway_latency_ms_p90" in content
    assert "llm_gateway_latency_ms_p99" in content
    assert "llm_gateway_cost_usd_total" in content
    assert "llm_gateway_system_cpu_percent" in content


def test_stats_percentiles_and_anomalies():
    """Verify get_stats returns P50/P90/P99 latency percentiles and anomaly detection."""
    # Insert test logs
    audit_logger.log_call(
        caller_id="test_user",
        agent_name="telemetry_test_agent",
        session_id="session_telemetry_test",
        caller_context={},
        model="ollama/test-model",
        skill_names=["test_skill"],
        tool_names=["test_tool"],
        request_messages=[{"role": "user", "content": "hello"}],
        request_tools=[],
        request_params={},
        response_content="world",
        response_tool_calls=[],
        prompt_tokens=50,
        completion_tokens=25,
        total_tokens=75,
        latency_ms=120.5,
        status="SUCCESS"
    )

    # Insert an anomaly log with high latency
    audit_logger.log_call(
        caller_id="test_user",
        agent_name="telemetry_test_agent",
        session_id="session_telemetry_test",
        caller_context={},
        model="ollama/slow-model",
        skill_names=[],
        tool_names=[],
        request_messages=[{"role": "user", "content": "slow"}],
        request_tools=[],
        request_params={},
        response_content="slow response",
        response_tool_calls=[],
        prompt_tokens=4500,
        completion_tokens=50,
        total_tokens=4550,
        latency_ms=6500.0,
        status="ERROR",
        error_message="Simulated connection timeout"
    )

    res = client.get("/v1/stats")
    assert res.status_code == 200
    data = res.json()

    assert "percentiles" in data
    assert "p50_latency_ms" in data["percentiles"]
    assert "p90_latency_ms" in data["percentiles"]
    assert "p99_latency_ms" in data["percentiles"]
    assert data["percentiles"]["p50_latency_ms"] >= 0.0

    assert "anomalies" in data
    assert isinstance(data["anomalies"], list)
    # The error or high token log should appear in anomalies
    anomaly_found = any(a.get("status") == "ERROR" or "slow" in a.get("model", "") for a in data["anomalies"])
    assert anomaly_found, "Expected error log to be flagged in anomalies"


def test_logs_export_json():
    """Verify /v1/logs/export with json format returns valid JSON array."""
    res = client.get("/v1/logs/export?format=json&limit=10")
    assert res.status_code == 200
    assert "application/json" in res.headers.get("content-type", "")
    assert "attachment" in res.headers.get("content-disposition", "")
    
    logs = res.json()
    assert isinstance(logs, list)
    if len(logs) > 0:
        first = logs[0]
        assert "id" in first or "request_id" in first
        assert "model" in first
        assert "timestamp" in first


def test_logs_export_csv():
    """Verify /v1/logs/export with csv format returns valid CSV with header."""
    res = client.get("/v1/logs/export?format=csv&limit=10")
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")
    assert "attachment" in res.headers.get("content-disposition", "")
    
    lines = res.text.strip().splitlines()
    assert len(lines) >= 1
    header = lines[0]
    assert "id" in header
    assert "model" in header
    assert "latency_ms" in header
    assert "total_tokens" in header


def test_audit_logger_pubsub_broadcasting():
    """Verify audit_logger subscribe, broadcast, and unsubscribe behavior."""
    q = audit_logger.subscribe()
    assert q in audit_logger._subscribers

    test_record = {"id": "test_broadcast_123", "model": "test_model", "status": "SUCCESS"}
    audit_logger._broadcast(test_record)

    assert not q.empty()
    item = q.get_nowait()
    assert item["id"] == "test_broadcast_123"

    audit_logger.unsubscribe(q)
    assert q not in audit_logger._subscribers


def test_logs_stream_endpoint_handshake():
    """Verify /v1/logs/stream SSE returns event-stream and initial handshake."""
    res = client.get("/v1/logs/stream?max_events=1")
    assert res.status_code == 200
    assert "text/event-stream" in res.headers.get("content-type", "")
    assert "event: connected" in res.text
