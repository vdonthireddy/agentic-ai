"""Tests for the task planner and multi-agent orchestrator."""

import pytest
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from task_planner import (
    TaskDAG, SubTask, build_decomposition_prompt,
    parse_decomposition_response, infer_skill
)


class TestSubTask:
    def test_to_dict(self):
        task = SubTask(
            task_id="t1",
            description="Research vacation spots",
            skill="research",
            depends_on=[]
        )
        d = task.to_dict()
        assert d["task_id"] == "t1"
        assert d["skill"] == "research"
        assert d["status"] == "pending"

    def test_default_values(self):
        task = SubTask(task_id="t1", description="test")
        assert task.status == "pending"
        assert task.depends_on == []
        assert task.result is None


class TestTaskDAG:
    def test_get_ready_tasks_all_independent(self):
        dag = TaskDAG(
            dag_id="dag1",
            original_prompt="test",
            tasks=[
                SubTask(task_id="t1", description="Task 1"),
                SubTask(task_id="t2", description="Task 2"),
            ]
        )
        ready = dag.get_ready_tasks()
        assert len(ready) == 2

    def test_get_ready_tasks_with_deps(self):
        dag = TaskDAG(
            dag_id="dag1",
            original_prompt="test",
            tasks=[
                SubTask(task_id="t1", description="Task 1"),
                SubTask(task_id="t2", description="Task 2", depends_on=["t1"]),
            ]
        )
        ready = dag.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "t1"

    def test_get_ready_after_completion(self):
        dag = TaskDAG(
            dag_id="dag1",
            original_prompt="test",
            tasks=[
                SubTask(task_id="t1", description="Task 1", status="completed"),
                SubTask(task_id="t2", description="Task 2", depends_on=["t1"]),
            ]
        )
        ready = dag.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "t2"

    def test_is_complete(self):
        dag = TaskDAG(
            dag_id="dag1",
            original_prompt="test",
            tasks=[
                SubTask(task_id="t1", description="T1", status="completed"),
                SubTask(task_id="t2", description="T2", status="completed"),
            ]
        )
        assert dag.is_complete() is True

    def test_is_not_complete(self):
        dag = TaskDAG(
            dag_id="dag1",
            original_prompt="test",
            tasks=[
                SubTask(task_id="t1", description="T1", status="completed"),
                SubTask(task_id="t2", description="T2", status="pending"),
            ]
        )
        assert dag.is_complete() is False

    def test_validate_acyclic_valid(self):
        dag = TaskDAG(
            dag_id="dag1",
            original_prompt="test",
            tasks=[
                SubTask(task_id="t1", description="T1"),
                SubTask(task_id="t2", description="T2", depends_on=["t1"]),
                SubTask(task_id="t3", description="T3", depends_on=["t1", "t2"]),
            ]
        )
        assert dag.validate_acyclic() is True

    def test_validate_acyclic_cycle(self):
        dag = TaskDAG(
            dag_id="dag1",
            original_prompt="test",
            tasks=[
                SubTask(task_id="t1", description="T1", depends_on=["t2"]),
                SubTask(task_id="t2", description="T2", depends_on=["t1"]),
            ]
        )
        assert dag.validate_acyclic() is False

    def test_to_dict(self):
        dag = TaskDAG(
            dag_id="dag1",
            original_prompt="test prompt",
            tasks=[SubTask(task_id="t1", description="T1")]
        )
        d = dag.to_dict()
        assert d["dag_id"] == "dag1"
        assert d["total_tasks"] == 1
        assert d["completed_tasks"] == 0


class TestInferSkill:
    def test_research_skill(self):
        assert infer_skill("Investigate and study the literature on quantum computing") == "research"

    def test_code_skill(self):
        assert infer_skill("Write code for a web scraper") == "code_review"

    def test_travel_skill(self):
        assert infer_skill("Plan a trip to Italy with flights and hotel") == "travel_planner"

    def test_cooking_skill(self):
        assert infer_skill("Create a recipe for pasta dinner") == "chef_meal_planner"

    def test_finance_skill(self):
        assert infer_skill("Help me budget my retirement savings") == "financial_advisor"

    def test_no_match(self):
        assert infer_skill("xyz") == ""


class TestParseDecomposition:
    def test_parse_valid_json(self):
        response = json.dumps([
            {"id": "t1", "description": "Research", "skill": "research", "depends_on": []},
            {"id": "t2", "description": "Synthesize", "skill": "general", "depends_on": ["t1"]}
        ])
        dag = parse_decomposition_response(response, "Test prompt")
        assert len(dag.tasks) == 2
        assert dag.tasks[0].task_id == "t1"
        assert dag.tasks[1].depends_on == ["t1"]

    def test_parse_json_with_code_fences(self):
        response = "```json\n" + json.dumps([
            {"id": "t1", "description": "Task 1", "skill": "research", "depends_on": []}
        ]) + "\n```"
        dag = parse_decomposition_response(response, "Test")
        assert len(dag.tasks) == 1

    def test_parse_invalid_json_fallback(self):
        response = "This is not JSON at all."
        dag = parse_decomposition_response(response, "Original prompt")
        assert len(dag.tasks) == 1
        assert dag.tasks[0].description == "Original prompt"

    def test_parse_with_extra_text(self):
        response = "Here are the tasks:\n" + json.dumps([
            {"id": "t1", "description": "Do something", "depends_on": []}
        ]) + "\nDone!"
        dag = parse_decomposition_response(response, "Test")
        assert len(dag.tasks) >= 1

    def test_parse_cyclic_gets_fixed(self):
        response = json.dumps([
            {"id": "t1", "description": "A", "depends_on": ["t2"]},
            {"id": "t2", "description": "B", "depends_on": ["t1"]}
        ])
        dag = parse_decomposition_response(response, "Test")
        # Should detect cycle and remove dependencies
        assert dag.validate_acyclic() is True

    def test_skill_inference_when_missing(self):
        response = json.dumps([
            {"id": "t1", "description": "Investigate and study the latest research papers", "depends_on": []}
        ])
        dag = parse_decomposition_response(response, "Test")
        assert dag.tasks[0].skill == "research"


class TestDecompositionPrompt:
    def test_prompt_includes_user_request(self):
        prompt = build_decomposition_prompt("Plan a vacation")
        assert "Plan a vacation" in prompt
        assert "sub-tasks" in prompt.lower() or "sub-task" in prompt.lower()
