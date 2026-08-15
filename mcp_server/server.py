"""Model Context Protocol (MCP) Server exposing real-world, fun, and easy-to-understand tools and skills."""

import json
import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Ensure parent directory is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib

MCPServer = None
for _mod_name, _cls_name in [
    ("mcp.server.fastmcp", "FastMCP"),
    ("mcp.server.mcpserver", "MCPServer"),
]:
    try:
        _mod = importlib.import_module(_mod_name)
        MCPServer = getattr(_mod, _cls_name)
        break
    except (ImportError, AttributeError):
        continue

if MCPServer is None:
    # Fallback for environments where MCP SDK is being installed
    class MCPServer:  # type: ignore
        def __init__(self, name: str = "", version: str = "1.0.0", description: str = "", **kwargs: Any):
            self.name = name
        def tool(self, name: Optional[str] = None, description: Optional[str] = None):
            def decorator(fn: Any) -> Any: return fn
            return decorator
        def prompt(self, name: Optional[str] = None, description: Optional[str] = None):
            def decorator(fn: Any) -> Any: return fn
            return decorator
        def resource(self, uri: Optional[str] = None, name: Optional[str] = None, description: Optional[str] = None, mime_type: Optional[str] = None):
            def decorator(fn: Any) -> Any: return fn
            return decorator
        async def run_stdio_async(self): pass
        async def run_sse_async(self, port: int = 8001): pass

try:
    from mcp_server.tools.math_tools import calculate
    from mcp_server.tools.weather_tools import get_weather as fetch_weather
    from mcp_server.tools.web_search_tools import web_search as do_web_search
    from mcp_server.tools.product_tools import product_knowledge as do_product_knowledge
    from mcp_server.tools.file_tools import workspace_file_ops as do_workspace_file_ops
    from mcp_server.skills import (
        ALL_SKILLS,
        render_travel_planner_skill,
        render_shopping_assistant_skill,
        render_party_planner_skill,
        render_chef_meal_planner_skill
    )
except (ImportError, ValueError):
    from tools.math_tools import calculate  # type: ignore[import-not-found]
    from tools.weather_tools import get_weather as fetch_weather  # type: ignore[import-not-found]
    from tools.web_search_tools import web_search as do_web_search  # type: ignore[import-not-found]
    from tools.product_tools import product_knowledge as do_product_knowledge  # type: ignore[import-not-found]
    from tools.file_tools import workspace_file_ops as do_workspace_file_ops  # type: ignore[import-not-found]
    from skills import (  # type: ignore[import-not-found]
        ALL_SKILLS,
        render_travel_planner_skill,
        render_shopping_assistant_skill,
        render_party_planner_skill,
        render_chef_meal_planner_skill
    )

# Initialize MCP Server instance
app = MCPServer(
    name="agentic-mcp-server",
    description="MCP Server providing real-world, everyday tools: Calculator, Live Weather, Web Search, Shopping Product Catalog, and Fun Domain Skills."
)

# ----------------------------------------------------------------------
# 1. Everyday Tools Registration
# ----------------------------------------------------------------------

@app.tool(
    name="calculator",
    description="Compute everyday math, shopping discounts, tip calculations, bill splitting, and travel budgets."
)
def tool_calculator(expression: str) -> str:
    """Calculate math expression safely."""
    res = calculate(expression)
    return json.dumps(res, indent=2)

@app.tool(
    name="calculate",
    description="Evaluate everyday arithmetic and financial expressions (+, -, *, /, %). Alias for calculator."
)
def tool_calculate(expression: str) -> str:
    """Calculate math expression safely."""
    res = calculate(expression)
    return json.dumps(res, indent=2)

@app.tool(
    name="weather",
    description="Look up current weather conditions, temperatures, and 3-day forecasts for any city or travel destination (e.g. San Francisco, Tokyo, Paris, New York, London, Honolulu)."
)
def tool_weather(
    location: str = "",
    city: str = "",
    units: str = "fahrenheit"
) -> str:
    """Get current weather and 3-day forecasts."""
    res = fetch_weather(location=location, city=city, units=units)
    return json.dumps(res, indent=2)

@app.tool(
    name="web_search",
    description="Search the web for top travel guides, delicious food spots, fun party games, and easy weeknight recipes."
)
def tool_web_search(
    query: str = "",
    search_query: str = "",
    max_results: int = 3
) -> str:
    """Search the web for recommendations and articles."""
    res = do_web_search(query=query, search_query=search_query, max_results=max_results)
    return json.dumps(res, indent=2)

