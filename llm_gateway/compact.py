"""
Context Compaction & Conversation History Summarizer.

Author: Vijay Donthireddy & Architect Kavini
Description: Prevents context window exhaustion, token bloat, and 'Lost in the Middle'
hallucinations by condensing older conversation turns into structured executive summaries.
"""

from typing import List, Dict, Any, Tuple
import json


def estimate_tokens(text: str) -> int:
    """Rough estimate of token count (~4 characters per token)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def estimate_messages_tokens(messages: List[Dict[str, str]]) -> int:
    """Estimates total token weight across a list of chat messages."""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += estimate_tokens(content) + 4  # overhead per message
        elif isinstance(content, list):
            total += estimate_tokens(str(content)) + 4
    return total


def summarize_transcript_fallback(older_messages: List[Dict[str, str]]) -> str:
    """
    Deterministic rule-based summary extractor when offline or running without cloud LLM.
    Captures key user queries, tools used, and established facts.
    """
    user_points = []
    assistant_points = []
    tools_used = set()

    for msg in older_messages:
        role = msg.get("role")
        content = msg.get("content", "")
        
        if role == "user":
            first_line = content.strip().split("\n")[0][:120]
            if first_line and not first_line.startswith("/"):
                user_points.append(first_line)
        elif role == "assistant":
            # Check for tool mentions
            if "Tool" in content or "weather" in content or "calculate" in content or "file" in content:
                for line in content.split("\n"):
                    if any(k in line.lower() for k in ["result", "created", "saved", "temperature", "split", "dollar"]):
                        assistant_points.append(line.strip()[:100])
            else:
                first_sent = content.strip().split(".")[0][:120]
                if first_sent:
                    assistant_points.append(first_sent)

    summary_lines = [
        "### 📦 Compacted Conversation Context (Executive Summary)",
        "**Key Inquiries & Topics Covered:**",
    ]
    for pt in user_points[:4]:
        summary_lines.append(f"- {pt}")
    
    if assistant_points:
        summary_lines.append("\n**Key Results & Decisions Established:**")
        for pt in assistant_points[:4]:
            summary_lines.append(f"- {pt}")
            
    summary_lines.append("\n*Note: Earlier chat turns were condensed to preserve context memory and reduce token latency.*")
    return "\n".join(summary_lines)


async def compact_conversation_history(
    messages: List[Dict[str, str]],
    keep_recent_turns: int = 2,
    custom_summary: str = None
) -> Dict[str, Any]:
    """
    Compacts older conversation messages into a single synthesized context card.
    
    Args:
        messages: The full list of conversation messages.
        keep_recent_turns: Number of recent user+assistant turns to retain verbatim.
        custom_summary: Optional LLM-generated summary override.
        
    Returns:
        Dict with compacted messages and token savings metrics.
    """
    if not messages:
        return {
            "compacted_messages": [],
            "original_tokens": 0,
            "compacted_tokens": 0,
            "tokens_saved": 0,
            "savings_percent": 0.0,
            "summary": ""
        }

    original_tokens = estimate_messages_tokens(messages)

    # 1. Extract System Prompt(s)
    system_messages = [m for m in messages if m.get("role") == "system"]
    non_system_messages = [m for m in messages if m.get("role") != "system"]

    # If conversation is already short (<= 4 non-system messages), no need to compress
    min_threshold = max(4, keep_recent_turns * 2)
    if len(non_system_messages) <= min_threshold:
        return {
            "compacted_messages": messages,
            "original_tokens": original_tokens,
            "compacted_tokens": original_tokens,
            "tokens_saved": 0,
            "savings_percent": 0.0,
            "summary": "Conversation is already compact."
        }

    # 2. Slice older messages vs recent working memory
    recent_slice_count = keep_recent_turns * 2
    older_messages = non_system_messages[:-recent_slice_count]
    recent_messages = non_system_messages[-recent_slice_count:]

    # 3. Generate structured executive summary
    summary_text = custom_summary or summarize_transcript_fallback(older_messages)

    summary_message = {
        "role": "system",
        "content": summary_text,
        "is_compaction_summary": True
    }

    # 4. Assemble new compacted history
    compacted_messages = []
    if system_messages:
        compacted_messages.extend(system_messages)
    compacted_messages.append(summary_message)
    compacted_messages.extend(recent_messages)

    compacted_tokens = estimate_messages_tokens(compacted_messages)
    tokens_saved = max(0, original_tokens - compacted_tokens)
    savings_percent = round((tokens_saved / max(1, original_tokens)) * 100.0, 1)

    return {
        "compacted_messages": compacted_messages,
        "original_tokens": original_tokens,
        "compacted_tokens": compacted_tokens,
        "tokens_saved": tokens_saved,
        "savings_percent": savings_percent,
        "summary": summary_text,
        "messages_pruned_count": len(older_messages)
    }
