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
    from mcp_server.tools.math_tools import calculate, calculate_tip_and_split
    from mcp_server.tools.weather_tools import get_weather as fetch_weather
    from mcp_server.tools.web_search_tools import web_search as do_web_search
    from mcp_server.tools.product_tools import product_knowledge as do_product_knowledge
    from mcp_server.tools.file_tools import workspace_file_ops as do_workspace_file_ops
    from mcp_server.tools.search_tools import search_knowledge as do_search_knowledge
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
except (ImportError, ValueError):
    from tools.math_tools import calculate, calculate_tip_and_split  # type: ignore[import-not-found]
    from tools.weather_tools import get_weather as fetch_weather  # type: ignore[import-not-found]
    from tools.web_search_tools import web_search as do_web_search  # type: ignore[import-not-found]
    from tools.product_tools import product_knowledge as do_product_knowledge  # type: ignore[import-not-found]
    from tools.file_tools import workspace_file_ops as do_workspace_file_ops  # type: ignore[import-not-found]
    from tools.search_tools import search_knowledge as do_search_knowledge  # type: ignore[import-not-found]
    from skills import (  # type: ignore[import-not-found]
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
    description="Compute everyday math, shopping discounts, tip calculations, bill splitting, and travel budgets. Provide 'expression' (e.g. '184.50 * 0.18') or tip/total values."
)
def tool_calculator(
    expression: str = "",
    formula: str = "",
    tip: str = "",
    total: str = "",
    math_expr: str = ""
) -> str:
    """Calculate math expression safely."""
    res = calculate(expression=expression, formula=formula, tip=tip, total=total, math_expr=math_expr)
    return json.dumps(res, indent=2)

@app.tool(
    name="calculate",
    description="Evaluate everyday arithmetic and financial expressions (+, -, *, /, %). Alias for calculator."
)
def tool_calculate(
    expression: str = "",
    formula: str = "",
    tip: str = "",
    total: str = "",
    math_expr: str = ""
) -> str:
    """Calculate math expression safely."""
    res = calculate(expression=expression, formula=formula, tip=tip, total=total, math_expr=math_expr)
    return json.dumps(res, indent=2)

@app.tool(
    name="calculate_tip_and_split",
    description="Calculate bill tip amounts and split costs evenly among multiple diners/friends."
)
def tool_calculate_tip_and_split(
    total: float = 0.0,
    bill: float = 0.0,
    amount: float = 0.0,
    total_bill: float = 0.0,
    bill_total: float = 0.0,
    tip_percentage: float = 0.18,
    tip_percent: float = 0.0,
    tip: float = 0.0,
    num_people: int = 1,
    number_of_people: int = 1,
    split: int = 1,
    people: int = 1
) -> str:
    """Calculate tip and split bill evenly."""
    res = calculate_tip_and_split(
        total=total,
        bill=bill,
        amount=amount,
        total_bill=total_bill,
        bill_total=bill_total,
        tip_percentage=tip_percentage,
        tip_percent=tip_percent,
        tip=tip,
        num_people=num_people,
        number_of_people=number_of_people,
        split=split,
        people=people
    )
    return json.dumps(res, indent=2)

@app.tool(
    name="tip_calculator",
    description="Calculate restaurant tip and split amounts. Alias for calculate_tip_and_split."
)
def tool_tip_calculator(
    total: float = 0.0,
    bill: float = 0.0,
    amount: float = 0.0,
    total_bill: float = 0.0,
    bill_total: float = 0.0,
    tip_percentage: float = 0.18,
    tip_percent: float = 0.0,
    tip: float = 0.0,
    num_people: int = 1,
    number_of_people: int = 1,
    split: int = 1,
    people: int = 1
) -> str:
    """Calculate tip and split bill evenly."""
    res = calculate_tip_and_split(
        total=total,
        bill=bill,
        amount=amount,
        total_bill=total_bill,
        bill_total=bill_total,
        tip_percentage=tip_percentage,
        tip_percent=tip_percent,
        tip=tip,
        num_people=num_people,
        number_of_people=number_of_people,
        split=split,
        people=people
    )
    return json.dumps(res, indent=2)

