"""Integration tests for Phase 2 API endpoints."""

import pytest
import json
import sys
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app


@pytest.fixture
def client():
    return TestClient(app)


class TestPhase2Endpoints:
    def test_get_costs(self, client):
        response = client.get("/api/costs")
        assert response.status_code == 200
        data = response.json()
        assert "total_cost_usd" in data
        assert "by_model" in data

    def test_get_cost_forecast(self, client):
        response = client.get("/api/costs/forecast?days=30")
        assert response.status_code == 200
        data = response.json()
        assert "projected_cost_usd" in data
        assert data["projected_days"] == 30

    def test_get_pricing_table(self, client):
        response = client.get("/api/costs/pricing")
        assert response.status_code == 200
        data = response.json()
        assert "pricing" in data
        assert len(data["pricing"]) > 0

    def test_get_rate_limit_status(self, client):
        response = client.get("/api/rate-limit/status")
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert "global_rpm_limit" in data

    def test_hitl_pending_and_rules(self, client):
        rules_resp = client.get("/api/hitl/rules")
        assert rules_resp.status_code == 200
        rules_data = rules_resp.json()
        assert "rules" in rules_data

        pending_resp = client.get("/api/hitl/pending")
        assert pending_resp.status_code == 200
        pending_data = pending_resp.json()
        assert "pending" in pending_data

    def test_memory_lifecycle_endpoints(self, client):
        # 1. Store
        store_resp = client.post("/api/memory/store", json={
            "content": "Phase 2 Integration Test Memory",
            "namespace": "test_ns"
        })
        assert store_resp.status_code == 200
        store_data = store_resp.json()
        assert store_data["status"] == "success"
        mem_id = store_data["memory_id"]

        # 2. List
        list_resp = client.get("/api/memory/list?namespace=test_ns")
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["count"] >= 1

        # 3. Recall
        recall_resp = client.post("/api/memory/recall", json={
            "query": "Phase Integration Test",
            "namespace": "test_ns",
            "top_k": 3
        })
        assert recall_resp.status_code == 200
        recall_data = recall_resp.json()
        assert recall_data["status"] == "success"

        # 4. Delete
        del_resp = client.delete(f"/api/memory/{mem_id}")
        assert del_resp.status_code == 200

    def test_voice_speak_endpoint(self, client):
        response = client.post("/api/voice/speak", json={
            "text": "Testing voice synthesis endpoint",
            "voice": "nova",
            "speed": 1.0
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["voice"] == "nova"

    def test_voice_transcribe_endpoint(self, client):
        import base64
        sample_b64 = base64.b64encode(b"RIFFdummydata").decode("utf-8")
        response = client.post("/api/voice/transcribe", json={
            "audio_base64": sample_b64,
            "language": "en"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
