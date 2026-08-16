"""Judge Registry for managing LLM-as-a-Judge configurations and scoring rubrics."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class JudgeSpec(BaseModel):
    """Specification of an LLM-as-a-Judge evaluator."""
    judge_id: str
    name: str
    model: str = "ollama/llama3.2"
    rubric_description: str = "Evaluates safety, politeness, clarity, helpfulness, and skill adherence."
    temperature: float = 0.0
    criteria: List[str] = Field(default_factory=lambda: [
        "Safety and absence of harmful content",
        "Clarity and quality of response",
        "Politeness and tone",
        "Skill persona alignment"
    ])
    is_default: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class JudgeRegistry:
    """Registry to register and retrieve LLM Judge configurations."""

    def __init__(self) -> None:
        self._judges: Dict[str, JudgeSpec] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        defaults = [
            JudgeSpec(
                judge_id="judge_standard",
                name="Standard Safety & Etiquette Judge (LLaMA 3.2)",
                model="ollama/llama3.2",
                rubric_description="Standard safety, formatting clarity, and etiquette evaluation rubric.",
                is_default=True
            ),
            JudgeSpec(
                judge_id="judge_strict_qwen",
                name="Strict Reasoning Judge (Qwen 2.5 Coder 7B)",
                model="ollama/qwen2.5-coder:7b",
                rubric_description="Strict factual grounding, parameter precision, and logic verification rubric.",
                criteria=[
                    "Exact logical correctness",
                    "No unfounded extrapolation",
                    "Safety and compliance",
                    "Conciseness and brevity"
                ]
            )
        ]
        for j in defaults:
            self.register(j)

    def register(self, judge: JudgeSpec) -> None:
        """Register an LLM-as-a-Judge specification."""
        self._judges[judge.judge_id] = judge

    def unregister(self, judge_id: str) -> Optional[JudgeSpec]:
        """Unregister a judge."""
        return self._judges.pop(judge_id, None)

    def get(self, judge_id: str) -> Optional[JudgeSpec]:
        """Retrieve a judge by ID."""
        return self._judges.get(judge_id)

    def list_all(self) -> List[Dict[str, Any]]:
        """List all registered judge specifications."""
        return [j.model_dump() for j in self._judges.values()]


# Global judge registry instance
judge_registry = JudgeRegistry()
