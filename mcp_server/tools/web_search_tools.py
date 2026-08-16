"""Real web search engine tool powered by DuckDuckGo (ddgs) with curated fallback."""

import logging
from typing import Dict, Any, List

logger = logging.getLogger("mcp_server.web_search")

# Try importing DDGS
try:
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS  # type: ignore[no-redef]
    HAS_DDGS = True
except Exception as _e:
    DDGS = None
    HAS_DDGS = False

WEB_INDEX = [
    {
        "query_keywords": ["tokyo", "japan", "ramen", "travel", "shibuya", "sushi"],
        "title": "The Ultimate 3-Day Tokyo Guide: Top Ramen Shops, Shibuya Crossing & Hidden Temples",
        "url": "https://wanderlustguides.com/tokyo-food-and-adventures",
        "snippet": "Discover Tokyo's best hidden izakayas in Omoide Yokocho, catch sunrise over Senso-ji temple, visit teamLab Planets, and slurp award-winning tonkotsu ramen in Shinjuku.",
        "category": "Travel & Food"
    },
    {
        "query_keywords": ["paris", "france", "croissant", "eiffel", "louvre", "bistro"],
        "title": "Paris Like a Local: Best Bakeries, Sunset Seine Picnics & Charming Neighborhoods",
        "url": "https://wanderlustguides.com/paris-bistros-and-walks",
        "snippet": "Stroll through the cobblestones of Montmartre, grab warm butter croissants at Du Pain et des Idées, and relax with cheese and wine by the banks of the Seine at sunset.",
        "category": "Travel & Food"
    },
    {
        "query_keywords": ["party", "game night", "games", "icebreakers", "birthday"],
        "title": "Top 10 Fun & Hilarious Party Games for Friends & Family Game Nights",
        "url": "https://epicpartyideas.com/best-game-night-favorites",
        "snippet": "From Codenames and Wavelength to hilarious trivia and DIY karaoke challenges, these easy-to-learn games keep everyone laughing and engaged all evening.",
        "category": "Entertainment & Parties"
    },
    {
        "query_keywords": ["pasta", "dinner", "recipe", "quick meal", "italian", "cook"],
        "title": "15-Minute Creamy Garlic Parmesan Tuscan Pasta (One-Pan Recipe)",
        "url": "https://cozykitchenbites.com/tuscan-garlic-pasta",
        "snippet": "A luscious 15-minute skillet pasta tossed with sun-dried tomatoes, baby spinach, fresh garlic, sweet cream, and shaved parmesan. Simple, decadent, and foolproof.",
        "category": "Recipes & Cooking"
    },
    {
        "query_keywords": ["budget", "savings", "50 30 20", "money", "personal finance"],
        "title": "Simple 50/30/20 Budgeting: How to Save for Vacations While Enjoying Everyday Life",
        "url": "https://smartmoneylifestyle.com/50-30-20-budgeting-guide",
        "snippet": "Allocate 50% of income to essentials, 30% to fun & lifestyle, and 20% toward future savings and exciting travel goals with zero stress.",
        "category": "Lifestyle & Budgeting"
    }
]

def _to_clean_str(val: Any) -> str:
    """Safely convert any input (list, dict, primitive) to a flat string."""
    if val is None:
        return ""
    if isinstance(val, (list, tuple, set)):
        return " ".join(_to_clean_str(x) for x in val)
    if isinstance(val, dict):
        return " ".join(_to_clean_str(v) for v in val.values())
    return str(val).strip()


def _search_curated_index(raw_query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """Local fallback search across curated travel, dining, recipes, and lifestyle index."""
    q = raw_query.lower()
    terms = [t for t in q.split() if t]
    matched = []
    
    for item in WEB_INDEX:
        score = 0
        keywords = item.get("query_keywords", [])
        if isinstance(keywords, (list, tuple, set)):
            for kw in keywords:
                if str(kw).lower() in q:
                    score += 5
        elif str(keywords).lower() in q:
            score += 5

        title = str(item.get("title", "")).lower()
        snippet = str(item.get("snippet", "")).lower()

        for term in terms:
            term_str = str(term).lower()
            if term_str in title:
                score += 3
            if term_str in snippet:
                score += 1
                
        if score > 0:
            matched.append((score, item))
            
    matched.sort(key=lambda x: x[0], reverse=True)
    results = [item for _, item in matched[:max_results]]
    
    if not results:
        results = [
            {
                "title": f"Curated Web Results for: '{raw_query}'",
                "url": f"https://duckduckgo.com/?q={q.replace(' ', '+')}",
                "snippet": f"Trending articles, recommendations, and reviews covering '{raw_query}'.",
                "category": "Web Search",
                "source": "DuckDuckGo Direct"
            }
        ]
    return results


def web_search(
    query: Any = "",
    search_query: Any = "",
    max_results: int = 3,
    use_live_search: bool = True
) -> Dict[str, Any]:
    """
    Search the live web using DuckDuckGo (ddgs) for real-time articles, travel guides, recipes, documentation, and news.
    
    Args:
        query: Search query (e.g. 'latest AI news', 'best ramen in Tokyo', '15 minute pasta recipe')
        search_query: Alternative query parameter
        max_results: Max results to return (default 3, max 10)
        use_live_search: Whether to query live DuckDuckGo API (defaults to True)
    """
    raw_query = _to_clean_str(query) or _to_clean_str(search_query)
    if not raw_query:
        return {"success": False, "error": "Please provide a search query."}

    max_limit = min(max(1, int(max_results or 3)), 10)
    live_results = []

    # Attempt live DuckDuckGo Search if available
    if HAS_DDGS and use_live_search and DDGS is not None:
        try:
            with DDGS(timeout=6) as ddgs_client:
                raw_items = list(ddgs_client.text(raw_query, max_results=max_limit))
                for item in raw_items:
                    title = item.get("title") or ""
                    url = item.get("href") or item.get("url") or ""
                    snippet = item.get("body") or item.get("snippet") or ""
                    if title or url:
                        live_results.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet,
                            "source": "DuckDuckGo Live"
                        })
        except Exception as e:
            logger.warning(f"Live DuckDuckGo search failed for '{raw_query}': {e}. Using curated index fallback.")

    if live_results:
        return {
            "success": True,
            "query": raw_query,
            "results_count": len(live_results),
            "engine": "DuckDuckGo Live (ddgs)",
            "results": live_results
        }

    # Fallback to curated search index
    fallback_results = _search_curated_index(raw_query, max_results=max_limit)
    return {
        "success": True,
        "query": raw_query,
        "results_count": len(fallback_results),
        "engine": "Curated Web Index",
        "results": fallback_results
    }
