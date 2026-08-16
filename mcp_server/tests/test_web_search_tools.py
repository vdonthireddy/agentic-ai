"""Unit tests for web search tool, keyword matching, ranking, and fallbacks."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.web_search_tools import web_search, WEB_INDEX

def test_web_search_travel_and_recipes():
    queries = [
        "Tokyo ramen shops",
        "Paris croissants and bistros",
        "party games for friends",
        "15-minute creamy tuscan garlic pasta",
        "50/30/20 budget method"
    ]
    for q in queries:
        res = web_search(query=q)
        assert res["success"] is True
        assert res["results_count"] > 0
        assert len(res["results"]) <= 3

def test_web_search_list_and_dict_payloads():
    # List of tokens
    res_list = web_search(query=["paris", "bistro", "eiffel"])
    assert res_list["success"] is True
    assert res_list["results_count"] > 0

    # Dict payload
    res_dict = web_search(query={"destination": "Tokyo", "food": "sushi"})
    assert res_dict["success"] is True
    assert res_dict["results_count"] > 0

def test_web_search_fallback():
    res = web_search(query="rare vintage telescope repair")
    assert res["success"] is True
    assert res["results_count"] > 0
    assert "google.com/search" in res["results"][0]["url"]

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
