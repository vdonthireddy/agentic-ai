"""Evaluation runner for benchmarking LLMs against MCP Tools and Skills."""

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

from agent import AgenticLLMAgent
from evaluators import (
    evaluate_tool_accuracy,
    evaluate_skill_adherence,
    evaluate_correctness,
    evaluate_performance
)
from reporters import print_evaluation_summary, generate_markdown_report

console = Console()

class EvalsRunner:
    """Orchestrates test loading, execution against LLM Gateway, scoring, and report generation."""

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
        """Runs the benchmark evaluation suite."""
        test_cases = self.load_test_cases(categories)
        console.print(f"[bold cyan]Running {len(test_cases)} evaluation benchmarks on {self.model}...[/bold cyan]\n")

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

                # 1. Evaluate Tool Calling Accuracy
                tool_eval = evaluate_tool_accuracy(tc, run_res.tool_calls_executed)
                tool_score = tool_eval["score"]

                # 2. Evaluate Skill Adherence
                skill_eval = evaluate_skill_adherence(tc, run_res.response)
                skill_score = skill_eval["score"]

                # 3. Evaluate Correctness
                corr_eval = evaluate_correctness(tc, run_res.response, run_res.tool_calls_executed)
                corr_score = corr_eval["score"]

                # Composite score calculation
                if category == "tool_calling":
                    composite_score = round(0.6 * tool_score + 0.4 * corr_score, 2)
                elif category == "skill_adherence":
                    composite_score = round(0.5 * skill_score + 0.3 * tool_score + 0.2 * corr_score, 2)
                else:
                    composite_score = round(0.4 * tool_score + 0.4 * corr_score + 0.2 * skill_score, 2)

                overall_passed = composite_score >= 0.70

                metric_item = {
                    "latency_ms": latency_ms,
                    "prompt_tokens": run_res.total_prompt_tokens,
                    "completion_tokens": run_res.total_completion_tokens,
                    "total_tokens": run_res.total_prompt_tokens + run_res.total_completion_tokens
                }
                metrics_list.append(metric_item)

                res_record = {
                    "id": test_id,
                    "name": test_name,
                    "category": category,
                    "prompt": prompt,
                    "tool_score": tool_score,
                    "skill_score": skill_score,
                    "correctness_score": corr_score,
                    "composite_score": composite_score,
                    "overall_passed": overall_passed,
                    "tool_eval": tool_eval,
                    "skill_eval": skill_eval,
                    "correctness_eval": corr_eval,
                    "executed_tools": [t.get("tool") for t in run_res.tool_calls_executed],
                    "response_snippet": run_res.response[:300]
                }
                results.append(res_record)

                status_tag = "[green]✓ PASS[/green]" if overall_passed else "[red]✗ FAIL[/red]"
                console.print(f"    ↳ Score: {int(composite_score*100)}% | Latency: {int(latency_ms)}ms | Status: {status_tag}\n")

            perf_summary = evaluate_performance(metrics_list)

            # Output Reports
            print_evaluation_summary(self.model, results, perf_summary)
            report_path = generate_markdown_report(self.model, results, perf_summary)
            console.print(f"\n[green]📄 Detailed Markdown Report saved to:[/green] [cyan]{report_path}[/cyan]\n")

            return {
                "model": self.model,
                "test_results": results,
                "performance": perf_summary,
                "report_file": report_path
            }

        finally:
            await agent.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LLM Evaluation Runner")
    parser.add_argument("--model", type=str, default=os.environ.get("DEFAULT_MODEL", "ollama/qwen2.5-coder:7b"), help="Model to evaluate")
    parser.add_argument("--gateway", type=str, default="http://localhost:8000", help="LLM Gateway URL")
    args = parser.parse_args()

    runner = EvalsRunner(model=args.model, gateway_url=args.gateway)
    asyncio.run(runner.run_suite())
