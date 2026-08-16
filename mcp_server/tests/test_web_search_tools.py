"""Unit tests for live DDGS web search tool, curated index, ranking, and fallbacks."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.web_search_tools import web_search, WEB_INDEX

def test_web_search_live_ddgs():
    # Test real-world live DuckDuckGo query
    res = web_search(query="Python programming language", max_results=3, use_live_search=True)
    assert res["success"] is True
    assert res["results_count"] > 0
    assert "results" in res
    assert any("python" in r["title"].lower() or "python" in r["snippet"].lower() for r in res["results"])

def test_web_search_offline_curated_index():
    queries = [
        "Tokyo ramen shops",
        "Paris croissants and bistros",
        "party games for friends",
        "15-minute creamy tuscan garlic pasta",
        "50/30/20 budget method"
    ]
    for q in queries:
        res = web_search(query=q, use_live_search=False)
        assert res["success"] is True
        assert res["results_count"] > 0
        assert len(res["results"]) <= 3

def test_web_search_list_and_dict_payloads():
    # List of tokens
    res_list = web_search(query=["paris", "bistro", "eiffel"], use_live_search=False)
    assert res_list["success"] is True
    assert res_list["results_count"] > 0

    # Dict payload
    res_dict = web_search(query={"destination": "Tokyo", "food": "sushi"}, use_live_search=False)
    assert res_dict["success"] is True
    assert res_dict["results_count"] > 0

def test_web_search_curated_fallback():
    # Force offline search for unknown query to verify fallback generation
    res = web_search(query="rare vintage telescope repair", use_live_search=False)
    assert res["success"] is True
    assert res["results_count"] > 0
    assert "duckduckgo.com" in res["results"][0]["url"]

def test_web_search_empty_query():
    res = web_search(query="")
    assert res["success"] is False
    assert "error" in res

def test_web_index_integrity():
    for item in WEB_INDEX:
        assert "query_keywords" in item
        assert "title" in item
        assert "url" in item
        assert "snippet" in item
        assert "category" in item
