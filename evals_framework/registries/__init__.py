"""Registries package for Evals Framework."""

from evals_framework.registries.models import ModelSpec, ModelRegistry, model_registry
from evals_framework.registries.judges import JudgeSpec, JudgeRegistry, judge_registry

__all__ = [
    "ModelSpec",
    "ModelRegistry",
    "model_registry",
    "JudgeSpec",
    "JudgeRegistry",
    "judge_registry"
]
