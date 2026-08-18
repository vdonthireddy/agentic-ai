"""Generic Evaluation Runner for benchmarking any Agent Adapter against local/remote LLMs with 4 specialized graders."""

import sys
import os
import json
import time
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from rich.console import Console

# Add search paths
base_dir = Path(__file__).parent.parent
sys.path.insert(0, str(base_dir))
sys.path.insert(0, str(base_dir / "mcp_server"))
sys.path.insert(0, str(Path(__file__).parent))

from evals_framework.adapters import BaseAgentAdapter, MCPAgentAdapter, agent_registry
from evals_framework.registries import model_registry, judge_registry
from evals_framework.graders import (
    grade_deterministic,
    grade_cost_and_efficiency,
    grade_llm_judge,
    grade_fact_checker
)
from evals_framework.evaluators import evaluate_performance
from evals_framework.reporters import print_evaluation_summary, generate_markdown_report

console = Console()


class EvalsRunner:
    """
    Generic Evals Runner:
    Benchmarks any registered Agent Adapter using candidate models and LLM judges across 4 graders.
    """

    def __init__(
        self,
        agent_adapter: Optional[Union[str, BaseAgentAdapter]] = None,
        model: str = "ollama/gemma2:2b",
        judge_model: str = "ollama/gemma2:2b",
        gateway_url: str = "http://localhost:8000",
        dataset_dir: Optional[str] = None,
        reports_dir: Optional[Union[str, Path]] = None
    ):
        self.model = model
        self.judge_model = judge_model
        self.gateway_url = gateway_url
        self.dataset_dir = Path(dataset_dir) if dataset_dir else Path(__file__).parent / "datasets"
        self.reports_dir = Path(reports_dir) if reports_dir else Path(__file__).parent / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Resolve Agent Adapter
        if isinstance(agent_adapter, BaseAgentAdapter):
            self.agent = agent_adapter
        elif isinstance(agent_adapter, str):
            resolved = agent_registry.get(agent_adapter)
            if not resolved:
                # Default to MCP adapter with the given ID
                resolved = MCPAgentAdapter(
                    adapter_id=agent_adapter,
                    model=self.model,
                    gateway_url=self.gateway_url
                )
            self.agent = resolved
        else:
            # Default built-in MCP agent
            self.agent = MCPAgentAdapter(
                adapter_id="mcp_default",
                model=self.model,
                gateway_url=self.gateway_url
            )

        # Sync model onto agent
        self.agent.model = self.model

    def load_test_cases(self, categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Loads benchmark test cases from datasets directory."""
        category_map = {
            "everyday_tools": "tool_calling",
            "tool_calling": "tool_calling",
            "tools": "tool_calling",
            "domain_skills": "skill_adherence",
            "skill_adherence": "skill_adherence",
            "skills": "skill_adherence",
            "reasoning": "reasoning",
            "multi_step_reasoning": "reasoning"
        }
        normalized_cats = {category_map.get(c, c) for c in categories} if categories else None

        tests = []
        for file in sorted(self.dataset_dir.glob("*.json")):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for item in data:
                        cat = item.get("category", "")
                        if not normalized_cats or cat in normalized_cats or category_map.get(cat, cat) in normalized_cats:
                            tests.append(item)
            except Exception as e:
                console.print(f"[red]Error loading dataset {file}: {e}[/red]")
        return tests

    async def run_suite(
        self,
        categories: Optional[List[str]] = None,
        on_event: Optional[Any] = None,
        iterations: int = 1
    ) -> Dict[str, Any]:
        iterations = max(1, int(iterations or 1))
        now = datetime.now().astimezone()
        run_id = f"{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        timestamp = now.isoformat()
        test_cases = self.load_test_cases(categories)

        async def emit(ev: Dict[str, Any]) -> None:
            if on_event:
                try:
                    import inspect
                    if inspect.iscoroutinefunction(on_event):
                        await on_event(ev)
                    else:
                        res = on_event(ev)
                        if inspect.isawaitable(res):
                            await res
                except Exception:
                    pass

        iter_desc = f" ({iterations}x Averaged Runs)" if iterations > 1 else ""
        console.print(f"[bold cyan]Running {len(test_cases)} benchmarks{iter_desc} | Agent: {self.agent.name} | Model: {self.model} | Judge: {self.judge_model}[/bold cyan]\n")

        start_msg = (
            f"🚀 Starting benchmark evaluation ({len(test_cases)} tests × {iterations} runs, averaging results to eliminate 'got lucky' variance) for '{self.model}' with Judge '{self.judge_model}'..."
            if iterations > 1 else
            f"🚀 Starting benchmark evaluation ({len(test_cases)} tests) for '{self.model}' with Judge '{self.judge_model}'..."
        )

        await emit({
            "type": "start",
            "run_id": run_id,
            "total_tests": len(test_cases),
            "iterations": iterations,
            "is_averaged": iterations > 1,
            "model": self.model,
            "judge_model": self.judge_model,
            "agent_id": self.agent.adapter_id,
            "agent_name": self.agent.name,
            "message": start_msg
        })

        test_runs: Dict[str, List[Dict[str, Any]]] = {tc.get("id", f"eval_{i+1}"): [] for i, tc in enumerate(test_cases)}
        metrics_list = []

        total_steps = len(test_cases) * iterations
        current_step = 0

        try:
            await self.agent.initialize()

            for iter_idx in range(1, iterations + 1):
                if iterations > 1:
                    console.print(f"[bold magenta]═══ Benchmark Iteration {iter_idx}/{iterations} ═══[/bold magenta]")

                for idx, tc in enumerate(test_cases, 1):
                    current_step += 1
                    test_id = tc.get("id", f"eval_{idx}")
                    test_name = tc.get("name", "Test")
                    category = tc.get("category", "general")
                    prompt = tc.get("prompt", "")

                    iter_prefix = f"[Run {iter_idx}/{iterations}] " if iterations > 1 else ""
                    console.print(f"[{current_step}/{total_steps}] {iter_prefix}[yellow]Evaluating:[/yellow] [bold]{test_id}[/bold] ({test_name})...")

                    await emit({
                        "type": "test_start",
                        "index": current_step,
                        "total": total_steps,
                        "test_index": idx,
                        "total_tests": len(test_cases),
                        "iteration": iter_idx,
                        "iterations": iterations,
                        "test_id": test_id,
                        "name": test_name,
                        "category": category,
                        "prompt": prompt[:120],
                        "message": f"▶ {iter_prefix}[{idx}/{len(test_cases)}] Running '{test_name}' ({test_id}) [Category: {category}]..."
                    })

                    # Execute test against the Agent Adapter
                    start_time = time.time()
                    run_res = await self.agent.run(
                        prompt=prompt,
                        session_id=f"eval_{run_id}_{test_id}_r{iter_idx}",
                        caller_context={"eval_id": test_id, "category": category, "benchmark": True, "iteration": iter_idx},
                        skill_name=tc.get("skill_name"),
                        skill_args=tc.get("skill_args", {})
                    )
                    latency_ms = (time.time() - start_time) * 1000

                    tokens_dict = {
                        "prompt_tokens": run_res.total_prompt_tokens,
                        "completion_tokens": run_res.total_completion_tokens,
                        "total_tokens": run_res.total_prompt_tokens + run_res.total_completion_tokens
                    }

                    executed_tools = [t.get("tool") for t in run_res.tool_calls_executed]
                    tools_str = f"Tools called: {', '.join(executed_tools)}" if executed_tools else "Direct LLM response (no tools invoked)"

                    await emit({
                        "type": "test_executed",
                        "index": current_step,
                        "total": total_steps,
                        "iteration": iter_idx,
                        "iterations": iterations,
                        "test_id": test_id,
                        "latency_ms": round(latency_ms, 1),
                        "total_tokens": tokens_dict["total_tokens"],
                        "executed_tools": executed_tools,
                        "message": f"  ⚡ {iter_prefix}Agent execution complete in {latency_ms:.0f}ms | {tools_str} | Tokens: {tokens_dict['total_tokens']}"
                    })

                    # ------------------------------------------------------
                    # Run the 4 Specialized Graders
                    # ------------------------------------------------------
                    # 1. Deterministic Grader (Tool Order, Schema, Keywords, Sections)
                    det_eval = grade_deterministic(tc, run_res.tool_calls_executed, run_res.response)

                    # 2. Cost & Efficiency Grader (Token Budget, Latency SLA, Loop Detection)
                    eff_eval = grade_cost_and_efficiency(tc, run_res.tool_calls_executed, tokens_dict, latency_ms)

                    # 3. LLM-as-a-Judge (Safety, Helpfulness, Tone, Persona)
                    judge_eval = await grade_llm_judge(
                        tc,
                        run_res.response,
                        gateway_url=self.gateway_url,
                        judge_model=self.judge_model
                    )

                    # 4. Fact-Checker & Groundedness (Tool output vs Summary Faithfulness)
                    fact_eval = await grade_fact_checker(
                        tc,
                        run_res.tool_calls_executed,
                        run_res.response,
                        gateway_url=self.gateway_url,
                        judge_model=self.judge_model
                    )

                    # Composite score calculation across all 4 graders
                    composite_score = round(
                        (det_eval["score"] * 0.40) +
                        (eff_eval["score"] * 0.20) +
                        (judge_eval["score"] * 0.20) +
                        (fact_eval["score"] * 0.20),
                        2
                    )

                    overall_passed = (
                        composite_score >= 0.65 and
                        det_eval.get("passed", True) and
                        judge_eval.get("passed", True)
                    )

                    metric_item = {
                        "latency_ms": latency_ms,
                        "prompt_tokens": run_res.total_prompt_tokens,
                        "completion_tokens": run_res.total_completion_tokens,
                        "total_tokens": tokens_dict["total_tokens"]
                    }
                    metrics_list.append(metric_item)

                    run_record = {
                        "iteration": iter_idx,
                        "overall_score": composite_score,
                        "composite_score": composite_score,
                        "passed": overall_passed,
                        "overall_passed": overall_passed,
                        "deterministic_score": det_eval["score"],
                        "efficiency_score": eff_eval["score"],
                        "judge_score": judge_eval["score"],
                        "fact_check_score": fact_eval["score"],
                        "deterministic_eval": det_eval,
                        "efficiency_eval": eff_eval,
                        "judge_eval": judge_eval,
                        "fact_check_eval": fact_eval,
                        "latency_ms": round(latency_ms, 1),
                        "total_prompt_tokens": run_res.total_prompt_tokens,
                        "total_completion_tokens": run_res.total_completion_tokens,
                        "total_tokens": tokens_dict["total_tokens"],
                        "executed_tools": executed_tools,
                        "response_snippet": run_res.response[:300]
                    }
                    test_runs[test_id].append(run_record)

                    status_color = "green" if overall_passed else "red"
                    status_text = "PASS" if overall_passed else "FAIL"
                    console.print(f"  [{status_color}]↳ {iter_prefix}{status_text}[/{status_color}] Score: {int(composite_score*100)}% | Det: {int(det_eval['score']*100)}% | Eff: {int(eff_eval['score']*100)}% | Judge: {int(judge_eval['score']*100)}% | Fact: {int(fact_eval['score']*100)}%\n")

                    await emit({
                        "type": "test_graded",
                        "index": current_step,
                        "total": total_steps,
                        "iteration": iter_idx,
                        "iterations": iterations,
                        "test_id": test_id,
                        "name": test_name,
                        "passed": overall_passed,
                        "composite_score": composite_score,
                        "deterministic_score": det_eval["score"],
                        "efficiency_score": eff_eval["score"],
                        "judge_score": judge_eval["score"],
                        "fact_check_score": fact_eval["score"],
                        "message": f"  {'✔' if overall_passed else '✖'} {iter_prefix}Grader Scores: Det: {int(det_eval['score']*100)}% | Eff: {int(eff_eval['score']*100)}% | Judge: {int(judge_eval['score']*100)}% | Fact: {int(fact_eval['score']*100)}% => Composite: {int(composite_score*100)}% ({status_text})"
                    })

        finally:
            await self.agent.close()

        # Compute averaged metrics across all iterations for each test case
        results = []
        for tc in test_cases:
            test_id = tc.get("id", "")
            runs = test_runs.get(test_id, [])
            if not runs:
                continue

            avg_composite = round(sum(r["composite_score"] for r in runs) / len(runs), 2)
            avg_det = round(sum(r["deterministic_score"] for r in runs) / len(runs), 2)
            avg_eff = round(sum(r["efficiency_score"] for r in runs) / len(runs), 2)
            avg_judge = round(sum(r["judge_score"] for r in runs) / len(runs), 2)
            avg_fact = round(sum(r["fact_check_score"] for r in runs) / len(runs), 2)

            passed_runs_count = sum(1 for r in runs if r["passed"])
            test_pass_rate = round((passed_runs_count / len(runs)) * 100, 1)
            overall_passed = (test_pass_rate >= 50.0) and (avg_composite >= 0.65)

            avg_lat = round(sum(r["latency_ms"] for r in runs) / len(runs), 1)
            avg_ptok = int(round(sum(r["total_prompt_tokens"] for r in runs) / len(runs)))
            avg_ctok = int(round(sum(r["total_completion_tokens"] for r in runs) / len(runs)))

            latest_run = runs[-1]
            res_record = {
                "id": test_id,
                "name": tc.get("name", "Test"),
                "category": tc.get("category", "general"),
                "prompt": tc.get("prompt", ""),
                "overall_score": avg_composite,
                "composite_score": avg_composite,
                "passed": overall_passed,
                "overall_passed": overall_passed,
                "pass_rate_pct": test_pass_rate,
                "passed_runs": passed_runs_count,
                "total_runs": len(runs),
                "deterministic_score": avg_det,
                "efficiency_score": avg_eff,
                "judge_score": avg_judge,
                "fact_check_score": avg_fact,
                "deterministic_eval": latest_run["deterministic_eval"],
                "efficiency_eval": latest_run["efficiency_eval"],
                "judge_eval": latest_run["judge_eval"],
                "fact_check_eval": latest_run["fact_check_eval"],
                "latency_ms": avg_lat,
                "total_prompt_tokens": avg_ptok,
                "total_completion_tokens": avg_ctok,
                "executed_tools": latest_run["executed_tools"],
                "response_snippet": latest_run["response_snippet"],
                "iteration_runs": runs
            }
            results.append(res_record)

        # Compute aggregate performance
        perf_metrics = evaluate_performance(metrics_list)
        passed_count = sum(1 for r in results if r["passed"])
        pass_rate = round((passed_count / len(results) * 100), 1) if results else 0
        avg_score = round((sum(r["overall_score"] for r in results) / len(results) * 100), 1) if results else 0

        # Grader averages
        grader_averages = {
            "deterministic": round(sum(r["deterministic_score"] for r in results) / len(results) * 100, 1) if results else 0,
            "efficiency": round(sum(r["efficiency_score"] for r in results) / len(results) * 100, 1) if results else 0,
            "llm_judge": round(sum(r["judge_score"] for r in results) / len(results) * 100, 1) if results else 0,
            "fact_checker": round(sum(r["fact_check_score"] for r in results) / len(results) * 100, 1) if results else 0
        }

        # Print Console Table
        print_evaluation_summary(self.model, results, perf_metrics, iterations=iterations)

        # Generate & save Markdown report
        report_md_file = generate_markdown_report(self.model, results, perf_metrics, iterations=iterations)

        # Generate & save structured JSON report
        report_json_file = self.reports_dir / f"eval_run_{run_id}.json"
        summary_dict = {
            "overall_score": avg_score,
            "pass_rate": pass_rate,
            "total_tests": len(results),
            "passed_tests": passed_count,
            "iterations": iterations,
            "is_averaged": iterations > 1,
            "avg_latency_ms": perf_metrics.get("avg_latency_ms", 0.0),
            "total_tokens": perf_metrics.get("total_tokens", 0)
        }
        run_payload = {
            "run_id": run_id,
            "timestamp": timestamp,
            "iterations": iterations,
            "is_averaged": iterations > 1,
            "agent_id": self.agent.adapter_id,
            "agent_name": self.agent.name,
            "model": self.model,
            "judge_model": self.judge_model,
            "summary": summary_dict,
            "total_tests": len(results),
            "passed_tests": passed_count,
            "pass_rate_pct": pass_rate,
            "pass_rate": pass_rate,
            "overall_score": avg_score,
            "average_score_pct": avg_score,
            "avg_latency_ms": perf_metrics.get("avg_latency_ms", 0.0),
            "total_tokens": perf_metrics.get("total_tokens", 0),
            "grader_averages": grader_averages,
            "performance_metrics": perf_metrics,
            "performance": perf_metrics,
            "results": results,
            "test_results": results,
            "report_md_path": str(report_md_file)
        }
        report_json_file.write_text(json.dumps(run_payload, indent=2), encoding="utf-8")
        console.print(f"[bold green]JSON Run Artifact saved to:[/bold green] {report_json_file}\n")

        avg_note = f" (Averaged over {iterations} runs)" if iterations > 1 else ""
        await emit({
            "type": "complete",
            "run_id": run_id,
            "iterations": iterations,
            "is_averaged": iterations > 1,
            "summary": summary_dict,
            "grader_averages": grader_averages,
            "performance_metrics": perf_metrics,
            "results": results,
            "payload": run_payload,
            "message": f"🏁 Benchmark completed for {self.model}{avg_note}: Pass Rate: {pass_rate}% ({passed_count}/{len(results)}) | Average Composite Score: {avg_score}%"
        })

        return run_payload


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generic LLM Evaluation Runner")
    parser.add_argument("--agent", type=str, default="mcp_default", help="Agent adapter ID (e.g. mcp_default)")
    parser.add_argument("--model", type=str, default="ollama/gemma2:2b", help="Model name to evaluate")
    parser.add_argument("--judge-model", type=str, default="ollama/gemma2:2b", help="LLM-as-a-Judge model")
    parser.add_argument("--category", type=str, choices=["tool_calling", "skill_adherence", "reasoning"], default=None)
    parser.add_argument("--iterations", "-n", type=int, default=1, help="Number of evaluation iterations to run and average (default: 1)")
    args = parser.parse_args()

    cats = [args.category] if args.category else None
    runner = EvalsRunner(agent_adapter=args.agent, model=args.model, judge_model=args.judge_model)
    asyncio.run(runner.run_suite(categories=cats, iterations=args.iterations))
