"""Search and knowledge retrieval mock tool for MCP Server."""

from typing import Dict, Any, List

# Curated knowledge index for simulated real-time lookups
KNOWLEDGE_BASE = [
    {
        "topic": "MCP Protocol",
        "keywords": ["mcp", "model context protocol", "anthropic", "tools", "skills", "resources"],
        "content": "Model Context Protocol (MCP) standardizes how AI applications connect with tools, data sources, and prompt templates. It supports Tools (executable functions), Resources (read-only data streams), and Prompts (reusable skills/templates)."
    },
    {
        "topic": "LiteLLM",
        "keywords": ["litellm", "gateway", "proxy", "logging", "routing", "ollama"],
        "content": "LiteLLM is a lightweight I/O library and proxy to call 100+ LLM APIs using the OpenAI format. It supports Ollama, vLLM, Anthropic, OpenAI, Bedrock, and has native support for custom callbacks, retries, fallbacks, and usage tracking."
    },
    {
        "topic": "Ollama Local Models",
        "keywords": ["ollama", "local llm", "llama3", "qwen", "mistral", "tools"],
        "content": "Ollama allows running open-weight LLMs locally on macOS, Linux, and Windows. Models like Qwen2.5-Coder and Llama 3.2 support JSON schema tool calling and structured outputs with high fidelity."
    },
    {
        "topic": "AI Agent Loop",
        "keywords": ["agent", "reasoning", "react", "tool use", "function calling"],
        "content": "An AI Agent loop executes ReAct (Reason + Act): receiving user prompt, selecting tools, executing them via MCP protocol, observing results, and refining the response iteratively until completion."
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


def search_knowledge(query: Any = "", limit: int = 3) -> Dict[str, Any]:
    """
    Search the agent's internal knowledge base for definitions, guides, and technical concepts.
    """
    raw_query = _to_clean_str(query)
    query_lower = raw_query.lower()
    query_tokens = set(query_lower.split())
    
    scored_results = []
    for item in KNOWLEDGE_BASE:
        score = 0
        for kw in item["keywords"]:
            if kw in query_lower:
                score += 3
            for tok in query_tokens:
                if tok in kw:
                    score += 1
        if any(tok in item["content"].lower() for tok in query_tokens):
            score += 1
        
        if score > 0:
            scored_results.append((score, item))
            
    scored_results.sort(key=lambda x: x[0], reverse=True)
    matches = [item for _, item in scored_results[:limit]]
    
    return {
        "success": True,
        "query": raw_query,
        "results_found": len(matches),
        "matches": matches if matches else [
            {"topic": "General Notice", "content": f"No direct match found for '{raw_query}'. Please use general reasoning or python execution."}
        ]
    }

# Export aliases for seamless compatibility
search_knowledge_base = search_knowledge
knowledge_base_search = search_knowledge
