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
    
    # Custom caller context and metadata passed directly in request body
    caller_id: Optional[str] = None
    agent_name: Optional[str] = None
    session_id: Optional[str] = None
    caller_context: Optional[Dict[str, Any]] = None
    skill_names: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class LogQueryFilter(BaseModel):
    limit: int = 50
    offset: int = 0
    session_id: Optional[str] = None
    agent_name: Optional[str] = None
    model: Optional[str] = None
