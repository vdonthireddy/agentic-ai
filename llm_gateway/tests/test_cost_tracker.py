"""Tests for the per-model cost tracker."""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from cost_tracker import CostTracker, DEFAULT_PRICING


class TestCostCalculation:
    @pytest.fixture
    def tracker(self):
        return CostTracker()

    def test_openai_cost(self, tracker):
        cost = tracker.calculate_cost("gpt-4o", prompt_tokens=1000, completion_tokens=500)
        # gpt-4o: $2.50/1M input, $10.00/1M output
        expected = (1000 / 1_000_000) * 2.50 + (500 / 1_000_000) * 10.00
        assert abs(cost - expected) < 1e-6

    def test_ollama_is_free(self, tracker):
        cost = tracker.calculate_cost("ollama/gemma2:2b", prompt_tokens=10000, completion_tokens=5000)
        assert cost == 0.0

    def test_ollama_chat_is_free(self, tracker):
        cost = tracker.calculate_cost("ollama_chat/llama3", prompt_tokens=10000, completion_tokens=5000)
        assert cost == 0.0

    def test_unknown_model_is_free(self, tracker):
        cost = tracker.calculate_cost("unknown-provider/unknown-model", prompt_tokens=1000, completion_tokens=500)
        assert cost == 0.0

    def test_anthropic_cost(self, tracker):
        cost = tracker.calculate_cost("anthropic/claude-3.5-sonnet", prompt_tokens=2000, completion_tokens=1000)
        expected = (2000 / 1_000_000) * 3.00 + (1000 / 1_000_000) * 15.00
        assert abs(cost - expected) < 1e-6

    def test_zero_tokens(self, tracker):
        cost = tracker.calculate_cost("gpt-4o", prompt_tokens=0, completion_tokens=0)
        assert cost == 0.0

    def test_prefix_matching(self, tracker):
        # "gpt-4o" should match "openai/gpt-4o" pricing
        cost = tracker.calculate_cost("gpt-4o", prompt_tokens=1000000, completion_tokens=0)
        assert cost > 0


class TestCostSummary:
    @pytest.fixture
    def db_path(self, tmp_path):
        db = tmp_path / "test_costs.db"
        conn = sqlite3.connect(str(db))
        conn.execute("""
            CREATE TABLE llm_logs (
                id TEXT PRIMARY KEY,
                model TEXT,
                caller_id TEXT,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER,
                cost_usd REAL DEFAULT 0.0,
                timestamp TEXT,
                status TEXT DEFAULT 'SUCCESS'
            )
        """)
        conn.execute("""
            INSERT INTO llm_logs (id, model, caller_id, prompt_tokens, completion_tokens, total_tokens, cost_usd, timestamp)
            VALUES ('req1', 'gpt-4o', 'user1', 1000, 500, 1500, 0.0075, '2026-08-18T10:00:00Z')
        """)
        conn.execute("""
            INSERT INTO llm_logs (id, model, caller_id, prompt_tokens, completion_tokens, total_tokens, cost_usd, timestamp)
            VALUES ('req2', 'ollama/gemma2:2b', 'user1', 2000, 1000, 3000, 0.0, '2026-08-18T10:01:00Z')
        """)
        conn.commit()
        conn.close()
        return db

    def test_summary_with_cost_column(self, db_path):
        tracker = CostTracker()
        summary = tracker.get_cost_summary(db_path)
        assert summary["total_cost_usd"] > 0
        assert summary["paid_calls"] == 1
        assert len(summary["by_model"]) >= 1

    def test_forecast(self, db_path):
        tracker = CostTracker()
        forecast = tracker.get_cost_forecast(db_path, days_ahead=30)
        assert "projected_cost_usd" in forecast
        assert "daily_average_usd" in forecast
        assert forecast["lookback_days"] == 7


class TestPricingTable:
    def test_default_pricing_has_entries(self):
        assert len(DEFAULT_PRICING) > 0
        assert "gpt-4o" in DEFAULT_PRICING or "openai/gpt-4o" in DEFAULT_PRICING

    def test_update_pricing(self):
        tracker = CostTracker()
        tracker.update_pricing("custom/model", 1.0, 2.0)
        assert "custom/model" in tracker.pricing
        cost = tracker.calculate_cost("custom/model", prompt_tokens=1_000_000, completion_tokens=1_000_000)
        assert cost == 3.0

    def test_get_pricing_table(self):
        tracker = CostTracker()
        table = tracker.get_pricing_table()
        assert isinstance(table, dict)
        assert len(table) > 0
