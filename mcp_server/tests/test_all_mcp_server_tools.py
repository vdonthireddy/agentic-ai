"""Unit tests for all FastMCP tool wrappers and prompts registered in mcp_server/server.py."""

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
    tool_code_review_skill,
    tool_financial_advisor_skill,
    tool_customer_support_skill,
    tool_data_analysis_skill,
    tool_research_skill,
    prompt_travel_planner,
    prompt_shopping_assistant,
    prompt_party_planner,
    prompt_chef_meal_planner,
    prompt_code_review,
    prompt_financial_advisor,
    prompt_customer_support,
    prompt_data_analysis,
    prompt_research,
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

def test_server_all_domain_skills_tools():
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

    finance = json.loads(tool_financial_advisor_skill(goal="Invest 100 dollars wisely", monthly_income="$3000"))
    assert finance["success"] is True
    assert "Financial" in finance["instructions"] or "Strategist" in finance["instructions"]

    code = json.loads(tool_code_review_skill(language="python", focus="security"))
    assert code["success"] is True
    assert "Code Reviewer" in code["instructions"]

    support = json.loads(tool_customer_support_skill(tone="warm"))
    assert support["success"] is True
    assert "Support" in support["instructions"]

    data = json.loads(tool_data_analysis_skill(metric_focus="Mean, Median, Standard Deviation"))
    assert data["success"] is True
    assert "Data" in data["instructions"]

    research = json.loads(tool_research_skill(topic="Agentic AI Trends"))
    assert research["success"] is True
    assert "Research" in research["instructions"]

def test_server_all_domain_skills_prompts():
    assert "Vacation" in prompt_travel_planner("Tokyo", "3")
    assert "Shopper" in prompt_shopping_assistant("Headphones", "$200")
    assert "Party" in prompt_party_planner("Game Night")
    assert "Chef" in prompt_chef_meal_planner("Tuscan Pasta")
    assert "Code Reviewer" in prompt_code_review("python")
    assert "Financial" in prompt_financial_advisor("Invest $100", "$4,000")
    assert "Support" in prompt_customer_support("warm")
    assert "Data" in prompt_data_analysis("Distributions")
    assert "Research" in prompt_research("Model Context Protocol")

def test_server_resource_skills_catalog():
    catalog_str = resource_skills_catalog()
    catalog = json.loads(catalog_str)
    assert isinstance(catalog, dict)
    assert len(catalog) >= 9
