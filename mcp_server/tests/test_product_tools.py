"""Unit tests for product tools, catalog search, SKU matching, and discounts."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.product_tools import product_knowledge, PRODUCT_CATALOG

def test_product_search_by_keyword():
    # Coffee maker
    res = product_knowledge(query="coffee maker")
    assert res["success"] is True
    assert res["items_found"] > 0
    assert any("AromaMaster" in p["product_name"] for p in res["products"])

    # Headphones
    res_audio = product_knowledge(query="headphones")
    assert res_audio["success"] is True
    assert any("CloudBeats" in p["product_name"] for p in res_audio["products"])

    # Suitcase
    res_luggage = product_knowledge(query="suitcase")
    assert res_luggage["success"] is True
    assert any("Voyager" in p["product_name"] for p in res_luggage["products"])

def test_product_search_by_sku():
    res = product_knowledge(sku="AUDIO-SILENCE-MAX")
    assert res["success"] is True
    assert len(res["products"]) >= 1
    assert res["products"][0]["sku"] == "AUDIO-SILENCE-MAX"

def test_product_search_by_category():
    res = product_knowledge(category="Apparel & Loungewear")
    assert res["success"] is True
    assert any(p["category"] == "Apparel & Loungewear" for p in res["products"])

def test_product_search_list_and_dict_payload():
    # List query argument
    res_list = product_knowledge(query=["espresso", "grinder"])
    assert res_list["success"] is True
    assert res_list["items_found"] > 0

    # Dict query argument
    res_dict = product_knowledge(query={"product": "hoodie"})
    assert res_dict["success"] is True
    assert res_dict["items_found"] > 0

def test_product_search_empty_query_featured_fallback():
    res = product_knowledge()
    assert res["success"] is True
    assert res["items_found"] > 0
    assert len(res["products"]) >= 3

def test_product_catalog_structure():
    for item in PRODUCT_CATALOG:
        assert "sku" in item
        assert "product_name" in item
        assert "category" in item
        assert "price_usd" in item
        assert "rating" in item
        assert "stock_status" in item
        assert "return_policy" in item
        assert "highlights" in item
