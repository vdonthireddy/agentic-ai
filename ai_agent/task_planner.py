"""LLM-powered task decomposition for multi-agent orchestration.

Takes a complex user prompt and decomposes it into a Directed Acyclic Graph (DAG)
of sub-tasks that can be distributed across specialized worker agents.
"""

import json
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class SubTask:
    """A single sub-task in the decomposed DAG."""
    task_id: str
    description: str
    skill: str = ""
    depends_on: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[str] = None
    worker_id: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "skill": self.skill,
            "depends_on": self.depends_on,
            "status": self.status,
            "result": self.result,
            "worker_id": self.worker_id,
            "error": self.error
        }


@dataclass
class TaskDAG:
    """A Directed Acyclic Graph of sub-tasks."""
    dag_id: str
    original_prompt: str
    tasks: List[SubTask] = field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dag_id": self.dag_id,
            "original_prompt": self.original_prompt,
            "status": self.status,
            "total_tasks": len(self.tasks),
            "completed_tasks": sum(1 for t in self.tasks if t.status == "completed"),
            "failed_tasks": sum(1 for t in self.tasks if t.status == "failed"),
            "tasks": [t.to_dict() for t in self.tasks]
        }

    def get_ready_tasks(self) -> List[SubTask]:
        """Return tasks whose dependencies are all completed."""
        completed_ids = {t.task_id for t in self.tasks if t.status == "completed"}
        return [
            t for t in self.tasks
            if t.status == "pending" and all(dep in completed_ids for dep in t.depends_on)
        ]

    def is_complete(self) -> bool:
        """Check if all tasks are completed or failed."""
        return all(t.status in ("completed", "failed") for t in self.tasks)

    def validate_acyclic(self) -> bool:
        """Verify the DAG has no cycles using topological sort."""
        in_degree = {t.task_id: 0 for t in self.tasks}
        adj = {t.task_id: [] for t in self.tasks}
        
        for t in self.tasks:
            for dep in t.depends_on:
                if dep in adj:
                    adj[dep].append(t.task_id)
                    in_degree[t.task_id] += 1

        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        visited = 0
        while queue:
            node = queue.pop(0)
            visited += 1
            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return visited == len(self.tasks)


# Available skill mappings for task decomposition
SKILL_KEYWORDS = {
    "research": ["research", "investigate", "study", "analyze literature", "find papers", "survey"],
    "code_review": ["code", "review", "debug", "refactor", "program", "implement", "write code"],
    "data_analysis": ["data", "analyze", "statistics", "chart", "graph", "metrics", "numbers"],
    "travel_planner": ["travel", "trip", "vacation", "flight", "hotel", "itinerary", "destination"],
    "shopping_assistant": ["shop", "buy", "purchase", "gift", "product", "price", "discount"],
    "party_planner": ["party", "event", "celebrate", "gathering", "invite"],
    "chef_meal_planner": ["cook", "recipe", "meal", "dinner", "food", "ingredient"],
    "financial_advisor": ["budget", "invest", "savings", "finance", "money", "retirement", "cost"],
    "customer_support": ["support", "complaint", "issue", "help", "resolve", "ticket"],
}


def infer_skill(description: str) -> str:
    """Infer the best matching skill for a task description."""
    desc_lower = description.lower()
    best_skill = ""
    best_count = 0
    
    for skill, keywords in SKILL_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in desc_lower)
        if count > best_count:
            best_count = count
            best_skill = skill
    
    return best_skill


DECOMPOSITION_PROMPT = """You are a task decomposition engine. Given a complex user request, 
break it down into 2-6 independent sub-tasks that can be executed by specialized AI agents.

Output ONLY a valid JSON array of sub-tasks. Each sub-task has:
- "id": a short unique identifier (e.g., "t1", "t2")
- "description": a clear, actionable description of what this sub-task should accomplish
- "skill": the best matching domain skill (one of: research, code_review, data_analysis, travel_planner, shopping_assistant, party_planner, chef_meal_planner, financial_advisor, customer_support, general)
- "depends_on": array of task IDs this task depends on (empty if independent)

Rules:
1. Each sub-task must be self-contained enough for a single agent to complete.
2. Minimize dependencies — prefer parallel execution.
3. The DAG must be acyclic (no circular dependencies).
4. Include a final "synthesis" task that depends on all other tasks to combine results.

User Request: {prompt}

Output only the JSON array, no markdown, no explanation:"""


def build_decomposition_prompt(user_prompt: str) -> str:
    """Build the LLM prompt for task decomposition."""
    return DECOMPOSITION_PROMPT.format(prompt=user_prompt)


def parse_decomposition_response(response_text: str, original_prompt: str) -> TaskDAG:
    """Parse the LLM's decomposition response into a TaskDAG.
    
    Handles common LLM output quirks (markdown fences, extra text).
    """
    dag_id = f"dag_{uuid.uuid4().hex[:10]}"
    
    # Clean up the response
    text = response_text.strip()
    # Remove markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    
    # Try to extract JSON array
    try:
        tasks_data = json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON array in the text
        import re
        match = re.search(r'\[[\s\S]*\]', text)
        if match:
            try:
                tasks_data = json.loads(match.group())
            except json.JSONDecodeError:
                # Fallback: create a single task
                tasks_data = [
                    {"id": "t1", "description": original_prompt, "skill": "general", "depends_on": []}
                ]
        else:
            tasks_data = [
                {"id": "t1", "description": original_prompt, "skill": "general", "depends_on": []}
            ]

    if not isinstance(tasks_data, list):
        tasks_data = [tasks_data]

    subtasks = []
    for item in tasks_data:
        if not isinstance(item, dict):
            continue
        task_id = item.get("id", f"t{len(subtasks) + 1}")
        desc = item.get("description", "")
        skill = item.get("skill", "")
        if not skill:
            skill = infer_skill(desc)
        depends = item.get("depends_on", [])
        if isinstance(depends, str):
            depends = [depends] if depends else []
        
        subtasks.append(SubTask(
            task_id=task_id,
            description=desc,
            skill=skill,
            depends_on=depends
        ))

    dag = TaskDAG(
        dag_id=dag_id,
        original_prompt=original_prompt,
        tasks=subtasks
    )
    
    # Validate DAG
    if not dag.validate_acyclic():
        # If cyclic, remove all dependencies to make it parallel
        for t in dag.tasks:
            t.depends_on = []

    return dag
