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

def search_knowledge(query: str, limit: int = 3) -> Dict[str, Any]:
    """
    Search the agent's internal knowledge base for definitions, guides, and technical concepts.
    """
    query_lower = query.lower()
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
        "query": query,
        "results_found": len(matches),
        "matches": matches if matches else [
            {"topic": "General Notice", "content": f"No direct match found for '{query}'. Please use general reasoning or python execution."}
        ]
    }
