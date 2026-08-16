"""Unit tests for weather tool functionality, forecasting, and data structures."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.weather_tools import get_weather, format_weather_summary, WEATHER_DATABASE

def test_weather_known_cities():
    cities = ["Paris", "Tokyo", "New York", "London", "San Francisco", "Seattle", "Bengaluru"]
    for city in cities:
        res = get_weather(location=city)
        assert res["success"] is True, f"Failed for city {city}"
        assert city.lower() in res["location"].lower()
        assert "current_temperature" in res
        assert "condition" in res
        assert "humidity_percent" in res
        assert "wind_speed" in res
        assert "3_day_forecast" in res
        assert len(res["3_day_forecast"]) == 3

def test_weather_city_aliases_and_case_insensitivity():
    # Lowercase & whitespace
    res = get_weather(city="  tokyo  ")
    assert res["success"] is True
    assert "Tokyo" in res["location"]

    # Parameter alias location vs city
    res_loc = get_weather(location="San Francisco")
    assert res_loc["success"] is True
    assert "San Francisco" in res_loc["location"]

def test_weather_list_and_dict_payload():
    res_list = get_weather(location=["Paris", "France"])
    assert res_list["success"] is True
    assert "Paris" in res_list["location"]

    res_dict = get_weather(location={"city": "Tokyo"})
    assert res_dict["success"] is True
    assert "Tokyo" in res_dict["location"]

def test_weather_unknown_city_fallback():
    res = get_weather(location="Atlantis Unknown Realm")
    assert res["success"] is True
    assert "Atlantis Unknown Realm" in res["location"]
    assert "current_temperature" in res
    assert "3_day_forecast" in res

def test_weather_empty_location_defaults_to_san_francisco():
    res = get_weather(location="")
    assert res["success"] is True
    assert "San Francisco" in res["location"]

def test_format_weather_summary():
    data = get_weather(location="Paris")
    summary = format_weather_summary(data)
    assert "Paris" in summary
    assert "Weather for Paris" in summary
