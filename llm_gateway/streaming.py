"""SSE Streaming utilities for the LLM Gateway.

Provides helpers for formatting Server-Sent Events, streaming LiteLLM
responses as SSE deltas, and accumulating chunks for post-stream audit logging.
"""

import json
import time
import uuid
from typing import Dict, Any, List, Optional, AsyncIterator
from dataclasses import dataclass, field


def format_sse_event(data: Dict[str, Any], event_type: Optional[str] = None) -> str:
    """Format a dictionary as an SSE event string."""
    lines = []
    if event_type:
        lines.append(f"event: {event_type}")
    lines.append(f"data: {json.dumps(data)}")
    lines.append("")  # Trailing newline to end the event
    return "\n".join(lines) + "\n"


def format_sse_done() -> str:
    """Format the terminal SSE [DONE] event (OpenAI-compatible)."""
    return "data: [DONE]\n\n"


def format_sse_keepalive() -> str:
    """Format a keepalive comment for SSE streams."""
    return ": keepalive\n\n"


@dataclass
class StreamAccumulator:
    """Accumulates streamed chunks for post-stream audit logging.
    
    Collects token deltas, tool call fragments, and usage statistics
    so a complete audit record can be written after the stream ends.
    """
    content_parts: List[str] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    finish_reason: Optional[str] = None
    _tool_call_buffers: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    def add_delta(self, delta: Dict[str, Any]):
        """Process a single streamed delta from LiteLLM."""
        # Accumulate content text
        content = delta.get("content")
        if content:
            self.content_parts.append(content)

        # Accumulate tool call fragments
        tc_list = delta.get("tool_calls")
        if tc_list:
            for tc in tc_list:
                idx = tc.get("index", 0)
                if idx not in self._tool_call_buffers:
                    self._tool_call_buffers[idx] = {
                        "id": tc.get("id", f"call_{uuid.uuid4().hex[:8]}"),
                        "type": "function",
                        "function": {"name": "", "arguments": ""}
                    }
                buf = self._tool_call_buffers[idx]
                if tc.get("id"):
                    buf["id"] = tc["id"]
                fn = tc.get("function", {})
                if fn.get("name"):
                    buf["function"]["name"] = fn["name"]
                if fn.get("arguments"):
                    buf["function"]["arguments"] += fn["arguments"]

    def add_usage(self, usage: Dict[str, Any]):
        """Record token usage from the final chunk or stream metadata."""
        self.prompt_tokens = usage.get("prompt_tokens", self.prompt_tokens)
        self.completion_tokens = usage.get("completion_tokens", self.completion_tokens)
        self.total_tokens = usage.get("total_tokens",
                                       self.prompt_tokens + self.completion_tokens)

    @property
    def full_content(self) -> str:
        """Return the fully accumulated content string."""
        return "".join(self.content_parts)

    @property
    def accumulated_tool_calls(self) -> List[Dict[str, Any]]:
        """Return the fully assembled tool calls list."""
        if self._tool_call_buffers and not self.tool_calls:
            self.tool_calls = [
                self._tool_call_buffers[idx]
                for idx in sorted(self._tool_call_buffers.keys())
            ]
        return self.tool_calls


async def stream_litellm_response(
    litellm_stream,
    request_id: str,
    model: str
) -> AsyncIterator[str]:
    """Consume an async LiteLLM streaming response and yield SSE event strings.
    
    Yields structured SSE events:
    - event: token_delta   — each content token chunk
    - event: tool_call     — tool call fragment
    - event: usage         — token usage statistics (final chunk)
    - data: [DONE]         — stream termination
    
    The caller should create a StreamAccumulator to capture the full
    response for audit logging after the stream ends.
    """
    accumulator = StreamAccumulator(model=model)
    
    try:
        async for chunk in litellm_stream:
            # Extract the choice delta
            choices = getattr(chunk, "choices", [])
            if not choices:
                continue
                
            choice = choices[0]
            delta = getattr(choice, "delta", None)
            finish_reason = getattr(choice, "finish_reason", None)

            if delta:
                delta_dict = delta.model_dump() if hasattr(delta, "model_dump") else dict(delta)
                accumulator.add_delta(delta_dict)

                content = delta_dict.get("content")
                if content:
                    yield format_sse_event({
                        "request_id": request_id,
                        "delta": {"content": content},
                        "model": model
                    }, event_type="token_delta")

                tc_list = delta_dict.get("tool_calls")
                if tc_list:
                    yield format_sse_event({
                        "request_id": request_id,
                        "delta": {"tool_calls": tc_list},
                        "model": model
                    }, event_type="tool_call")

            if finish_reason:
                accumulator.finish_reason = finish_reason

            # Extract usage if available (typically on the last chunk)
            usage = getattr(chunk, "usage", None)
            if usage:
                usage_dict = usage.model_dump() if hasattr(usage, "model_dump") else {}
                if usage_dict:
                    accumulator.add_usage(usage_dict)
                    yield format_sse_event({
                        "request_id": request_id,
                        "usage": usage_dict
                    }, event_type="usage")

    except Exception as e:
        yield format_sse_event({
            "request_id": request_id,
            "error": str(e)
        }, event_type="error")

    yield format_sse_done()
    
    # Attach the accumulator as an attribute for the caller to retrieve
    stream_litellm_response._last_accumulator = accumulator
