"""Evals Framework for Agentic AI Benchmarking."""

from evals_framework.adapters import (
    BaseAgentAdapter,
    AgentRunOutput,
    MCPAgentAdapter,
    HTTPAgentAdapter,
    CallableAgentAdapter,
    AgentRegistry,
    agent_registry
)
from evals_framework.registries import (
    ModelSpec,
    ModelRegistry,
    model_registry,
    JudgeSpec,
    JudgeRegistry,
    judge_registry
)
from evals_framework.history import HistoryEngine, history_engine
from evals_framework.runner import EvalsRunner
from evals_framework.router import router

__all__ = [
    "BaseAgentAdapter",
    "AgentRunOutput",
    "MCPAgentAdapter",
    "HTTPAgentAdapter",
    "CallableAgentAdapter",
    "AgentRegistry",
    "agent_registry",
    "ModelSpec",
    "ModelRegistry",
    "model_registry",
    "JudgeSpec",
    "JudgeRegistry",
    "judge_registry",
    "HistoryEngine",
    "history_engine",
    "EvalsRunner",
    "router"
]
