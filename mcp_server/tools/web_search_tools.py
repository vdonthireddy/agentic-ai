"""Web search engine tool with real-world travel, dining, recipes, and lifestyle recommendations."""

from typing import Dict, Any, List

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


def web_search(
    query: Any = "",
    search_query: Any = "",
    max_results: int = 3
) -> Dict[str, Any]:
    """
    Search the web for travel guides, delicious recipes, fun party ideas, lifestyle tips, and articles.
    
    Args:
        query: Search query (e.g. 'best ramen in Tokyo', 'fun party game ideas', '15 minute pasta recipe')
        search_query: Alternative query parameter
        max_results: Max results to return
    """
    raw_query = _to_clean_str(query) or _to_clean_str(search_query)
    q = raw_query.lower()
    if not q:
        return {"success": False, "error": "Please provide a search query."}
        
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
                "title": f"Top Curated Recommendations for: '{raw_query}'",
                "url": f"https://www.google.com/search?q={q.replace(' ', '+')}",
                "snippet": f"Trending articles, local recommendations, and reviews covering '{raw_query}'.",
                "category": "Web Search"
            }
        ]
        
    return {
        "success": True,
        "query": raw_query,
        "results_count": len(results),
        "results": results
    }
