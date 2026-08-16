"""Pydantic schemas for LLM Gateway API and requests."""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: Optional[Union[str, List[Dict[str, Any]]]] = None
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: List[ChatMessage]
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    temperature: Optional[float] = 0.2
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    
    # Custom provider / API endpoint overrides per request
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    provider: Optional[str] = None

    # Custom caller context and hierarchical metadata
    caller_id: Optional[str] = None
    agent_name: Optional[str] = None
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None
    turn_id: Optional[str] = None
    request_id: Optional[str] = None
    caller_context: Optional[Dict[str, Any]] = None
    skill_names: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class LogQueryFilter(BaseModel):
    limit: int = 50
    offset: int = 0
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None
    turn_id: Optional[str] = None
    request_id: Optional[str] = None
    agent_name: Optional[str] = None
    model: Optional[str] = None


class LLMCallRecord(BaseModel):
    id: str
    request_id: str
    turn_id: Optional[str] = None
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: str
    caller_id: Optional[str] = None
    agent_name: Optional[str] = None
    caller_context: Optional[Dict[str, Any]] = None
    model: str
    skill_names: Optional[List[str]] = None
    tool_names: Optional[List[str]] = None
    request_messages: Optional[List[Dict[str, Any]]] = None
    request_tools: Optional[List[Dict[str, Any]]] = None
    request_params: Optional[Dict[str, Any]] = None
    response_content: Optional[str] = None
    response_tool_calls: Optional[List[Dict[str, Any]]] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    status: str = "SUCCESS"
    error_message: Optional[str] = None


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    owned_by: str = "ollama"
    provider: str = "ollama"
    description: Optional[str] = ""
    supports_tools: bool = True
