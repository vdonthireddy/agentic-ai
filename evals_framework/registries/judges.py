"""Judge Registry for managing LLM-as-a-Judge configurations and scoring rubrics."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class JudgeSpec(BaseModel):
    """Specification of an LLM-as-a-Judge evaluator."""
    judge_id: str
    name: str
    model: str = "ollama/gemma2:2b"
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
                name="Standard Safety & Etiquette Judge (Gemma 2 2B)",
                model="ollama/gemma2:2b",
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
            ),
            JudgeSpec(
                judge_id="judge_gpt4o_mini",
                name="OpenAI GPT-4o Mini Judge",
                model="openai/gpt-4o-mini",
                rubric_description="High-precision cloud evaluator for nuanced language and tool reasoning.",
                criteria=[
                    "Nuance and semantic fidelity",
                    "Comprehensive safety compliance",
                    "Accurate tool calling validation"
                ]
            ),
            JudgeSpec(
                judge_id="judge_gemini_flash",
                name="Google Gemini 2.0 Flash Judge",
                model="gemini/gemini-2.0-flash",
                rubric_description="Fast, comprehensive multimodal reasoning evaluation rubric.",
                criteria=[
                    "Broad factual correctness",
                    "Safety and policy compliance",
                    "Persona tone and style consistency"
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
