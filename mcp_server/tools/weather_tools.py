"""Weather information and forecast tool with rich mock data for major global cities."""

from typing import Dict, Any, Optional

WEATHER_DATABASE = {
    "san francisco": {
        "city": "San Francisco, CA, USA",
        "temperature_c": 18,
        "temperature_f": 64,
        "condition": "Partly Cloudy with Coastal Fog",
        "humidity": 78,
        "wind_speed_mph": 14,
        "uv_index": 5,
        "air_quality_index": 28,
        "forecast_3day": [
            {"day": "Tomorrow", "high_f": 66, "low_f": 52, "condition": "Sunny"},
            {"day": "Day 2", "high_f": 63, "low_f": 50, "condition": "Foggy morning, clear afternoon"},
            {"day": "Day 3", "high_f": 65, "low_f": 51, "condition": "Partly Cloudy"}
        ]
    },
    "new york": {
        "city": "New York, NY, USA",
        "temperature_c": 24,
        "temperature_f": 75,
        "condition": "Sunny and Clear",
        "humidity": 52,
        "wind_speed_mph": 8,
        "uv_index": 7,
        "air_quality_index": 42,
        "forecast_3day": [
            {"day": "Tomorrow", "high_f": 78, "low_f": 64, "condition": "Sunny"},
            {"day": "Day 2", "high_f": 81, "low_f": 68, "condition": "Isolated Thunderstorms"},
            {"day": "Day 3", "high_f": 74, "low_f": 60, "condition": "Breezy and Clear"}
        ]
    },
    "london": {
        "city": "London, UK",
        "temperature_c": 16,
        "temperature_f": 61,
        "condition": "Light Rain Showers",
        "humidity": 84,
        "wind_speed_mph": 12,
        "uv_index": 3,
        "air_quality_index": 22,
        "forecast_3day": [
            {"day": "Tomorrow", "high_f": 63, "low_f": 49, "condition": "Overcast"},
            {"day": "Day 2", "high_f": 66, "low_f": 52, "condition": "Intermittent Rain"},
            {"day": "Day 3", "high_f": 68, "low_f": 54, "condition": "Partly Sunny"}
        ]
    },
    "tokyo": {
        "city": "Tokyo, Japan",
        "temperature_c": 22,
        "temperature_f": 72,
        "condition": "Clear and Mild",
        "humidity": 58,
        "wind_speed_mph": 6,
        "uv_index": 6,
        "air_quality_index": 31,
        "forecast_3day": [
            {"day": "Tomorrow", "high_f": 75, "low_f": 61, "condition": "Clear"},
            {"day": "Day 2", "high_f": 73, "low_f": 60, "condition": "Cloudy"},
            {"day": "Day 3", "high_f": 70, "low_f": 58, "condition": "Light Morning Rain"}
        ]
    },
    "paris": {
        "city": "Paris, France",
        "temperature_c": 21,
        "temperature_f": 70,
        "condition": "Partly Sunny",
        "humidity": 60,
        "wind_speed_mph": 9,
        "uv_index": 6,
        "air_quality_index": 35,
        "forecast_3day": [
            {"day": "Tomorrow", "high_f": 72, "low_f": 55, "condition": "Sunny"},
            {"day": "Day 2", "high_f": 74, "low_f": 57, "condition": "Mild and Sunny"},
            {"day": "Day 3", "high_f": 69, "low_f": 53, "condition": "Passing Clouds"}
        ]
    },
    "seattle": {
        "city": "Seattle, WA, USA",
        "temperature_c": 15,
        "temperature_f": 59,
        "condition": "Light Drizzle",
        "humidity": 85,
        "wind_speed_mph": 7,
        "uv_index": 3,
        "air_quality_index": 18,
        "forecast_3day": [
            {"day": "Tomorrow", "high_f": 62, "low_f": 48, "condition": "Morning Drizzle, Afternoon Sun"},
            {"day": "Day 2", "high_f": 65, "low_f": 50, "condition": "Partly Cloudy"},
            {"day": "Day 3", "high_f": 64, "low_f": 49, "condition": "Scattered Showers"}
        ]
    },
    "bengaluru": {
        "city": "Bengaluru, Karnataka, India",
        "temperature_c": 27,
        "temperature_f": 81,
        "condition": "Pleasant with Gentle Breeze",
        "humidity": 62,
        "wind_speed_mph": 10,
        "uv_index": 8,
        "air_quality_index": 48,
        "forecast_3day": [
            {"day": "Tomorrow", "high_f": 82, "low_f": 68, "condition": "Partly Cloudy"},
            {"day": "Day 2", "high_f": 80, "low_f": 67, "condition": "Evening Thunderstorms"},
            {"day": "Day 3", "high_f": 83, "low_f": 69, "condition": "Mostly Sunny"}
        ]
    }
}

def get_weather(
    location: str = "",
    city: str = "",
    units: str = "fahrenheit"
) -> Dict[str, Any]:
    """
    Get real-time weather conditions and 3-day forecast for a given location or city.
    
    Args:
        location: City name or location string (e.g. 'San Francisco', 'Tokyo', 'London')
        city: Alternative argument name for location
        units: Temperature units ('fahrenheit' or 'celsius')
    """
    loc_key = (location or city or "San Francisco").strip().lower()
    
    # Direct match or substring match
    matched = None
    for key, data in WEATHER_DATABASE.items():
        if key in loc_key or loc_key in key:
            matched = data
            break
            
    if not matched:
        # Fallback generated weather for unlisted locations
        matched = {
            "city": location or city or "Unknown Location",
            "temperature_c": 20,
            "temperature_f": 68,
            "condition": "Mostly Sunny with Mild Breeze",
            "humidity": 65,
            "wind_speed_mph": 10,
            "uv_index": 5,
            "air_quality_index": 35,
            "forecast_3day": [
                {"day": "Tomorrow", "high_f": 70, "low_f": 54, "condition": "Sunny"},
                {"day": "Day 2", "high_f": 72, "low_f": 56, "condition": "Partly Cloudy"},
                {"day": "Day 3", "high_f": 67, "low_f": 52, "condition": "Clear"}
            ]
        }
        
    return {
        "success": True,
        "location": matched["city"],
        "current_temperature": f"{matched['temperature_f']}°F ({matched['temperature_c']}°C)",
        "condition": matched["condition"],
        "humidity_percent": matched["humidity"],
        "wind_speed": f"{matched['wind_speed_mph']} mph",
        "air_quality_index": matched["air_quality_index"],
        "uv_index": matched["uv_index"],
        "3_day_forecast": matched["forecast_3day"]
    }
