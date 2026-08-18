from .travel_planner import render_travel_planner_skill
from .shopping_assistant import render_shopping_assistant_skill
from .party_planner import render_party_planner_skill
from .chef_meal_planner import render_chef_meal_planner_skill
from .code_review import render_code_review_skill
from .customer_support import render_customer_support_skill
from .data_analysis import render_data_analysis_skill
from .financial_advisor import render_financial_advisor_skill
from .research import render_research_skill

ALL_SKILLS = {
    "travel_planner_skill": {
        "id": "travel_planner_skill",
        "name": "🏖️ Vacation & Adventure Concierge",
        "category": "Lifestyle & Travel",
        "description": "Plans fun, weather-aware travel itineraries with top food recommendations and packing tips.",
        "recommended_tools": ["weather", "web_search", "calculator"],
        "default_params": {"destination": "Paris, France", "duration_days": "3", "travel_vibe": "quaint bakeries, art museums"}
    },
    "shopping_assistant_skill": {
        "id": "shopping_assistant_skill",
        "name": "🛍️ Personal Shopper & Gift Finder",
        "category": "E-Commerce & Deals",
        "description": "Finds popular products, computes discounts & savings, and checks customer reviews.",
        "recommended_tools": ["product_knowledge", "calculator"],
        "default_params": {"shopper_goal": "Find top-rated noise-canceling headphones", "budget_usd": "$200"}
    },
    "party_planner_skill": {
        "id": "party_planner_skill",
        "name": "🎉 Epic Party & Celebration Host",
        "category": "Events & Entertainment",
        "description": "Designs game nights, birthdays, and dinner parties with weather checks, budgets, and fun games.",
        "recommended_tools": ["weather", "web_search", "calculator"],
        "default_params": {"event_type": "Game Night", "guest_count": "8", "theme": "Cozy Boardgames & Pizza"}
    },
    "chef_meal_planner_skill": {
        "id": "chef_meal_planner_skill",
        "name": "🍳 Cozy Chef & Home Meal Crafter",
        "category": "Food & Culinary",
        "description": "Creates easy 15-30 minute weeknight recipes, grocery lists, and scaled ingredient portions.",
        "recommended_tools": ["web_search", "calculator"],
        "default_params": {"dietary_preferences": "Quick 15-minute pasta", "servings": "4"}
    },
    "code_review_skill": {
        "id": "code_review_skill",
        "name": "💻 Senior Code Reviewer & Architect",
        "category": "Engineering & Code",
        "description": "Performs security audits, performance profiling, clean code reviews, and idiomatic refactoring.",
        "recommended_tools": ["workspace_file_ops", "calculator"],
        "default_params": {"language": "python", "focus": "security, error handling, performance"}
    },
    "financial_advisor_skill": {
        "id": "financial_advisor_skill",
        "name": "📈 Personal Wealth & Financial Advisor",
        "category": "Finance & Budgeting",
        "description": "Analyzes household budgets, compound interest, emergency funds, debt payoffs, and investments.",
        "recommended_tools": ["calculator", "web_search"],
        "default_params": {"goal": "Retirement & Monthly Budget Plan", "monthly_income": "$6,500"}
    },
    "customer_support_skill": {
        "id": "customer_support_skill",
        "name": "🎧 Empathetic Support Specialist",
        "category": "Customer Experience",
        "description": "Delivers polite, empathetic, structured issue resolution, warranty troubleshooting, and returns guidance.",
        "recommended_tools": ["product_knowledge", "web_search"],
        "default_params": {"tone": "Warm, professional, solution-oriented"}
    },
    "data_analysis_skill": {
        "id": "data_analysis_skill",
        "name": "📊 Data Scientist & Statistical Analyst",
        "category": "Analytics & Research",
        "description": "Summarizes datasets, calculates statistical distributions, detects trends, and interprets correlations.",
        "recommended_tools": ["calculator", "workspace_file_ops"],
        "default_params": {"metric_focus": "Conversion rate, Mean, Median, Variance"}
    },
    "research_skill": {
        "id": "research_skill",
        "name": "🔬 Intelligence & Literature Researcher",
        "category": "Research & Synthesis",
        "description": "Conducts deep synthesis across topics, compares technologies, and creates executive briefs.",
        "recommended_tools": ["web_search", "workspace_file_ops"],
        "default_params": {"topic": "State of Agentic AI & Model Context Protocol in 2026"}
    }
}

SKILL_RENDERERS = {
    "travel_planner_skill": render_travel_planner_skill,
    "shopping_assistant_skill": render_shopping_assistant_skill,
    "party_planner_skill": render_party_planner_skill,
    "chef_meal_planner_skill": render_chef_meal_planner_skill,
    "code_review_skill": render_code_review_skill,
    "customer_support_skill": render_customer_support_skill,
    "data_analysis_skill": render_data_analysis_skill,
    "financial_advisor_skill": render_financial_advisor_skill,
    "research_skill": render_research_skill
}

def render_skill(skill_name: str, params: dict = None) -> str:
    """
    Dynamically renders the complete prompt instructions for a given skill.
    Supports skill name shorthands (e.g. 'travel_planner' or 'travel_planner_skill').
    """
    params = params or {}
    clean_name = skill_name.strip()
    if not clean_name.endswith("_skill") and f"{clean_name}_skill" in SKILL_RENDERERS:
        clean_name = f"{clean_name}_skill"

    renderer = SKILL_RENDERERS.get(clean_name)
    if not renderer:
        available = list(ALL_SKILLS.keys())
        return f"Error: Skill '{skill_name}' not found. Available skills: {', '.join(available)}"

    meta = ALL_SKILLS.get(clean_name, {})
    default_p = dict(meta.get("default_params", {}))
    default_p.update(params)

    # Handle common parameter aliases
    if "goal" in default_p and "financial_goal" not in default_p:
        default_p["financial_goal"] = default_p["goal"]
    if "dietary_preferences" in default_p and "cuisine_preference" not in default_p:
        default_p["cuisine_preference"] = default_p["dietary_preferences"]
    if "dietary_preferences" in default_p and "dietary_notes" not in default_p:
        default_p["dietary_notes"] = default_p["dietary_preferences"]
    if "dataset_description" in default_p and "dataset_summary" not in default_p:
        default_p["dataset_summary"] = default_p["dataset_description"]

    try:
        # Call renderer with default + supplied parameters
        import inspect
        sig = inspect.signature(renderer)
        kwargs = {}
        for param in sig.parameters.values():
            if param.name in default_p:
                kwargs[param.name] = default_p[param.name]
        return renderer(**kwargs)
    except Exception as e:
        return f"Error rendering skill '{skill_name}': {str(e)}"

__all__ = [
    "ALL_SKILLS",
    "SKILL_RENDERERS",
    "render_skill",
    "render_travel_planner_skill",
    "render_shopping_assistant_skill",
    "render_party_planner_skill",
    "render_chef_meal_planner_skill",
    "render_code_review_skill",
    "render_customer_support_skill",
    "render_data_analysis_skill",
    "render_financial_advisor_skill",
    "render_research_skill"
]

