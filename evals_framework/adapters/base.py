"""Base Agent Adapter Interface for Evals Framework.
Defines standard contracts allowing any AI agent architecture to be benchmarked.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class AgentRunOutput:
    """Standardized output produced by an Agent Adapter."""
    response: str
    tool_calls_executed: List[Dict[str, Any]] = field(default_factory=list)
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    latency_ms: float = 0.0
    session_id: str = ""
    active_skills: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgentAdapter(ABC):
    """
    Abstract Base Class for Agent Adapters.
    Wrap any agent implementation (MCP agent, LangChain, LlamaIndex, custom function, or remote HTTP service).
    """

    def __init__(
        self,
        adapter_id: str,
        name: str,
        description: str = "",
        model: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.adapter_id = adapter_id
        self.name = name
        self.description = description
        self.model = model
        self.config = config or {}

    async def initialize(self) -> None:
        """Optional hook to initialize connections, servers, or discover tools."""
        pass

    async def close(self) -> None:
        """Optional hook to release resources or close sessions."""
        pass

    @abstractmethod
    async def run(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        caller_context: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> AgentRunOutput:
        """
        Execute an agent turn with the given prompt and return standardized AgentRunOutput.
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Serialize adapter metadata."""
        return {
            "id": self.adapter_id,
            "name": self.name,
            "description": self.description,
            "model": self.model,
            "type": self.__class__.__name__,
            "config": self.config
        }
