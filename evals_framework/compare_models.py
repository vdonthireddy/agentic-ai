"""Comparative evaluation script for benchmarking multiple local LLM models."""

import sys
import asyncio
from pathlib import Path
from typing import List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add search path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

try:
    from evals_framework import EvalsRunner
except (ImportError, ValueError):
    from runner import EvalsRunner  # type: ignore[import-not-found]

console = Console()

async def compare_models(models: List[str], gateway_url: str = "http://localhost:8000"):
    console.print(Panel.fit(
        "[bold cyan]Head-to-Head LLM Model Comparative Benchmark[/bold cyan]\n"
        f"[dim]Comparing Models: {', '.join(models)}[/dim]",
        border_style="cyan"
    ))

    all_results = {}

    for model in models:
        console.print(f"\n[bold yellow]═════════════════ Running Evals for: {model} ═════════════════[/bold yellow]")
        runner = EvalsRunner(model=model, gateway_url=gateway_url)
        summary = await runner.run_suite()
        all_results[model] = summary

    # Render Comparative Table
    table = Table(title="Model Comparative Scorecard", border_style="cyan")
    table.add_column("Model Name", style="bold cyan")
    table.add_column("Pass Rate", style="green")
    table.add_column("Avg Composite Score", style="yellow")
    table.add_column("Avg Latency", style="magenta")
    table.add_column("Total Tokens", style="blue")
    table.add_column("Throughput (tok/s)", style="white")

    for model, data in all_results.items():
        results = data.get("results") or data.get("test_results", [])
        perf = data.get("performance_metrics") or data.get("performance", {})
        total = data.get("total_tests", len(results))
        passed = data.get("passed_tests", sum(1 for r in results if r.get("overall_passed") or r.get("passed")))
        pass_rate = f"{data.get('pass_rate_pct', round(passed/total*100, 1) if total else 0)}% ({passed}/{total})"
        avg_score = f"{data.get('average_score_pct', round((sum(r.get('composite_score', r.get('overall_score', 0.0)) for r in results)/total)*100, 1) if total else 0)}%"
        
        table.add_row(
            model,
            pass_rate,
            avg_score,
            f"{perf.get('avg_latency_ms', 0):.1f}ms",
            f"{perf.get('total_tokens', 0):,}",
            f"{perf.get('tokens_per_second', 0):.1f}"
        )

    console.print("\n")
    console.print(table)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Compare multiple models")
    parser.add_argument("--models", nargs="+", default=["ollama/gemma2:2b", "ollama/qwen2.5-coder:7b"], help="List of models to compare")
    parser.add_argument("--gateway", type=str, default="http://localhost:8000", help="Gateway URL")
    args = parser.parse_args()

    asyncio.run(compare_models(args.models, args.gateway))
