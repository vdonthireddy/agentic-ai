"""Unit tests for everyday tools (calculator, weather, web_search, product_knowledge) and fun skills."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.math_tools import calculate, calculate_tip_and_split
from tools.weather_tools import get_weather
from tools.web_search_tools import web_search
from tools.product_tools import product_knowledge
from skills import (
    render_travel_planner_skill,
    render_shopping_assistant_skill,
    render_party_planner_skill,
    render_chef_meal_planner_skill
)

def test_calculator_bill_splitting_and_discounts():
    # Split $184.50 bill among 4 people
    res = calculate("184.50 / 4")
    assert res["success"] is True
    assert res["result"] == 46.125

    # 15% discount on $199.99
    res_discount = calculate("199.99 * 0.15")
    assert res_discount["success"] is True
    assert round(res_discount["result"], 2) == 30.00

def test_calculate_tip_and_split_direct():
    # $184.50 for 4 people with 18% tip (0.18)
    res = calculate_tip_and_split(total=184.5, num_people=4, tip_percentage=0.18)
    assert res["success"] is True
    assert res["bill"] == 184.5
    assert res["tip_amount"] == 33.21
    assert res["total_with_tip"] == 217.71
    assert res["num_people"] == 4
    assert res["per_person"] == 54.43

def test_weather_paris_and_tokyo():
    res_paris = get_weather(location="Paris")
    assert res_paris["success"] is True
    assert "Paris" in res_paris["location"]
    assert "3_day_forecast" in res_paris

    res_tokyo = get_weather(location="Tokyo")
    assert res_tokyo["success"] is True
    assert "Tokyo" in res_tokyo["location"]

def test_web_search_lifestyle_queries():
    # Standard string query
    res = web_search(query="best ramen in Tokyo")
    assert res["success"] is True
    assert res["results_count"] > 0
    assert any("Tokyo" in r["title"] or "ramen" in r["snippet"].lower() for r in res["results"])

    # List query (e.g. when LLM passes list of tokens)
    res_list = web_search(query=["ramen", "tokyo"])
    assert res_list["success"] is True
    assert res_list["results_count"] > 0

    # Dict query
    res_dict = web_search(query={"keywords": "party games"})
    assert res_dict["success"] is True
    assert res_dict["results_count"] > 0

def test_product_knowledge_catalog():
    # Search espresso machine
    res = product_knowledge(query="espresso maker")
    assert res["success"] is True
    assert res["items_found"] > 0
    item = res["products"][0]
    assert "AromaMaster" in item["product_name"] or "Coffee" in item["category"]
    assert item["rating"] >= 4.5

    # Search noise canceling headphones
    res_audio = product_knowledge(query="headphones")
    assert res_audio["success"] is True
    assert any("CloudBeats" in p["product_name"] for p in res_audio["products"])

def test_fun_skills_rendering():
    travel = render_travel_planner_skill(destination="Paris", duration_days="3")
    assert "Vacation & Adventure Concierge" in travel
    assert "Paris" in travel

    shopping = render_shopping_assistant_skill(shopper_goal="Espresso maker on sale")
    assert "Personal Shopper" in shopping
    assert "Espresso maker" in shopping

    party = render_party_planner_skill(party_theme="Game Night", guest_count="8 friends")
    assert "Epic Party" in party
    assert "Game Night" in party

    chef = render_chef_meal_planner_skill(cuisine_preference="Tuscan Pasta")
    assert "Cozy Chef" in chef
    assert "Tuscan Pasta" in chef

def test_knowledge_base_search_lookup():
    from tools.search_tools import search_knowledge, search_knowledge_base
    res = search_knowledge("LiteLLM")
    assert res["success"] is True
    assert res["results_found"] > 0
    assert any("LiteLLM" in m["topic"] for m in res["matches"])

    res_alias = search_knowledge_base("Ollama")
    assert res_alias["success"] is True
    assert res_alias["results_found"] > 0
