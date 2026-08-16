"""Unit tests for internal knowledge base search tools."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.search_tools import (
    search_knowledge,
    search_knowledge_base,
    knowledge_base_search,
    KNOWLEDGE_BASE
)

def test_search_knowledge_known_topics():
    topics = ["MCP Protocol", "LiteLLM", "Ollama Local Models", "AI Agent Loop"]
    for t in topics:
        res = search_knowledge(t)
        assert res["success"] is True
        assert res["results_found"] > 0
        assert any(t.lower() in m["topic"].lower() for m in res["matches"])

def test_search_knowledge_aliases():
    res1 = search_knowledge_base("LiteLLM")
    res2 = knowledge_base_search("LiteLLM")
    assert res1["success"] is True
    assert res2["success"] is True
    assert res1["results_found"] == res2["results_found"]

def test_search_knowledge_list_and_dict_payload():
    res_list = search_knowledge(["fastmcp", "tools"])
    assert res_list["success"] is True
    assert res_list["results_found"] > 0

    res_dict = search_knowledge({"term": "react agent reasoning"})
    assert res_dict["success"] is True
    assert res_dict["results_found"] > 0

def test_search_knowledge_no_match_notice():
    res = search_knowledge("quantum warp drive astrophysics")
    assert res["success"] is True
    assert res["results_found"] == 0
    assert "matches" in res
    assert "No direct match found" in res["matches"][0]["content"]

def test_knowledge_base_items_integrity():
    for item in KNOWLEDGE_BASE:
        assert "topic" in item
        assert "keywords" in item
        assert isinstance(item["keywords"], list)
        assert "content" in item
