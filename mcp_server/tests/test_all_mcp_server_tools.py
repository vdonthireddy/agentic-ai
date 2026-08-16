"""Unit tests for all FastMCP tool wrappers registered in mcp_server/server.py."""

import json
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import (
    tool_calculator,
    tool_calculate,
    tool_calculate_tip_and_split,
    tool_tip_calculator,
    tool_split_bill,
    tool_weather,
    tool_web_search,
    tool_product_knowledge,
    tool_workspace_file_ops,
    tool_knowledge_base_search,
    tool_travel_planner_skill,
    tool_shopping_assistant_skill,
    tool_party_planner_skill,
    tool_chef_meal_planner_skill,
    resource_skills_catalog
)

def test_server_tool_calculator_and_aliases():
    res1 = json.loads(tool_calculator(expression="50 * 4 + 10"))
    assert res1["success"] is True
    assert res1["result"] == 210.0

    res2 = json.loads(tool_calculate(expression="100 / 5"))
    assert res2["success"] is True
    assert res2["result"] == 20.0

def test_server_tool_tip_and_split_and_aliases():
    res1 = json.loads(tool_calculate_tip_and_split(total=100.0, tip_percentage=0.20, num_people=4))
    assert res1["success"] is True
    assert res1["total_with_tip"] == 120.0
    assert res1["per_person"] == 30.0

    res2 = json.loads(tool_tip_calculator(total=80.0, tip_percentage=0.15, num_people=2))
    assert res2["success"] is True

    res3 = json.loads(tool_split_bill(bill=50.0, tip_percent=0.10, people=2))
    assert res3["success"] is True

def test_server_tool_weather():
    res = json.loads(tool_weather(location="Tokyo"))
    assert res["success"] is True
    assert "Tokyo" in res["location"]

def test_server_tool_web_search():
    res = json.loads(tool_web_search(query="best ramen in Tokyo"))
    assert res["success"] is True
    assert res["results_count"] > 0

def test_server_tool_product_knowledge():
    res = json.loads(tool_product_knowledge(query="espresso maker"))
    assert res["success"] is True
    assert res["items_found"] > 0

def test_server_tool_workspace_file_ops():
    # Write
    write_res = json.loads(tool_workspace_file_ops(action="write", filename="server_tool_test.txt", content="MCP Test Content"))
    assert write_res["success"] is True

    # Read
    read_res = json.loads(tool_workspace_file_ops(action="read", filename="server_tool_test.txt"))
    assert read_res["success"] is True
    assert "MCP Test Content" in read_res["content"]

    # List
    list_res = json.loads(tool_workspace_file_ops(action="list"))
    assert list_res["success"] is True

    # Delete
    del_res = json.loads(tool_workspace_file_ops(action="delete", filename="server_tool_test.txt"))
    assert del_res["success"] is True

def test_server_tool_knowledge_base_search():
    res = json.loads(tool_knowledge_base_search(query="LiteLLM"))
    assert res["success"] is True
    assert res["results_found"] > 0

def test_server_tool_domain_skills():
    travel = json.loads(tool_travel_planner_skill(destination="Honolulu", trip_length="5 days"))
    assert travel["success"] is True
    assert "Honolulu" in travel["instructions"]

    shopping = json.loads(tool_shopping_assistant_skill(shopper_goal="Find wireless headphones"))
    assert shopping["success"] is True
    assert "headphones" in shopping["goal"]

    party = json.loads(tool_party_planner_skill(party_theme="Taco & Board Game Night"))
    assert party["success"] is True
    assert "Taco" in party["theme"]

    chef = json.loads(tool_chef_meal_planner_skill(cuisine_preference="Tuscan Garlic Pasta"))
    assert chef["success"] is True
    assert "Tuscan Garlic Pasta" in chef["cuisine"]

def test_server_resource_skills_catalog():
    catalog_str = resource_skills_catalog()
    catalog = json.loads(catalog_str)
    assert isinstance(catalog, dict)
    assert len(catalog) >= 9
