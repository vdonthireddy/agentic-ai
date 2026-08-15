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

def web_search(
    query: str = "",
    search_query: str = "",
    max_results: int = 3
) -> Dict[str, Any]:
    """
    Search the web for travel guides, delicious recipes, fun party ideas, lifestyle tips, and articles.
    
    Args:
        query: Search query (e.g. 'best ramen in Tokyo', 'fun party game ideas', '15 minute pasta recipe')
        search_query: Alternative query parameter
        max_results: Max results to return
    """
    q = (query or search_query or "").strip().lower()
    if not q:
        return {"success": False, "error": "Please provide a search query."}
        
    terms = q.split()
    matched = []
    
    for item in WEB_INDEX:
        score = 0
        for kw in item["query_keywords"]:
            if kw in q:
                score += 5
        for term in terms:
            if term in item["title"].lower():
                score += 3
            if term in item["snippet"].lower():
                score += 1
                
        if score > 0:
            matched.append((score, item))
            
    matched.sort(key=lambda x: x[0], reverse=True)
    results = [item for _, item in matched[:max_results]]
    
    if not results:
        results = [
            {
                "title": f"Top Curated Recommendations for: '{query or search_query}'",
                "url": f"https://www.google.com/search?q={q.replace(' ', '+')}",
                "snippet": f"Trending articles, local recommendations, and reviews covering '{query or search_query}'.",
                "category": "Web Search"
            }
        ]
        
    return {
        "success": True,
        "query": query or search_query,
        "results_count": len(results),
        "results": results
    }
