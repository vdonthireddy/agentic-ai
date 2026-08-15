"""Evaluation runner for benchmarking LLMs against MCP Tools and Skills with 4 specialized graders."""

import sys
import os
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from rich.console import Console

# Add search paths
base_dir = Path(__file__).parent.parent
sys.path.insert(0, str(base_dir / "agent-client"))
sys.path.insert(0, str(base_dir / "mcp-server"))
sys.path.insert(0, str(Path(__file__).parent))

from agent import AgenticLLMAgent  # type: ignore[import-not-found,import-untyped]
from graders import (
    grade_deterministic,
    grade_cost_and_efficiency,
    grade_llm_judge,
    grade_fact_checker
)
from evaluators import (
    evaluate_tool_accuracy,
    evaluate_skill_adherence,
    evaluate_correctness,
    evaluate_performance
)
from reporters import print_evaluation_summary, generate_markdown_report

console = Console()

class EvalsRunner:
    """Orchestrates test loading, execution against LLM Gateway, 4-grader evaluation, and report generation."""

    def __init__(
        self,
        model: str = "ollama/qwen2.5-coder:7b",
        gateway_url: str = "http://localhost:8000",
        dataset_dir: Optional[str] = None
    ):
        self.model = model
        self.gateway_url = gateway_url
        self.dataset_dir = Path(dataset_dir) if dataset_dir else Path(__file__).parent / "datasets"

    def load_test_cases(self, categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Loads benchmark test cases from datasets directory."""
        tests = []
        for file in self.dataset_dir.glob("*.json"):
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
        test_cases = self.load_test_cases(categories)
        console.print(f"[bold cyan]Running {len(test_cases)} evaluation benchmarks on {self.model} with 4 specialized graders...[/bold cyan]\n")

        agent = AgenticLLMAgent(
            gateway_url=self.gateway_url,
            agent_name="EvalsFramework",
            caller_id="evals_runner",
            model=self.model
        )

        results = []
        metrics_list = []

        try:
            await agent.initialize()

            for idx, tc in enumerate(test_cases, 1):
                test_id = tc.get("id", f"eval_{idx}")
                test_name = tc.get("name", "Test")
                category = tc.get("category", "general")
                prompt = tc.get("prompt", "")

                console.print(f"[{idx}/{len(test_cases)}] [yellow]Evaluating:[/yellow] [bold]{test_id}[/bold] ({test_name})...")
                
                # Reset skills and conversation state to clean baseline
                agent.reset_skills()

                # Activate skill if specified for this test case
                if tc.get("skill_name"):
                    await agent.activate_skill(tc["skill_name"], tc.get("skill_args", {}))

                start_time = time.time()
                run_res = await agent.run(
                    user_input=prompt,
                    caller_context={"eval_id": test_id, "category": category, "benchmark": True}
                )
                latency_ms = (time.time() - start_time) * 1000

                tokens_dict = {
                    "prompt_tokens": run_res.total_prompt_tokens,
                    "completion_tokens": run_res.total_completion_tokens,
                    "total_tokens": run_res.total_prompt_tokens + run_res.total_completion_tokens
                }

                # ------------------------------------------------------
                # Run the 4 Graders
                # ------------------------------------------------------
                # 1. Deterministic Grader (Tool Order, Schema, Keywords, Sections)
                det_eval = grade_deterministic(tc, run_res.tool_calls_executed, run_res.response)
                
                # 2. Cost & Efficiency Grader (Token Budget, Latency SLA, Loops)
                eff_eval = grade_cost_and_efficiency(tc, run_res.tool_calls_executed, tokens_dict, latency_ms)
                
                # 3. LLM-as-a-Judge (Safety, Helpfulness, Tone)
                judge_eval = await grade_llm_judge(tc, run_res.response, gateway_url=self.gateway_url, judge_model=self.model)
                
                # 4. Fact-Checker & Groundedness (Tool vs Summary Faithfulness)
                fact_eval = await grade_fact_checker(tc, run_res.tool_calls_executed, run_res.response, gateway_url=self.gateway_url, judge_model=self.model)

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
                    "deterministic_score": det_eval["score"],
                    "efficiency_score": eff_eval["score"],
                    "judge_score": judge_eval["score"],
                    "fact_check_score": fact_eval["score"],
                    "composite_score": composite_score,
                    "overall_passed": overall_passed,
                    "deterministic_eval": det_eval,
                    "efficiency_eval": eff_eval,
                    "judge_eval": judge_eval,
                    "fact_check_eval": fact_eval,
                    "executed_tools": [t.get("tool") for t in run_res.tool_calls_executed],
                    "response_snippet": run_res.response[:300]
                }
                results.append(res_record)

                status_color = "green" if overall_passed else "red"
                status_text = "PASS" if overall_passed else "FAIL"
                console.print(f"  [{status_color}]↳ {status_text}[/{status_color}] Composite Score: {int(composite_score*100)}% | Det: {int(det_eval['score']*100)}% | Eff: {int(eff_eval['score']*100)}% | Judge: {int(judge_eval['score']*100)}% | Fact: {int(fact_eval['score']*100)}%\n")

        finally:
            await agent.close()

        # Compute aggregate performance
        perf_metrics = evaluate_performance(metrics_list)
        passed_count = sum(1 for r in results if r["overall_passed"])
        pass_rate = round((passed_count / len(results) * 100), 1) if results else 0
        avg_score = round((sum(r["composite_score"] for r in results) / len(results) * 100), 1) if results else 0

        # Print Console Table
        print_evaluation_summary(self.model, results, perf_metrics)

        # Generate & save Markdown report
        report_file = generate_markdown_report(self.model, results, perf_metrics)
        console.print(f"[bold green]Report saved to:[/bold green] {report_file}\n")

        return {
            "model": self.model,
            "total_tests": len(results),
            "passed_tests": passed_count,
            "pass_rate": pass_rate,
            "average_score": avg_score,
            "test_results": results,
            "performance_metrics": perf_metrics,
            "report_path": str(report_file)
        }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LLM Evaluation Runner")
    parser.add_argument("--model", type=str, default="ollama/qwen2.5-coder:7b", help="Model name to evaluate")
    parser.add_argument("--category", type=str, choices=["tool_calling", "skill_adherence", "reasoning"], default=None)
    args = parser.parse_args()

    cats = [args.category] if args.category else None
    runner = EvalsRunner(model=args.model)
    asyncio.run(runner.run_suite(categories=cats))
