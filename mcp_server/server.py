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
        render_skill,
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
        render_skill,
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
try:
    app = MCPServer(
        name="agentic-mcp-server",
        description="MCP Server providing real-world, everyday tools: Calculator, Live Weather, Web Search, Shopping Product Catalog, and Fun Domain Skills."
    )
except TypeError:
    app = MCPServer("agentic-mcp-server")

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
    total: Any = None,
    bill: Any = None,
    amount: Any = None,
    total_bill: Any = None,
    bill_total: Any = None,
    tip_percentage: Any = None,
    tip_percent: Any = None,
    tip: Any = None,
    num_people: Any = None,
    number_of_people: Any = None,
    num_diners: Any = None,
    people_count: Any = None,
    split: Any = None,
    people: Any = None,
    diners: Any = None,
    count: Any = None
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
        num_diners=num_diners,
        people_count=people_count,
        split=split,
        people=people,
        diners=diners,
        count=count
    )
    return json.dumps(res, indent=2)

@app.tool(
    name="tip_calculator",
    description="Calculate restaurant tip and split amounts. Alias for calculate_tip_and_split."
)
def tool_tip_calculator(
    total: Any = None,
    bill: Any = None,
    amount: Any = None,
    total_bill: Any = None,
    bill_total: Any = None,
    tip_percentage: Any = None,
    tip_percent: Any = None,
    tip: Any = None,
    num_people: Any = None,
    number_of_people: Any = None,
    num_diners: Any = None,
    people_count: Any = None,
    split: Any = None,
    people: Any = None,
    diners: Any = None,
    count: Any = None
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
        num_diners=num_diners,
        people_count=people_count,
        split=split,
        people=people,
        diners=diners,
        count=count
    )
    return json.dumps(res, indent=2)
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
# Long-Term Semantic Memory Tools
# ----------------------------------------------------------------------

try:
    from mcp_server.tools.memory_tools import memory_store as do_memory_store, memory_recall as do_memory_recall, memory_list as do_memory_list, memory_delete as do_memory_delete
except ImportError:
    try:
        from tools.memory_tools import memory_store as do_memory_store, memory_recall as do_memory_recall, memory_list as do_memory_list, memory_delete as do_memory_delete  # type: ignore[import-not-found]
    except ImportError:
        do_memory_store = do_memory_recall = do_memory_list = do_memory_delete = None

if do_memory_store is not None:
    @app.tool(
        name="memory_store",
        description="Store information or calculation results for long-term semantic recall across sessions. Save notes, summaries, preferences, or important facts."
    )
    def tool_memory_store(
        content: Any = "",
        text: Any = "",
        data: Any = "",
        payload: Any = "",
        info: Any = "",
        note: Any = "",
        value: Any = "",
        result: Any = "",
        message: Any = "",
        namespace: str = "default",
        ns: str = "",
        source: str = "",
        tags: str = ""
    ) -> str:
        """Store a memory for long-term recall."""
        res = do_memory_store(
            content=content,
            text=text,
            data=data,
            payload=payload,
            info=info,
            note=note,
            value=value,
            result=result,
            message=message,
            namespace=namespace,
            ns=ns,
            source=source,
            tags=tags
        )
        return json.dumps(res, indent=2)

    @app.tool(
        name="memory_recall",
        description="Recall previously stored memories semantically similar to a query. Search across sessions for stored notes, facts, and preferences."
    )
    def tool_memory_recall(
        query: Any = "",
        search: Any = "",
        question: Any = "",
        namespace: str = "default",
        ns: str = "",
        top_k: int = 5,
        limit: int = 0
    ) -> str:
        """Recall memories by semantic similarity."""
        res = do_memory_recall(
            query=query,
            search=search,
            question=question,
            namespace=namespace,
            ns=ns,
            top_k=top_k,
            limit=limit
        )
        return json.dumps(res, indent=2)

    @app.tool(
        name="memory_list",
        description="List all stored memories in a namespace."
    )
    def tool_memory_list(
        namespace: str = "default",
        ns: str = "",
        limit: int = 50
    ) -> str:
        """List stored memories."""
        res = do_memory_list(namespace=namespace, ns=ns, limit=limit)
        return json.dumps(res, indent=2)

    @app.tool(
        name="memory_delete",
        description="Delete a specific stored memory by its ID. Use with caution — this action is irreversible."
    )
    def tool_memory_delete(
        memory_id: str = "",
        id: str = ""
    ) -> str:
        """Delete a specific memory."""
        res = do_memory_delete(memory_id=memory_id, id=id)
        return json.dumps(res, indent=2)