@app.tool(
    name="product_knowledge",
    description="Search popular consumer products (coffee makers, headphones, suitcases, cozy hoodies, camping gear) with prices, discounts, ratings, and return policies."
)
def tool_product_knowledge(
    query: str = "",
    product_name: str = "",
    sku: str = "",
    category: str = ""
) -> str:
    """Search shopping catalog for products, deals, and ratings."""
    res = do_product_knowledge(query=query, product_name=product_name, sku=sku, category=category)
    return json.dumps(res, indent=2)

@app.tool(
    name="workspace_file_ops",
    description="Save or read travel itineraries, shopping lists, and party plans into the local workspace folder."
)
def tool_workspace_file_ops(
    action: str,
    filepath: str = "",
    file_path: str = "",
    filename: str = "",
    file_name: str = "",
    path: str = "",
    content: str = "",
    text: str = ""
) -> str:
    """File operations for saving itineraries and notes."""
    res = do_workspace_file_ops(
        action=action,
        filepath=filepath,
        file_path=file_path,
        filename=filename,
        file_name=file_name,
        path=path,
        content=content,
        text=text
    )
    return json.dumps(res, indent=2)

# ----------------------------------------------------------------------
# 2. Real-World, Fun Domain Skills (MCP Prompts)
# ----------------------------------------------------------------------

@app.prompt(
    name="travel_planner_skill",
    description="🏖️ Vacation Concierge: Creates fun, weather-aware day-by-day travel itineraries with food highlights and packing tips."
)
def prompt_travel_planner(
    destination: str = "Tokyo",
    duration_days: str = "3",
    travel_vibe: str = "foodie adventures, scenic walks, relaxing coffee shops"
) -> str:
    """Activate Vacation & Adventure Concierge skill."""
    return render_travel_planner_skill(destination, duration_days, travel_vibe)

@app.prompt(
    name="shopping_assistant_skill",
    description="🛍️ Personal Shopper: Finds great gifts, calculates discount savings, and highlights customer reviews."
)
def prompt_shopping_assistant(
    shopper_goal: str = "Find a great gift",
    recipient: str = "myself or friend",
    budget_usd: str = "$100 - $300"
) -> str:
    """Activate Personal Shopper & Gift Finder skill."""
    return render_shopping_assistant_skill(shopper_goal, recipient, budget_usd)

@app.prompt(
    name="party_planner_skill",
    description="🎉 Epic Party Host: Plans game nights, birthday parties, guest food budgets, and weather contingencies."
)
def prompt_party_planner(
    party_theme: str = "Game Night & Pizza Party",
    guest_count: str = "8-12 friends",
    location: str = "San Francisco"
) -> str:
    """Activate Epic Party Host skill."""
    return render_party_planner_skill(party_theme, guest_count, location)

@app.prompt(
    name="chef_meal_planner_skill",
    description="🍳 Cozy Home Chef: Creates fast 15-30 minute weeknight recipes, grocery checklists, and ingredient scaling."
)
def prompt_chef_meal_planner(
    cuisine_preference: str = "Italian & Mediterranean",
    dietary_notes: str = "quick weeknight dinners",
    servings: str = "2-4 people"
) -> str:
    """Activate Cozy Chef & Meal Crafter skill."""
    return render_chef_meal_planner_skill(cuisine_preference, dietary_notes, servings)

# ----------------------------------------------------------------------
# 3. MCP Resources Registration
# ----------------------------------------------------------------------

@app.resource(
    uri="skills://catalog",
    name="Skills Catalog",
    description="Catalog of all available real-world skills, their metadata, and recommended tools.",
    mime_type="application/json"
)
def resource_skills_catalog() -> str:
    """Returns the JSON list of installed skills."""
    return json.dumps(ALL_SKILLS, indent=2)

# ----------------------------------------------------------------------
# Server Entrypoint
# ----------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Real-World Everyday Agentic MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio", help="MCP Transport to use")
    parser.add_argument("--port", type=int, default=8001, help="Port for SSE transport")
    args = parser.parse_args()

    if args.transport == "stdio":
        asyncio.run(app.run_stdio_async())
    elif args.transport == "sse":
        asyncio.run(app.run_sse_async(port=args.port))
