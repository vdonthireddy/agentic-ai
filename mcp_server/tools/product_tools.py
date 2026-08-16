"""Consumer product catalog and shopping knowledge base."""

from typing import Dict, Any, List

PRODUCT_CATALOG = [
    {
        "sku": "BREW-BARISTA-PRO",
        "product_name": "AromaMaster Smart Espresso & Coffee Maker",
        "category": "Kitchen & Coffee",
        "price_usd": 199.99,
        "discount_percent": 15,
        "rating": 4.8,
        "reviews_count": 1420,
        "stock_status": "In Stock (35 available)",
        "return_policy": "30-day risk-free home trial with free returns",
        "highlights": [
            "Built-in conical burr grinder with 15 grind settings",
            "One-touch latte, cappuccino, and cold brew presets",
            "Smartphone app to schedule morning brew from bed"
        ],
        "description": "Brew café-quality espresso, silky lattes, and iced cold brews in under 60 seconds."
    },
    {
        "sku": "AUDIO-SILENCE-MAX",
        "product_name": "CloudBeats Pro Wireless Noise-Canceling Headphones",
        "category": "Audio & Travel",
        "price_usd": 249.99,
        "discount_percent": 20,
        "rating": 4.9,
        "reviews_count": 3890,
        "stock_status": "In Stock (50 available)",
        "return_policy": "45-day satisfaction guarantee",
        "highlights": [
            "Active Noise Cancellation eliminates airplane rumble and chatter",
            "40-hour battery life with 5-minute quick charge for 4 hours playback",
            "Ultra-plush memory foam ear cushions for all-day comfort"
        ],
        "description": "Immersive studio-grade sound with industry-leading noise cancellation. Perfect for flights, study, and daily walks."
    },
    {
        "sku": "VOYAGE-SPINNER-CARRYON",
        "product_name": "Voyager Ultralight 20-inch Carry-On Suitcase",
        "category": "Luggage & Travel",
        "price_usd": 139.99,
        "discount_percent": 10,
        "rating": 4.7,
        "reviews_count": 890,
        "stock_status": "In Stock (18 available)",
        "return_policy": "Lifetime warranty covering wheels, handles, and zippers",
        "highlights": [
            "Unbreakable aerospace-grade polycarbonate hard shell",
            "Whisper-quiet 360-degree Japanese Hinomoto spinner wheels",
            "Built-in TSA lock and USB power bank charging pocket"
        ],
        "description": "Sleek, durable carry-on designed to glide effortlessly through airport terminals."
    },
    {
        "sku": "COZY-HOODIE-FLEECE",
        "product_name": "CloudKnit Premium Oversized Sherpa Hoodie",
        "category": "Apparel & Loungewear",
        "price_usd": 68.00,
        "discount_percent": 0,
        "rating": 4.9,
        "reviews_count": 2150,
        "stock_status": "In Stock (75 available)",
        "return_policy": "60-day returns and exchanges",
        "highlights": [
            "Double-brushed organic cotton and ultra-soft fleece interior",
            "Hidden kangaroo pocket phone sleeve",
            "Pre-shrunk, machine washable, and pill-resistant"
        ],
        "description": "The coziest hoodie on earth. Designed for relaxed weekends, cool movie nights, and outdoor campfires."
    },
    {
        "sku": "GLOW-CAMP-LANTERN",
        "product_name": "Sunbeam Pop-Up Solar Camping Lantern & Power Bank",
        "category": "Outdoor & Adventure",
        "price_usd": 34.99,
        "discount_percent": 10,
        "rating": 4.6,
        "reviews_count": 640,
        "stock_status": "In Stock (40 available)",
        "return_policy": "30-day money-back guarantee",
        "highlights": [
            "Collapsible silicone design packs down to 1-inch flat",
            "Recharges via built-in solar panel or USB-C fast charging",
            "Charges your smartphone in emergencies"
        ],
        "description": "Versatile waterproof ambient lighting for camping, stargazing, beach bonfires, and backyard dinners."
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


def product_knowledge(
    query: Any = "",
    product_name: Any = "",
    sku: Any = "",
    category: Any = ""
) -> Dict[str, Any]:
    """
    Search the shopping catalog for popular products, gift ideas, prices, discounts, reviews, and return policies.
    
    Args:
        query: Search term (e.g. 'coffee maker', 'headphones', 'suitcase', 'hoodie', 'camping')
        product_name: Specific item name
        sku: Product SKU
        category: Filter by category (e.g. 'Kitchen & Coffee', 'Audio & Travel', 'Apparel & Loungewear')
    """
    clean_query = _to_clean_str(query)
    clean_name = _to_clean_str(product_name)
    clean_sku = _to_clean_str(sku)
    clean_cat = _to_clean_str(category)

    search_term = (clean_query or clean_name or clean_sku or clean_cat or "").lower()
    
    matched = []
    for item in PRODUCT_CATALOG:
        score = 0
        if sku and sku.lower() in item["sku"].lower():
            score += 10
        if search_term in item["sku"].lower():
            score += 8
        if search_term in item["product_name"].lower():
            score += 6
        if search_term in item["category"].lower():
            score += 4
        if search_term in item["description"].lower():
            score += 2
        for h in item.get("highlights", []):
            if search_term in h.lower():
                score += 3
            
        if score > 0:
            matched.append((score, item))
            
    matched.sort(key=lambda x: x[0], reverse=True)
    results = [item for _, item in matched]
    
    if not results:
        # If no specific match, return top featured products
        results = PRODUCT_CATALOG[:3]
        
    return {
        "success": True,
        "search_term": search_term,
        "items_found": len(results),
        "products": results
    }