# ----------------------------------------------------------------------
# Voice Interface Tools (Speech-to-Text and Text-to-Speech)
# ----------------------------------------------------------------------

try:
    from mcp_server.tools.voice_tools import transcribe_audio as do_transcribe_audio, speak_text as do_speak_text
except ImportError:
    try:
        from tools.voice_tools import transcribe_audio as do_transcribe_audio, speak_text as do_speak_text  # type: ignore[import-not-found]
    except ImportError:
        do_transcribe_audio = do_speak_text = None

if do_transcribe_audio is not None:
    @app.tool(
        name="transcribe_audio",
        description="Transcribe audio data (base64 encoded) to text using Whisper speech recognition."
    )
    def tool_transcribe_audio(
        audio_base64: str = "",
        language: str = "en"
    ) -> str:
        """Transcribe base64 audio to text."""
        res = do_transcribe_audio(audio_base64=audio_base64, language=language)
        return json.dumps(res, indent=2)

    @app.tool(
        name="speak_text",
        description="Convert text into spoken speech audio output (TTS)."
    )
    def tool_speak_text(
        text: str = "",
        voice: str = "default"
    ) -> str:
        """Synthesize text to speech."""
        res = do_speak_text(text=text, voice=voice)
        return json.dumps(res, indent=2)

# ----------------------------------------------------------------------
# Progressive Disclosure Meta-Tools for Frontier & Autonomous Agents
# ----------------------------------------------------------------------

@app.tool(
    name="discover_skills",
    description="Discover and inspect available specialized domain skills without loading their full prompts into context. Returns a lightweight catalog (id, name, category, 1-line description, recommended tools). Filter optionally by category."
)
def tool_discover_skills(category: str = "") -> str:
    """Returns a lightweight JSON index of all available skills for progressive discovery."""
    skills_index = []
    cat_filter = (category or "").strip().lower()
    for skill_id, meta in ALL_SKILLS.items():
        if cat_filter and cat_filter not in meta.get("category", "").lower() and cat_filter not in skill_id.lower():
            continue
        skills_index.append({
            "skill_id": skill_id,
            "name": meta.get("name"),
            "category": meta.get("category"),
            "description": meta.get("description"),
            "recommended_tools": meta.get("recommended_tools", []),
            "default_params": meta.get("default_params", {})
        })
    return json.dumps({
        "status": "success",
        "total_skills": len(skills_index),
        "instructions": "Call tool 'load_skill' with a skill_id to dynamically load full domain guidelines, persona, and execution instructions on demand.",
        "skills": skills_index
    }, indent=2)

@app.tool(
    name="load_skill",
    description="Dynamically loads and renders full domain guidelines, persona rules, and execution instructions for a specialized skill (Progressive Disclosure). Pass 'skill_name' (e.g. 'travel_planner_skill' or 'code_review_skill') and optional 'parameters'."
)
def tool_load_skill(
    skill_name: str = "",
    skill_id: str = "",
    parameters: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None
) -> str:
    """Dynamically loads and renders full domain guidelines for a skill."""
    target_name = (skill_name or skill_id or "").strip()
    if not target_name:
        return json.dumps({
            "status": "error",
            "message": "Please provide 'skill_name' (e.g. 'travel_planner_skill', 'code_review_skill', 'shopping_assistant_skill')."
        })

    target_params = parameters or params or {}
    rendered_instructions = render_skill(target_name, target_params)
    clean_id = target_name if target_name.endswith("_skill") else f"{target_name}_skill"
    meta = ALL_SKILLS.get(clean_id, {})

    return json.dumps({
        "status": "success",
        "skill_id": clean_id,
        "skill_name": meta.get("name", clean_id),
        "category": meta.get("category", "General"),
        "recommended_tools": meta.get("recommended_tools", []),
        "instructions": rendered_instructions
    }, indent=2)

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
