"""Multi-Agent Orchestrator for coordinating Supervisor and Worker agents.

Decomposes complex prompts into task DAGs, spawns specialized worker agents
for parallel sub-task execution, and synthesizes final consolidated responses.
"""

import json
import uuid
import time
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field

try:
    from .agent import AgenticLLMAgent, AgentRunResult
    from .task_planner import (
        TaskDAG, SubTask, build_decomposition_prompt,
        parse_decomposition_response
    )
except (ImportError, ValueError):
    from agent import AgenticLLMAgent, AgentRunResult  # type: ignore[import-not-found]
    from task_planner import (  # type: ignore[import-not-found]
        TaskDAG, SubTask, build_decomposition_prompt,
        parse_decomposition_response
    )


@dataclass
class OrchestratorRunResult:
    """Result from a multi-agent orchestration run."""
    run_id: str
    original_prompt: str
    dag: TaskDAG
    synthesized_response: str
    worker_results: List[Dict[str, Any]]
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    elapsed_seconds: float = 0.0
    status: str = "completed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "original_prompt": self.original_prompt,
            "dag": self.dag.to_dict(),
            "synthesized_response": self.synthesized_response,
            "worker_results": self.worker_results,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "status": self.status
        }


class SupervisorAgent:
    """Orchestrates multi-agent task execution.
    
    1. Decomposes a user prompt into a DAG of sub-tasks using the LLM.
    2. Spawns WorkerAgent instances for each sub-task.
    3. Manages parallel execution respecting DAG dependencies.
    4. Synthesizes worker outputs into a final consolidated response.
    """

    def __init__(
        self,
        gateway_url: str = "http://localhost:8000",
        model: str = "ollama/gemma2:2b",
        max_workers: int = 4,
        on_event_callback: Optional[Callable] = None
    ):
        self.gateway_url = gateway_url
        self.model = model
        self.max_workers = max_workers
        self.on_event = on_event_callback
        self._runs: Dict[str, OrchestratorRunResult] = {}
        try:
            from .gateway_client import LLMGatewayClient
        except (ImportError, ValueError):
            from gateway_client import LLMGatewayClient  # type: ignore[import-not-found]
        self.gateway = LLMGatewayClient(base_url=self.gateway_url, agent_name="SupervisorAgent")

    def _emit(self, event_type: str, data: Any):
        if self.on_event:
            try:
                if asyncio.iscoroutinefunction(self.on_event):
                    asyncio.create_task(self.on_event({"type": event_type, **data}))
                else:
                    self.on_event({"type": event_type, **data})
            except Exception:
                pass

    async def decompose(self, prompt: str) -> TaskDAG:
        """Use the LLM to decompose a complex prompt into a task DAG."""
        try:
            decomp_prompt = build_decomposition_prompt(prompt)
            resp = await self.gateway.chat_completion(
                messages=[
                    {"role": "system", "content": "You are an expert task planner. Decompose complex user requests into a structured JSON array of subtasks."},
                    {"role": "user", "content": decomp_prompt}
                ],
                tools=None,
                model=self.model,
                temperature=0.1
            )
            raw_text = resp["choices"][0]["message"]["content"]
            dag = parse_decomposition_response(raw_text, prompt)
            
            self._emit("dag_created", {
                "dag_id": dag.dag_id,
                "total_tasks": len(dag.tasks),
                "tasks": [t.to_dict() for t in dag.tasks]
            })
            
            return dag
        except Exception:
            # Fallback to single task DAG
            from task_planner import TaskDAG, SubTask
            single_task = SubTask(task_id="t1", description=prompt, skill="general")
            dag = TaskDAG(original_prompt=prompt, tasks=[single_task])
            self._emit("dag_created", {
                "dag_id": dag.dag_id,
                "total_tasks": 1,
                "tasks": [single_task.to_dict()]
            })
            return dag

    async def _execute_worker(
        self,
        task: SubTask,
        dag: TaskDAG,
        semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        """Execute a single sub-task with a dedicated worker agent."""
        async with semaphore:
            task.status = "running"
            worker_id = f"worker_{uuid.uuid4().hex[:6]}"
            task.worker_id = worker_id
            
            self._emit("worker_start", {
                "task_id": task.task_id,
                "worker_id": worker_id,
                "description": task.description,
                "skill": task.skill
            })

            worker = AgenticLLMAgent(
                gateway_url=self.gateway_url,
                agent_name=f"Worker-{task.skill or 'general'}",
                model=self.model,
                max_tool_iterations=4
            )

            try:
                await worker.initialize()

                # Activate the relevant skill if specified
                if task.skill and task.skill != "general":
                    skill_name = f"{task.skill}_skill"
                    try:
                        await worker.activate_skill(skill_name)
                    except Exception:
                        pass  # Skill may not exist; continue without it

                # Include dependency results in the prompt
                dep_context = ""
                for dep_id in task.depends_on:
                    dep_task = next((t for t in dag.tasks if t.task_id == dep_id), None)
                    if dep_task and dep_task.result:
                        dep_context += f"\n[Result from '{dep_id}': {dep_task.description}]\n{dep_task.result}\n"

                full_prompt = task.description
                if dep_context:
                    full_prompt = f"Context from prior tasks:{dep_context}\n\nYour task: {task.description}"

                result = await worker.run(full_prompt)
                
                task.status = "completed"
                task.result = result.response

                self._emit("worker_complete", {
                    "task_id": task.task_id,
                    "worker_id": worker_id,
                    "status": "completed",
                    "response_preview": result.response[:200] if result.response else ""
                })

                return {
                    "task_id": task.task_id,
                    "worker_id": worker_id,
                    "skill": task.skill,
                    "description": task.description,
                    "status": "completed",
                    "response": result.response,
                    "tool_calls": result.tool_calls_executed,
                    "prompt_tokens": result.total_prompt_tokens,
                    "completion_tokens": result.total_completion_tokens
                }

            except Exception as e:
                task.status = "failed"
                task.error = str(e)

                self._emit("worker_failed", {
                    "task_id": task.task_id,
                    "worker_id": worker_id,
                    "error": str(e)
                })

                return {
                    "task_id": task.task_id,
                    "worker_id": worker_id,
                    "skill": task.skill,
                    "description": task.description,
                    "status": "failed",
                    "error": str(e),
                    "prompt_tokens": 0,
                    "completion_tokens": 0
                }
            finally:
                await worker.close()

    async def _execute_dag(self, dag: TaskDAG) -> List[Dict[str, Any]]:
        """Execute all tasks in the DAG respecting dependencies."""
        semaphore = asyncio.Semaphore(self.max_workers)
        all_results = []
        dag.status = "running"

        while not dag.is_complete():
            ready = dag.get_ready_tasks()
            if not ready:
                # No tasks ready — check for deadlock
                pending = [t for t in dag.tasks if t.status == "pending"]
                if pending:
                    # Force-unblock by removing unsatisfied dependencies
                    for t in pending:
                        t.depends_on = [
                            d for d in t.depends_on
                            if any(dt.task_id == d and dt.status == "completed"
                                   for dt in dag.tasks)
                        ]
                    ready = dag.get_ready_tasks()
                    if not ready:
                        break

            # Execute ready tasks in parallel
            coros = [self._execute_worker(t, dag, semaphore) for t in ready]
            batch_results = await asyncio.gather(*coros, return_exceptions=True)
            
            for r in batch_results:
                if isinstance(r, Exception):
                    all_results.append({"status": "failed", "error": str(r)})
                else:
                    all_results.append(r)

        dag.status = "completed" if all(t.status == "completed" for t in dag.tasks) else "partial"
        return all_results

    async def _synthesize(self, dag: TaskDAG, worker_results: List[Dict[str, Any]]) -> str:
        """Synthesize worker results into a final consolidated response."""
        results_text = ""
        for wr in worker_results:
            if wr.get("status") == "completed" and wr.get("response"):
                results_text += f"\n--- [{wr['task_id']}] {wr['description']} ---\n{wr['response']}\n"

        if not results_text.strip():
            for t in dag.tasks:
                if t.result:
                    results_text += f"\n--- [{t.task_id}] {t.description} ---\n{t.result}\n"

        if not results_text.strip():
            return "No task results were produced."

        synth_prompt = (
            f"You are a synthesis agent. The user's original request was:\n\n"
            f"\"{dag.original_prompt}\"\n\n"
            f"Multiple specialized agents have completed sub-tasks. Here are their results:\n"
            f"{results_text}\n\n"
            f"Please synthesize all these results into a single, coherent, well-structured response "
            f"that fully addresses the user's original request. Maintain all specific data, numbers, "
            f"and recommendations from the individual results. Do NOT attempt to call tools. Output only your clear markdown response."
        )

        try:
            resp = await self.gateway.chat_completion(
                messages=[
                    {"role": "system", "content": "You are an expert synthesis agent. Consolidate and summarize the sub-task outputs into a comprehensive final answer. Do NOT invoke any tools."},
                    {"role": "user", "content": synth_prompt}
                ],
                tools=None,
                model=self.model,
                temperature=0.2
            )
            content = resp["choices"][0]["message"]["content"]
            if not content or "Unknown tool" in content or "synthesize_response" in content:
                return f"### Consolidated Results\n\n{results_text.strip()}"
            return content
        except Exception:
            return f"### Consolidated Results\n\n{results_text.strip()}"

    async def run(self, prompt: str) -> OrchestratorRunResult:
        """Execute a full multi-agent orchestration run.
        
        1. Decompose the prompt into a task DAG
        2. Execute workers in parallel (respecting dependencies)
        3. Synthesize results into a final response
        """
        run_id = f"orch_{uuid.uuid4().hex[:10]}"
        start_time = time.time()

        self._emit("orchestration_start", {
            "run_id": run_id,
            "prompt": prompt
        })

        # Step 1: Decompose
        dag = await self.decompose(prompt)

        # Step 2: Execute DAG
        worker_results = await self._execute_dag(dag)

        # Step 3: Synthesize
        self._emit("synthesis_start", {"run_id": run_id})
        synthesized = await self._synthesize(dag, worker_results)

        elapsed = time.time() - start_time
        total_pt = sum(wr.get("prompt_tokens", 0) for wr in worker_results)
        total_ct = sum(wr.get("completion_tokens", 0) for wr in worker_results)

        result = OrchestratorRunResult(
            run_id=run_id,
            original_prompt=prompt,
            dag=dag,
            synthesized_response=synthesized,
            worker_results=worker_results,
            total_prompt_tokens=total_pt,
            total_completion_tokens=total_ct,
            elapsed_seconds=elapsed,
            status=dag.status
        )

        self._runs[run_id] = result
        
        self._emit("orchestration_complete", {
            "run_id": run_id,
            "status": dag.status,
            "total_tasks": len(dag.tasks),
            "elapsed_seconds": round(elapsed, 2)
        })

        return result

    def get_run(self, run_id: str) -> Optional[OrchestratorRunResult]:
        """Retrieve a completed orchestration run by ID."""
        return self._runs.get(run_id)

    def list_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recent orchestration runs."""
        runs = sorted(
            self._runs.values(),
            key=lambda r: r.elapsed_seconds,
            reverse=True
        )[:limit]
        return [r.to_dict() for r in runs]
