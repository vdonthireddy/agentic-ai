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
        judge_model: str = "ollama/llama3.2",
        gateway_url: str = "http://localhost:8000",
        dataset_dir: Optional[str] = None
    ):
        self.model = model
        self.judge_model = judge_model
        self.gateway_url = gateway_url
        self.dataset_dir = Path(dataset_dir) if dataset_dir else Path(__file__).parent / "datasets"
        self.reports_dir = Path(__file__).parent / "reports"
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
        tests = []
        for file in sorted(self.dataset_dir.glob("*.json")):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for item in data:
                        if not categories or item.get("category") in categories:
                            tests.append(item)
            except Exception as e:
                console.print(f"[red]Error loading dataset {file}: {e}[/red]")
        return tests

    async def run_suite(self, categories: Optional[List[str]] = None) -> Dict[str, Any]:
        """Runs the benchmark evaluation suite with all 4 graders."""
        run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        timestamp = datetime.now().isoformat()
        test_cases = self.load_test_cases(categories)

        console.print(f"[bold cyan]Running {len(test_cases)} benchmarks | Agent: {self.agent.name} | Model: {self.model} | Judge: {self.judge_model}[/bold cyan]\n")

        results = []
        metrics_list = []

        try:
            await self.agent.initialize()

            for idx, tc in enumerate(test_cases, 1):
                test_id = tc.get("id", f"eval_{idx}")
                test_name = tc.get("name", "Test")
                category = tc.get("category", "general")
                prompt = tc.get("prompt", "")

                console.print(f"[{idx}/{len(test_cases)}] [yellow]Evaluating:[/yellow] [bold]{test_id}[/bold] ({test_name})...")

                # Execute test against the Agent Adapter
                start_time = time.time()
                run_res = await self.agent.run(
                    prompt=prompt,
                    session_id=f"eval_{run_id}_{test_id}",
                    caller_context={"eval_id": test_id, "category": category, "benchmark": True},
                    skill_name=tc.get("skill_name"),
                    skill_args=tc.get("skill_args", {})
                )
                latency_ms = (time.time() - start_time) * 1000

                tokens_dict = {
                    "prompt_tokens": run_res.total_prompt_tokens,
                    "completion_tokens": run_res.total_completion_tokens,
                    "total_tokens": run_res.total_prompt_tokens + run_res.total_completion_tokens
                }

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
                    composite_score >= 0.70 and
                    det_eval["passed"] and
                    eff_eval["passed"] and
                    judge_eval["passed"] and
                    fact_eval["passed"]
                )

                metric_item = {
                    "latency_ms": latency_ms,
                    "prompt_tokens": run_res.total_prompt_tokens,
                    "completion_tokens": run_res.total_completion_tokens,
                    "total_tokens": tokens_dict["total_tokens"]
                }
                metrics_list.append(metric_item)

                res_record = {
                    "id": test_id,
                    "name": test_name,
                    "category": category,
                    "prompt": prompt,
                    "overall_score": composite_score,
                    "passed": overall_passed,
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
                    "executed_tools": [t.get("tool") for t in run_res.tool_calls_executed],
                    "response_snippet": run_res.response[:300]
                }
                results.append(res_record)

                status_color = "green" if overall_passed else "red"
                status_text = "PASS" if overall_passed else "FAIL"
                console.print(f"  [{status_color}]↳ {status_text}[/{status_color}] Score: {int(composite_score*100)}% | Det: {int(det_eval['score']*100)}% | Eff: {int(eff_eval['score']*100)}% | Judge: {int(judge_eval['score']*100)}% | Fact: {int(fact_eval['score']*100)}%\n")

        finally:
            await self.agent.close()

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
        print_evaluation_summary(self.model, results, perf_metrics)

        # Generate & save Markdown report
        report_md_file = generate_markdown_report(self.model, results, perf_metrics)

        # Generate & save structured JSON report
        report_json_file = self.reports_dir / f"eval_run_{run_id}.json"
        run_payload = {
            "run_id": run_id,
            "timestamp": timestamp,
            "agent_id": self.agent.adapter_id,
            "agent_name": self.agent.name,
            "model": self.model,
            "judge_model": self.judge_model,
            "total_tests": len(results),
            "passed_tests": passed_count,
            "pass_rate_pct": pass_rate,
            "average_score_pct": avg_score,
            "avg_latency_ms": perf_metrics.get("avg_latency_ms", 0.0),
            "total_tokens": perf_metrics.get("total_tokens", 0),
            "grader_averages": grader_averages,
            "performance_metrics": perf_metrics,
            "results": results,
            "report_md_path": str(report_md_file)
        }
        report_json_file.write_text(json.dumps(run_payload, indent=2), encoding="utf-8")
        console.print(f"[bold green]JSON Run Artifact saved to:[/bold green] {report_json_file}\n")

        return run_payload


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generic LLM Evaluation Runner")
    parser.add_argument("--agent", type=str, default="mcp_default", help="Agent adapter ID (e.g. mcp_default)")
    parser.add_argument("--model", type=str, default="ollama/gemma2:2b", help="Model name to evaluate")
    parser.add_argument("--judge-model", type=str, default="ollama/llama3.2", help="LLM-as-a-Judge model")
    parser.add_argument("--category", type=str, choices=["tool_calling", "skill_adherence", "reasoning"], default=None)
    args = parser.parse_args()

    cats = [args.category] if args.category else None
    runner = EvalsRunner(agent_adapter=args.agent, model=args.model, judge_model=args.judge_model)
    asyncio.run(runner.run_suite(categories=cats))
