"""Agentic AI Engine orchestrating MCP Tools/Skills and LLM Gateway."""

import json
import uuid
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field

try:
    from .mcp_client import MCPClientManager
    from .gateway_client import LLMGatewayClient
except (ImportError, ValueError):
    from mcp_client import MCPClientManager
    from gateway_client import LLMGatewayClient

@dataclass
class AgentRunResult:
    response: str
    tool_calls_executed: List[Dict[str, Any]] = field(default_factory=list)
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    session_id: str = ""
    active_skills: List[str] = field(default_factory=list)

class AgenticLLMAgent:
    """
    Autonomous AI Agent that:
    1. Connects to MCP Server for dynamic tool & skill discovery.
    2. Communicates with local Ollama strictly through the LiteLLM Gateway.
    3. Manages conversational state, skill injection, and multi-step tool execution loops.
    """

    def __init__(
        self,
        gateway_url: str = "http://localhost:8000",
        agent_name: str = "Ollama-MCP-Agent",
        caller_id: str = "user_primary",
        model: str = "ollama/qwen2.5-coder:7b",
        session_id: Optional[str] = None,
        max_tool_iterations: int = 6,
        on_step_callback: Optional[Callable[[str, Any], None]] = None
    ):
        self.session_id = session_id or f"sess_{uuid.uuid4().hex[:8]}"
        self.gateway = LLMGatewayClient(
            base_url=gateway_url,
            agent_name=agent_name,
            caller_id=caller_id,
            session_id=self.session_id
        )
        self.mcp = MCPClientManager()
        self.model = model
        self.max_tool_iterations = max_tool_iterations
        self.on_step_callback = on_step_callback
        
        self.messages: List[Dict[str, Any]] = []
        self.active_skills: List[str] = []
        self.base_system_prompt: str = (
            "You are an intelligent autonomous AI assistant equipped with Model Context Protocol (MCP) tools and domain skills. "
            "When asked to perform calculations, run code, inspect files, check system status, or search knowledge, "
            "always invoke the relevant tools rather than guessing. Think step-by-step and provide clear, well-reasoned answers."
        )
        self.system_prompt: str = self.base_system_prompt
        self.tools_schema: List[Dict[str, Any]] = []
        self._connected = False

    def clear_history(self, reset_skills: bool = False):
        """Reset conversation history while preserving or clearing active skills."""
        if reset_skills:
            self.active_skills = []
            self.system_prompt = self.base_system_prompt
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def reset_skills(self):
        """Clear all active skills and reset system prompt to default."""
        self.clear_history(reset_skills=True)

    def _emit(self, event_type: str, data: Any):
        if self.on_step_callback:
            try:
                self.on_step_callback(event_type, data)
            except Exception:
                pass

    async def initialize(self):
        """Connect to MCP server, discover tools and skills."""
        if not self._connected:
            self._emit("mcp_connecting", "Connecting to MCP Server...")
            await self.mcp.connect()
            self.tools_schema = await self.mcp.list_tools_for_llm()
            self._connected = True
            self._emit("mcp_connected", {
                "tools": [t["function"]["name"] for t in self.tools_schema],
                "skills": [s["name"] for s in await self.mcp.list_skills()]
            })

    async def close(self):
        """Clean up MCP connections."""
        if self._connected:
            await self.mcp.disconnect()
            self._connected = False

    async def activate_skill(self, skill_name: str, arguments: Optional[Dict[str, str]] = None) -> str:
        """
        Fetches the specialized skill prompt from the MCP Server and activates it in the agent context.
        """
        await self.initialize()
        skill_prompt = await self.mcp.get_skill_prompt(skill_name, arguments)
        if skill_name not in self.active_skills:
            self.active_skills.append(skill_name)
        
        # Inject skill instructions into system prompt
        self.system_prompt += f"\n\n--- [ACTIVE SKILL: {skill_name}] ---\n{skill_prompt}\n-----------------------------------"
        self._emit("skill_activated", {"skill": skill_name, "prompt_preview": skill_prompt[:120] + "..."})
        return skill_prompt

    async def run(self, user_input: str, caller_context: Optional[Dict[str, Any]] = None) -> AgentRunResult:
        """
        Execute an agent turn with tool-calling loop through the LLM Gateway.
        """
        await self.initialize()

        # Build initial conversation if empty
        if not self.messages:
            self.messages.append({"role": "system", "content": self.system_prompt})
        
        self.messages.append({"role": "user", "content": user_input})
        self._emit("user_message", user_input)

        tool_calls_executed = []
        total_prompt_tokens = 0
        total_completion_tokens = 0
        consecutive_duplicate_calls = 0
        last_tool_signature = None

        iteration = 0
        while iteration < self.max_tool_iterations:
            iteration += 1
            self._emit("llm_calling", {
                "iteration": iteration,
                "model": self.model,
                "active_skills": self.active_skills,
                "tools_available": [t["function"]["name"] for t in self.tools_schema]
            })

            # Call LLM Gateway
            response = await self.gateway.chat_completion(
                messages=self.messages,
                tools=self.tools_schema if self.tools_schema else None,
                model=self.model,
                skill_names=self.active_skills,
                caller_context=caller_context,
                temperature=0.1
            )

            # Record tokens
            usage = response.get("usage", {})
            total_prompt_tokens += usage.get("prompt_tokens", 0)
            total_completion_tokens += usage.get("completion_tokens", 0)

            choice = response["choices"][0]
            assistant_msg = choice["message"]
            self.messages.append(assistant_msg)

            tool_calls = assistant_msg.get("tool_calls")
            if not tool_calls:
                # Check if model outputted tool call as text in content (common in small Ollama models)
                raw_content = assistant_msg.get("content") or ""
                import re
                match = re.search(r"Tool Calls:\s*(\[\s*\{.*?\}\s*\])", raw_content, re.DOTALL | re.IGNORECASE)
                if not match:
                    match = re.search(r"(\[\s*\{\s*\"(?:id|type|function)\".*?\}\s*\])", raw_content, re.DOTALL)
                if match:
                    try:
                        extracted = json.loads(match.group(1))
                        if isinstance(extracted, list) and len(extracted) > 0 and isinstance(extracted[0], dict):
                            tool_calls = extracted
                            assistant_msg["tool_calls"] = tool_calls
                    except Exception:
                        pass

            if not tool_calls:
                # LLM finished reasoning and returned final text
                final_content = assistant_msg.get("content", "")
                if final_content and ("### User" in final_content or "### Human" in final_content):
                    import re
                    final_content = re.split(r"###\s*(?:User|Human)", final_content)[0].strip()
                self._emit("final_answer", final_content)
                return AgentRunResult(
                    response=final_content,
                    tool_calls_executed=tool_calls_executed,
                    total_prompt_tokens=total_prompt_tokens,
                    total_completion_tokens=total_completion_tokens,
                    session_id=self.session_id,
                    active_skills=self.active_skills
                )

            # Handle Tool Calls
            loop_detected = False
            for tc in tool_calls:
                func_info = tc.get("function", {})
                tool_name = func_info.get("name", "")
                args_raw = func_info.get("arguments", "{}")
                
                try:
                    args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                except Exception:
                    args = {"raw_input": args_raw}

                # Check if this exact tool call with these args was just executed
                current_sig = f"{tool_name}:{json.dumps(args, sort_keys=True)}"
                if current_sig == last_tool_signature:
                    consecutive_duplicate_calls += 1
                else:
                    consecutive_duplicate_calls = 0
                    last_tool_signature = current_sig

                self._emit("tool_executing", {"tool": tool_name, "args": args})

                if consecutive_duplicate_calls >= 1:
                    # Model is repeating itself: reuse existing output and break loop
                    loop_detected = True
                    tool_output = tool_calls_executed[-1]["output"] if tool_calls_executed else "{}"
                else:
                    # Execute against MCP Server
                    try:
                        tool_output = await self.mcp.execute_tool(tool_name, args)
                    except Exception as e:
                        tool_output = json.dumps({"error": f"Tool execution failed: {str(e)}"})

                    self._emit("tool_result", {"tool": tool_name, "output_preview": str(tool_output)[:200]})

                    tool_calls_executed.append({
                        "tool": tool_name,
                        "arguments": args,
                        "output": tool_output
                    })

                # Append tool response message
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", f"call_{uuid.uuid4().hex[:6]}"),
                    "name": tool_name,
                    "content": tool_output
                })

            # If the model is stuck in a repeating tool call loop, force synthesis or return cleanly
            if loop_detected or consecutive_duplicate_calls >= 1:
                # Attempt one final completion without tools so the model summarizes the result
                try:
                    synth_resp = await self.gateway.chat_completion(
                        messages=self.messages,
                        tools=None,
                        model=self.model,
                        skill_names=self.active_skills,
                        caller_context=caller_context,
                        temperature=0.1
                    )
                    synth_content = synth_resp["choices"][0]["message"].get("content", "")
                    if synth_content:
                        return AgentRunResult(
                            response=synth_content,
                            tool_calls_executed=tool_calls_executed,
                            total_prompt_tokens=total_prompt_tokens,
                            total_completion_tokens=total_completion_tokens,
                            session_id=self.session_id,
                            active_skills=self.active_skills
                        )
                except Exception:
                    pass
                
                # Fallback: extract latest tool output
                fallback_content = tool_calls_executed[-1]["output"] if tool_calls_executed else "Operation completed."
                return AgentRunResult(
                    response=fallback_content,
                    tool_calls_executed=tool_calls_executed,
                    total_prompt_tokens=total_prompt_tokens,
                    total_completion_tokens=total_completion_tokens,
                    session_id=self.session_id,
                    active_skills=self.active_skills
                )

        # If loop reached max iterations, return last valid content or tool output
        last_content = None
        for m in reversed(self.messages):
            if m.get("role") == "assistant" and m.get("content"):
                last_content = m["content"]
                break
        if not last_content and tool_calls_executed:
            last_content = tool_calls_executed[-1]["output"]
            
        return AgentRunResult(
            response=last_content or "Maximum reasoning steps reached.",
            tool_calls_executed=tool_calls_executed,
            total_prompt_tokens=total_prompt_tokens,
            total_completion_tokens=total_completion_tokens,
            session_id=self.session_id,
            active_skills=self.active_skills
        )
