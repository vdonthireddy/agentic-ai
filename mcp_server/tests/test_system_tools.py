"""Unit tests for system metrics and knowledge search tools."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.system_tools import get_system_metrics
from tools.search_tools import search_knowledge

def test_get_system_metrics():
    metrics = get_system_metrics()
    assert "cpu" in metrics
    assert "memory" in metrics
    assert "os" in metrics
    assert "disk" in metrics
    assert isinstance(metrics["cpu"]["usage_percent"], (int, float))
    assert metrics["memory"]["total_gb"] > 0

def test_search_knowledge():
    res = search_knowledge("Model Context Protocol")
    assert res["results_found"] > 0
    assert any("MCP" in m["topic"] or "Protocol" in m["content"] for m in res["matches"])