@app.tool(
    name="split_bill",
    description="Split restaurant dinner bills and calculate tip percentages. Alias for calculate_tip_and_split."
)
def tool_split_bill(
    total: float = 0.0,
    bill: float = 0.0,
    amount: float = 0.0,
    total_bill: float = 0.0,
    bill_total: float = 0.0,
    tip_percentage: float = 0.18,
    tip_percent: float = 0.0,
    tip: float = 0.0,
    num_people: int = 1,
    number_of_people: int = 1,
    split: int = 1,
    people: int = 1
) -> str:
    """Calculate tip and split bill evenly."""
    res = calculate_tip_and_split(
        total=total,
        bill=bill,
        amount=amount,
        total_bill=total_bill,
        bill_total=bill_total,
        tip_percentage=tip_percentage,
        tip_percent=tip_percent,
        tip=tip,
        num_people=num_people,
        number_of_people=number_of_people,
        split=split,
        people=people
    )
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
    query: Any = "",
    search_query: Any = "",
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
    action: str = "",
    operation: str = "",
    op: str = "",
    filepath: str = "",
    file_path: str = "",
    filename: str = "",
    file_name: str = "",
    path: str = "",
    content: str = "",
    text: str = "",
    data: str = ""
) -> str:
    """File operations for saving itineraries and notes."""
    res = do_workspace_file_ops(
        action=action,
        operation=operation,
        op=op,
        filepath=filepath,
        file_path=file_path,
        filename=filename,
        file_name=file_name,
        path=path,
        content=content,
        text=text,
        data=data
    )
    return json.dumps(res, indent=2)

@app.tool(
    name="knowledge_base_search",
    description="Search internal technical documentation and knowledge base (LiteLLM proxy, Ollama, FastMCP protocol, ReAct agents)."
)
def tool_knowledge_base_search(
    query: Any = "",
    limit: int = 3
) -> str:
    """Search internal knowledge base."""
    res = do_search_knowledge(query=query, limit=limit)
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

@app.prompt(
    name="code_review_skill",
    description="💻 Senior Code Reviewer: Performs security audits, performance profiling, and clean code refactoring."
)
def prompt_code_review(
    language: str = "python",
    focus: str = "security, error handling, performance"
) -> str:
    """Activate Code Reviewer skill."""
    return render_code_review_skill(language, focus)

@app.prompt(
    name="financial_advisor_skill",
    description="📈 Personal Wealth & Financial Advisor: Analyzes budgets, compound interest, emergency funds, and investments."
)
def prompt_financial_advisor(
    goal: str = "Retirement & Monthly Budget Plan",
    monthly_income: str = "$6,500"
) -> str:
    """Activate Financial Advisor skill."""
    return render_financial_advisor_skill(goal, monthly_income)

@app.prompt(
    name="customer_support_skill",
    description="🎧 Empathetic Support Specialist: Delivers warm, structured issue resolution and customer guidance."
)
def prompt_customer_support(
    tone: str = "Warm, professional, solution-oriented"
) -> str:
    """Activate Customer Support skill."""
    return render_customer_support_skill(tone)

@app.prompt(
    name="data_analysis_skill",
    description="📊 Data Scientist: Summarizes datasets, calculates statistical distributions, and detects trends."
)
def prompt_data_analysis(
    metric_focus: str = "Conversion rate, Mean, Median, Variance"
) -> str:
    """Activate Data Analysis skill."""
    return render_data_analysis_skill("Dataset", metric_focus)

@app.prompt(
    name="research_skill",
    description="🔬 Intelligence Researcher: Conducts deep synthesis across topics and creates executive briefs."
)
def prompt_research(
    topic: str = "State of Agentic AI & Model Context Protocol in 2026"
) -> str:
    """Activate Research skill."""
    return render_research_skill(topic)

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
