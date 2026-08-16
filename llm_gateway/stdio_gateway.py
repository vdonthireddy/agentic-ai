"""Stdio Transport Server for LLM Gateway.
Reads JSON request lines from stdin and writes JSON response lines to stdout.
Redirects audit and telemetry logs to stderr or SQLite DB.
"""

import sys
import os
import json
import time
import uuid
import asyncio
import logging
from typing import Dict, Any, Optional

# Ensure parent directory in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set logging to stderr so stdout remains purely JSON
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("llm_gateway_stdio")

import litellm
from llm_gateway.config import config
from llm_gateway.logger import audit_logger
from llm_gateway.db import get_stats, query_logs, init_db

# Suppress LiteLLM stdout printing
litellm.suppress_debug_info = True


async def handle_stdio_request(req_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single JSON command/request dict and return the response dict."""
    action = req_data.get("action") or req_data.get("method") or "chat_completions"
    
    # 1. Health / Ping
    if action in ("health", "ping"):
        return {
            "status": "healthy",
            "service": "llm-gateway",
            "transport": "stdio",
            "default_model": config.default_model,
            "ollama_api_base": config.ollama_api_base
        }

    # 2. Models list
    if action in ("models", "get_models", "list_models"):
        return {
            "object": "list",
            "data": [
                {"id": "ollama/qwen2.5-coder:7b", "object": "model", "owned_by": "ollama"},
                {"id": "ollama/llama3.2", "object": "model", "owned_by": "ollama"},
                {"id": "ollama/mistral:latest", "object": "model", "owned_by": "ollama"},
                {"id": "ollama/gemma2:2b", "object": "model", "owned_by": "ollama"}
            ],
            "default_model": config.default_model
        }

    # 3. Statistics
    if action in ("stats", "get_stats"):
        return get_stats(db_path=config.db_path)

    # 4. Logs
    if action in ("logs", "get_logs"):
        limit = int(req_data.get("limit", 50))
        offset = int(req_data.get("offset", 0))
        return {
            "logs": query_logs(
                limit=limit,
                offset=offset,
                session_id=req_data.get("session_id"),
                agent_name=req_data.get("agent_name"),
                model=req_data.get("model"),
                db_path=config.db_path
            )
        }

    # 5. Chat Completions (Default)
    caller_id = req_data.get("caller_id") or "stdio_caller"
    agent_name = req_data.get("agent_name") or "Agentic-AI-StdioClient"
    session_id = req_data.get("session_id") or f"session_{uuid.uuid4().hex[:8]}"
    caller_context_data = req_data.get("caller_context") or {}
    skill_names = list(req_data.get("skill_names") or [])
    
    tools = req_data.get("tools")
    tool_names = []
    if tools:
        for t in tools:
            if isinstance(t, dict):
                fn = t.get("function", {})
                name = fn.get("name") if isinstance(fn, dict) else t.get("name")
                if name:
                    tool_names.append(name)

    target_model = req_data.get("model") or config.default_model
    if not target_model.startswith("ollama/") and not target_model.startswith("openai/"):
        target_model = f"ollama/{target_model}"

    messages = req_data.get("messages") or []
    temperature = float(req_data.get("temperature", 0.1))
    
    start_time = time.time()
    try:
        litellm_kwargs: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "api_base": config.ollama_api_base,
            "temperature": temperature
        }
        if tools:
            litellm_kwargs["tools"] = tools
        if req_data.get("tool_choice"):
            litellm_kwargs["tool_choice"] = req_data.get("tool_choice")
        if req_data.get("max_tokens"):
            litellm_kwargs["max_tokens"] = int(req_data.get("max_tokens"))

        if target_model.startswith("ollama/"):
            litellm_kwargs["stop"] = ["### User:", "### User\n", "### Human:", "\n\nUser:", "\n\nHuman:"]

        response = await litellm.acompletion(**litellm_kwargs)
        latency_ms = (time.time() - start_time) * 1000

        choice = response.choices[0]
        msg = choice.message
        resp_content = getattr(msg, "content", None)
        
        resp_tool_calls = []
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                if hasattr(tc, "model_dump"):
                    resp_tool_calls.append(tc.model_dump())
                elif isinstance(tc, dict):
                    resp_tool_calls.append(tc)
                else:
                    resp_tool_calls.append({
                        "id": getattr(tc, "id", str(uuid.uuid4())),
                        "type": getattr(tc, "type", "function"),
                        "function": {
                            "name": getattr(getattr(tc, "function", None), "name", ""),
                            "arguments": getattr(getattr(tc, "function", None), "arguments", "{}")
                        }
                    })

        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens) if usage else 0

        # Log call in SQLite audit system
        audit_logger.log_call(
            caller_id=caller_id,
            agent_name=agent_name,
            session_id=session_id,
            caller_context=caller_context_data,
            model=target_model,
            skill_names=skill_names,
            tool_names=tool_names,
            request_messages=messages,
            request_tools=tools,
            request_params={"temperature": temperature},
            response_content=resp_content,
            response_tool_calls=resp_tool_calls,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            status="SUCCESS"
        )

        return {
            "id": getattr(response, "id", f"chatcmpl_{uuid.uuid4().hex[:8]}"),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": target_model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": resp_content,
                        "tool_calls": resp_tool_calls if resp_tool_calls else None
                    },
                    "finish_reason": getattr(choice, "finish_reason", "stop")
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            }
        }

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        err_msg = str(e)
        logger.error(f"Stdio Gateway Execution Error on {target_model}: {err_msg}")

        audit_logger.log_call(
            caller_id=caller_id,
            agent_name=agent_name,
            session_id=session_id,
            caller_context=caller_context_data,
            model=target_model,
            skill_names=skill_names,
            tool_names=tool_names,
            request_messages=messages,
            request_tools=tools,
            request_params={"temperature": temperature},
            response_content=None,
            response_tool_calls=[],
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            latency_ms=latency_ms,
            status="ERROR",
            error_message=err_msg
        )

        return {
            "error": "LLM Gateway Execution Error",
            "message": err_msg,
            "status": "ERROR"
        }


async def run_stdio_loop():
    """Main event loop listening on stdin and responding on stdout."""
    init_db(config.db_path)
    logger.info(f"LLM Gateway Stdio Transport Initialized. Default model: {config.default_model}")
    
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        line_bytes = await reader.readline()
        if not line_bytes:
            # EOF reached
            break
        
        line_str = line_bytes.decode("utf-8").strip()
        if not line_str:
            continue
        
        try:
            req_data = json.loads(line_str)
            res_data = await handle_stdio_request(req_data)
        except json.JSONDecodeError as err:
            res_data = {"error": f"Invalid JSON on stdin: {str(err)}", "status": "ERROR"}
        except Exception as e:
            res_data = {"error": f"Internal Server Error: {str(e)}", "status": "ERROR"}

        # Write output line to stdout
        output_line = json.dumps(res_data) + "\n"
        sys.stdout.write(output_line)
        sys.stdout.flush()


def main():
    try:
        asyncio.run(run_stdio_loop())
    except (KeyboardInterrupt, BrokenPipeError):
        pass


if __name__ == "__main__":
    main()
