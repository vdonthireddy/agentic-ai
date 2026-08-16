"""Model Registry for registering and selecting candidate models for Evals."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ModelSpec(BaseModel):
    """Specification of a candidate model for benchmark evaluations."""
    model_id: str
    name: str
    provider: str = "ollama"
    api_base: Optional[str] = None
    description: str = ""
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    is_default: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModelRegistry:
    """Registry to register, manage, and retrieve candidate models."""

    def __init__(self) -> None:
        self._models: Dict[str, ModelSpec] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        defaults = [
            ModelSpec(
                model_id="ollama/qwen2.5-coder:7b",
                name="Qwen 2.5 Coder 7B",
                provider="ollama",
                description="High-performance code & tool calling reasoning model",
                is_default=True
            ),
            ModelSpec(
                model_id="ollama/llama3.2",
                name="LLaMA 3.2 3B",
                provider="ollama",
                description="Fast, lightweight conversational agent model"
            ),
            ModelSpec(
                model_id="ollama/gemma2:2b",
                name="Gemma 2 2B",
                provider="ollama",
                description="Compact lightweight Google Gemma 2B model"
            ),
            ModelSpec(
                model_id="ollama/mistral:latest",
                name="Mistral 7B",
                provider="ollama",
                description="General-purpose instruction tuned model"
            )
        ]
        for m in defaults:
            self.register(m)

    def register(self, model: ModelSpec) -> None:
        """Register a new candidate model."""
        self._models[model.model_id] = model

    def unregister(self, model_id: str) -> Optional[ModelSpec]:
        """Unregister a model."""
        return self._models.pop(model_id, None)

    def get(self, model_id: str) -> Optional[ModelSpec]:
        """Retrieve model specification by ID."""
        return self._models.get(model_id)

    def list_all(self) -> List[Dict[str, Any]]:
        """List all registered candidate models."""
        return [m.model_dump() for m in self._models.values()]


# Global model registry instance
model_registry = ModelRegistry()
