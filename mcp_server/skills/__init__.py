from .travel_planner import render_travel_planner_skill
from .shopping_assistant import render_shopping_assistant_skill
from .party_planner import render_party_planner_skill
from .chef_meal_planner import render_chef_meal_planner_skill

ALL_SKILLS = {
    "travel_planner_skill": {
        "name": "🏖️ Vacation & Adventure Concierge",
        "description": "Plans fun, weather-aware travel itineraries with top food recommendations and packing tips.",
        "recommended_tools": ["weather", "web_search", "calculator"]
    },
    "shopping_assistant_skill": {
        "name": "🛍️ Personal Shopper & Gift Finder",
        "description": "Finds popular products, computes discounts & savings, and checks customer reviews.",
        "recommended_tools": ["product_knowledge", "calculator"]
    },
    "party_planner_skill": {
        "name": "🎉 Epic Party & Celebration Host",
        "description": "Designs game nights, birthdays, and dinner parties with weather checks, budgets, and fun games.",
        "recommended_tools": ["weather", "web_search", "calculator"]
    },
    "chef_meal_planner_skill": {
        "name": "🍳 Cozy Chef & Home Meal Crafter",
        "description": "Creates easy 15-30 minute weeknight recipes, grocery lists, and scaled ingredient portions.",
        "recommended_tools": ["web_search", "calculator"]
    }
}

__all__ = [
    "ALL_SKILLS",
    "render_travel_planner_skill",
    "render_shopping_assistant_skill",
    "render_party_planner_skill",
    "render_chef_meal_planner_skill"
]
