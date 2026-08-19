"""Tests for SSE streaming utilities."""

import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from streaming import format_sse_event, format_sse_done, format_sse_keepalive, StreamAccumulator


class TestFormatSSEEvent:
    def test_basic_event(self):
        result = format_sse_event({"content": "hello"})
        assert result.startswith("data: ")
        assert result.endswith("\n\n")
        data = json.loads(result.strip().split("data: ", 1)[1])
        assert data["content"] == "hello"

    def test_event_with_type(self):
        result = format_sse_event({"token": "hi"}, event_type="token_delta")
        assert "event: token_delta" in result
        assert "data: " in result

    def test_done_event(self):
        result = format_sse_done()
        assert result == "data: [DONE]\n\n"

    def test_keepalive(self):
        result = format_sse_keepalive()
        assert result == ": keepalive\n\n"


class TestStreamAccumulator:
    def test_accumulate_content(self):
        acc = StreamAccumulator()
        acc.add_delta({"content": "Hello "})
        acc.add_delta({"content": "world!"})
        assert acc.full_content == "Hello world!"

    def test_accumulate_tool_calls(self):
        acc = StreamAccumulator()
        acc.add_delta({
            "tool_calls": [{
                "index": 0,
                "id": "call_abc123",
                "function": {"name": "calculator", "arguments": ""}
            }]
        })
        acc.add_delta({
            "tool_calls": [{
                "index": 0,
                "function": {"arguments": '{"expr": "2+2"}'}
            }]
        })
        
        tc = acc.accumulated_tool_calls
        assert len(tc) == 1
        assert tc[0]["function"]["name"] == "calculator"
        assert tc[0]["function"]["arguments"] == '{"expr": "2+2"}'
        assert tc[0]["id"] == "call_abc123"

    def test_accumulate_usage(self):
        acc = StreamAccumulator()
        acc.add_usage({"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150})
        assert acc.prompt_tokens == 100
        assert acc.completion_tokens == 50
        assert acc.total_tokens == 150

    def test_empty_accumulator(self):
        acc = StreamAccumulator()
        assert acc.full_content == ""
        assert acc.accumulated_tool_calls == []
        assert acc.prompt_tokens == 0

    def test_multiple_tool_calls(self):
        acc = StreamAccumulator()
        acc.add_delta({
            "tool_calls": [
                {"index": 0, "id": "call_1", "function": {"name": "weather", "arguments": ""}},
                {"index": 1, "id": "call_2", "function": {"name": "calculator", "arguments": ""}}
            ]
        })
        acc.add_delta({
            "tool_calls": [
                {"index": 0, "function": {"arguments": '{"city":"NYC"}'}},
                {"index": 1, "function": {"arguments": '{"expr":"1+1"}'}}
            ]
        })

        tc = acc.accumulated_tool_calls
        assert len(tc) == 2
        assert tc[0]["function"]["name"] == "weather"
        assert tc[1]["function"]["name"] == "calculator"
