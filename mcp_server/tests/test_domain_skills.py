"""Unit tests for domain skills catalog and prompt rendering in MCP Server."""

import pytest
from mcp_server.skills import (
    ALL_SKILLS,
    render_travel_planner_skill,
    render_shopping_assistant_skill,
    render_party_planner_skill,
    render_chef_meal_planner_skill,
    render_code_review_skill,
    render_customer_support_skill,
    render_data_analysis_skill,
    render_financial_advisor_skill,
    render_research_skill
)

def test_all_skills_catalog():
    assert len(ALL_SKILLS) == 9
    expected_ids = {
        "travel_planner_skill",
        "shopping_assistant_skill",
        "party_planner_skill",
        "chef_meal_planner_skill",
        "code_review_skill",
        "financial_advisor_skill",
        "customer_support_skill",
        "data_analysis_skill",
        "research_skill"
    }
    assert set(ALL_SKILLS.keys()) == expected_ids

def test_render_travel_planner_skill():
    prompt = render_travel_planner_skill("Tokyo, Japan", "5", "sushi, anime, gardens")
    assert "Tokyo, Japan" in prompt
    assert "5" in prompt
    assert "weather" in prompt

def test_render_shopping_assistant_skill():
    prompt = render_shopping_assistant_skill("mechanical keyboard", "$150")
    assert "mechanical keyboard" in prompt
    assert "$150" in prompt

def test_render_party_planner_skill():
    prompt = render_party_planner_skill("Board Game Night", "6", "Cozy winter vibe")
    assert "Board Game Night" in prompt
    assert "6" in prompt

def test_render_chef_meal_planner_skill():
    prompt = render_chef_meal_planner_skill("Creamy Tuscan Garlic Pasta", "4")
    assert "Creamy Tuscan Garlic Pasta" in prompt
    assert "4" in prompt

def test_render_code_review_skill():
    prompt = render_code_review_skill("python", "security, performance")
    assert "python" in prompt

def test_render_customer_support_skill():
    prompt = render_customer_support_skill("Empathetic, clear, structured")
    assert "Empathetic" in prompt

def test_render_data_analysis_skill():
    prompt = render_data_analysis_skill("User sales dataset with 10k rows", "Mean, Median, StdDev")
    assert "User sales dataset" in prompt
    assert "Mean, Median" in prompt

def test_render_financial_advisor_skill():
    prompt = render_financial_advisor_skill("Retirement plan", "$5,000")
    assert "Retirement plan" in prompt
    assert "$5,000" in prompt

def test_render_research_skill():
    prompt = render_research_skill("Agentic AI LLM Gateways")
    assert "Agentic AI LLM Gateways" in prompt
