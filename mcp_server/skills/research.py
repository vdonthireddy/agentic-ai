"""Research and technical synthesis skill definition and prompts."""

from typing import Dict, Any

RESEARCH_SKILL_METADATA = {
    "name": "research_skill",
    "description": "Deep research and technical synthesis skill for investigating complex topics, comparing architectures, and summarizing evidence.",
    "version": "1.0.0",
    "recommended_tools": ["search_knowledge", "execute_python", "workspace_file_ops"]
}

def render_research_skill(topic: str, context: str = "", scope: str = "comprehensive") -> str:
    """
    Renders structured instructions for conducting technical research.
    """
    return f"""# Skill: Technical Research & Synthesis

## Research Topic: {topic}
## Scope: {scope}
## Prior Context: {context if context else "None provided"}

## Research Protocol:
1. **Explore & Query**: Use `search_knowledge` or workspace tools to gather relevant facts, definitions, and technical parameters.
2. **Synthesize Key Concepts**: Break down the core architecture, pros/cons, design tradeoffs, and operational considerations.
3. **Compare & Contrast**: If multiple approaches exist, compare them systematically across latency, scalability, security, and developer ergonomics.
4. **Structured Deliverable**:
   - Executive Overview
   - Architectural Deep-Dive
   - Comparative Analysis / Trade-Off Matrix
   - Recommended Strategy & Implementation Roadmap
"""
