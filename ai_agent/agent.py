import json
import uuid
import time
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
    conversation_id: str = ""
    turn_id: str = ""
    request_ids: List[str] = field(default_factory=list)
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
        model: str = "ollama/gemma2:2b",
        session_id: Optional[str] = None,
        max_tool_iterations: int = 6,
        on_step_callback: Optional[Callable[[str, Any], None]] = None,
        gateway_transport: Optional[str] = None
    ):
        self.session_id = session_id or f"sess_{uuid.uuid4().hex[:8]}"
        self.gateway = LLMGatewayClient(
            base_url=gateway_url,
            agent_name=agent_name,
            caller_id=caller_id,
            session_id=self.session_id,
            transport=gateway_transport
        )
        self.mcp = MCPClientManager()
        self.model = model
        self.max_tool_iterations = max_tool_iterations
        self.on_step_callback = on_step_callback
        
        self.messages: List[Dict[str, Any]] = []
        self.active_skills: List[str] = []
        self.base_system_prompt: str = (
            "You are an intelligent autonomous AI assistant equipped with Model Context Protocol (MCP) tools and dynamic domain skills. "
            "When asked to perform calculations, run code, inspect files, check system status, or search knowledge, "
            "always invoke the relevant tools rather than guessing. Think step-by-step and provide clear, well-reasoned answers.\n\n"
            "Progressive Disclosure: You have access to specialized domain skills (e.g. travel planner, financial advisor, code reviewer, chef meal planner, shopping assistant, party planner, data analysis, research). "
            "Use tool 'discover_skills' to inspect available domain skills, and call tool 'load_skill' (with 'skill_name', e.g. 'travel_planner_skill') to dynamically load full domain guidelines, persona constraints, and execution checklists on-demand."
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
        """Clean up MCP and Gateway connections."""
        if self._connected:
            await self.mcp.disconnect()
            self._connected = False
        await self.gateway.close()

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

        # Generate unique Turn ID for this user interaction
        turn_id = (caller_context.get("turn_id") if caller_context else None) or f"turn_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
        conv_id = self.session_id

        tool_calls_executed = []
        request_ids = []
        total_prompt_tokens = 0
        total_completion_tokens = 0
        consecutive_duplicate_calls = 0
        last_tool_signature = None

        iteration = 0
        while iteration < self.max_tool_iterations:
            iteration += 1
            request_id = f"req_{uuid.uuid4().hex[:12]}"
            request_ids.append(request_id)

            self._emit("llm_calling", {
                "iteration": iteration,
                "model": self.model,
                "conversation_id": conv_id,
                "turn_id": turn_id,
                "request_id": request_id,
                "active_skills": self.active_skills,
                "tools_available": [t["function"]["name"] for t in self.tools_schema]
            })

            # Call LLM Gateway with Turn ID and Request ID
            response = await self.gateway.chat_completion(
                messages=self.messages,
                tools=self.tools_schema if self.tools_schema else None,
                model=self.model,
                skill_names=self.active_skills,
                caller_context=caller_context,
                temperature=0.1,
                conversation_id=conv_id,
                turn_id=turn_id,
                request_id=request_id
            )

            # Record tokens
            usage = response.get("usage", {})
            total_prompt_tokens += usage.get("prompt_tokens", 0)
            total_completion_tokens += usage.get("completion_tokens", 0)

            choice = response["choices"][0]
            assistant_msg = choice["message"]
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
                            sanitized_extracted = []
                            for item in extracted:
                                if "function" in item and isinstance(item["function"], dict):
                                    fn_name = item["function"].get("name", "")
                                    fn_args = item["function"].get("arguments", "{}")
                                    if isinstance(fn_args, (dict, list)):
                                        fn_args = json.dumps(fn_args)
                                    sanitized_extracted.append({
                                        "id": item.get("id", f"call_{uuid.uuid4().hex[:6]}"),
                                        "type": "function",
                                        "function": {
                                            "name": fn_name,
                                            "arguments": fn_args
                                        }
                                    })
                                elif "name" in item or "tool" in item:
                                    fn_name = item.get("name") or item.get("tool", "")
                                    fn_args = item.get("arguments") or item.get("args", "{}")
                                    if isinstance(fn_args, (dict, list)):
                                        fn_args = json.dumps(fn_args)
                                    sanitized_extracted.append({
                                        "id": item.get("id", f"call_{uuid.uuid4().hex[:6]}"),
                                        "type": "function",
                                        "function": {
                                            "name": fn_name,
                                            "arguments": fn_args
                                        }
                                    })
                            if sanitized_extracted:
                                tool_calls = sanitized_extracted
                                assistant_msg["tool_calls"] = tool_calls
                    except Exception:
                        pass

            # Ensure any tool_calls in assistant_msg have stringified arguments
            if tool_calls:
                clean_tc_list = []
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        tc_dict = dict(tc)
                        if "function" in tc_dict and isinstance(tc_dict["function"], dict):
                            fn_dict = dict(tc_dict["function"])
                            raw_a = fn_dict.get("arguments", "{}")
                            if isinstance(raw_a, (dict, list)):
                                fn_dict["arguments"] = json.dumps(raw_a)
                            tc_dict["function"] = fn_dict
                        clean_tc_list.append(tc_dict)
                    else:
                        clean_tc_list.append(tc)
                tool_calls = clean_tc_list
                assistant_msg["tool_calls"] = clean_tc_list

            self.messages.append(assistant_msg)

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
                    conversation_id=conv_id,
                    turn_id=turn_id,
                    request_ids=request_ids,
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

                    # Progressive Disclosure: Track dynamically loaded skill in active_skills
                    if tool_name in ("load_skill", "load_skill_instructions"):
                        sk_id = args.get("skill_name") or args.get("skill_id") or ""
                        if sk_id:
                            clean_sk = sk_id if sk_id.endswith("_skill") else f"{sk_id}_skill"
                            if clean_sk not in self.active_skills:
                                self.active_skills.append(clean_sk)
                            self._emit("skill_dynamically_loaded", {
                                "skill_id": clean_sk,
                                "method": "progressive_disclosure"
                            })

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
