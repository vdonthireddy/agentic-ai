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
            # Local Ollama Models
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
            ),
            # Cloud Models
            ModelSpec(
                model_id="openai/gpt-4o",
                name="OpenAI GPT-4o",
                provider="openai",
                description="Flagship multimodal agent and tool-use model"
            ),
            ModelSpec(
                model_id="openai/gpt-4o-mini",
                name="OpenAI GPT-4o Mini",
                provider="openai",
                description="Fast, lightweight cost-efficient benchmark model"
            ),
            ModelSpec(
                model_id="anthropic/claude-3-5-sonnet-20241022",
                name="Claude 3.5 Sonnet",
                provider="anthropic",
                description="Anthropic state-of-the-art coding and agentic model"
            ),
            ModelSpec(
                model_id="gemini/gemini-2.0-flash",
                name="Gemini 2.0 Flash",
                provider="gemini",
                description="Google Gemini next-generation fast multimodal model"
            ),
            ModelSpec(
                model_id="groq/llama-3.3-70b-versatile",
                name="Groq LLaMA 3.3 70B",
                provider="groq",
                description="Ultra-fast LPU-accelerated open-weights cloud model"
            ),
            ModelSpec(
                model_id="deepseek/deepseek-chat",
                name="DeepSeek V3",
                provider="deepseek",
                description="DeepSeek V3 official cloud model"
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
