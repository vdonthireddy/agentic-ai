"""Console reporting for Evaluation results using Rich with 4 specialized graders."""

from datetime import datetime
from typing import Dict, Any, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def print_evaluation_summary(
    model_name: str,
    test_results: List[Dict[str, Any]],
    performance_metrics: Dict[str, Any],
    iterations: int = 1
):
    """
    Renders evaluation scoreboard and individual test results in the terminal with 4 grader scores.
    """
    total_tests = len(test_results)
    passed_tests = sum(1 for t in test_results if t.get("overall_passed") or t.get("passed"))
    avg_score = (sum(t.get("composite_score", t.get("overall_score", 0.0)) for t in test_results) / total_tests) if total_tests > 0 else 0.0

    score_color = "green" if avg_score >= 0.8 else "yellow" if avg_score >= 0.6 else "red"
    server_time = datetime.now().astimezone().strftime("%Y-%m-%d %I:%M:%S %p %Z")
    mode_str = f"\n[bold]Evaluation Mode:[/bold] [magenta]{iterations}x Averaged Runs (Zero-Luck Variance Filter)[/magenta]" if iterations > 1 else ""

    console.print(Panel(
        f"[bold]Generated (Server Time):[/bold] [cyan]{server_time}[/cyan]{mode_str}\n"
        f"[bold]Model Evaluated:[/bold] [cyan]{model_name}[/cyan]\n"
        f"[bold]Total Benchmark Tests:[/bold] {total_tests}\n"
        f"[bold]Tests Passed:[/bold] [green]{passed_tests}/{total_tests}[/green] ({round(passed_tests/total_tests*100, 1) if total_tests else 0}%)\n"
        f"[bold]Average Composite Score:[/bold] [{score_color}]{round(avg_score * 100, 1)}%[/{score_color}]\n"
        f"[bold]Tokens Consumed:[/bold] Total={performance_metrics.get('total_tokens', 0):,} (Prompt: {performance_metrics.get('total_prompt_tokens', 0):,}, Comp: {performance_metrics.get('total_completion_tokens', 0):,})\n"
        f"[bold]Avg Latency:[/bold] {performance_metrics.get('avg_latency_ms', 0):.1f}ms | [bold]P50:[/bold] {performance_metrics.get('p50_latency_ms', 0):.1f}ms | [bold]P95:[/bold] {performance_metrics.get('p95_latency_ms', 0):.1f}ms",
        title=f"🏆 4-Grader LLM Evaluation Scorecard - {model_name}{f' ({iterations}x Average)' if iterations > 1 else ''}",
        border_style="cyan"
    ))

    table = Table(title="4-Grader Test Case Breakdown", border_style="cyan")
    table.add_column("Test ID", style="yellow")
    table.add_column("Category", style="magenta")
    table.add_column("Test Name", style="white")
    table.add_column("Deterministic", style="green")
    table.add_column("Efficiency", style="cyan")
    table.add_column("Judge", style="blue")
    table.add_column("Fact-Check", style="magenta")
    table.add_column("Composite", style="bold")
    table.add_column("Status", style="bold")

    for t in test_results:
        is_passed = bool(t.get("overall_passed") or t.get("passed"))
        status_str = "[bold green]PASS[/bold green]" if is_passed else "[bold red]FAIL[/bold red]"
        det_score = int(t.get("deterministic_score", t.get("tool_score", 1.0)) * 100)
        eff_score = int(t.get("efficiency_score", 1.0) * 100)
        judge_score = int(t.get("judge_score", 1.0) * 100)
        fact_score = int(t.get("fact_check_score", t.get("correctness_score", 1.0)) * 100)
        comp_score = int(t.get("composite_score", t.get("overall_score", 0.0)) * 100)

        table.add_row(
            t["id"],
            t["category"],
            t["name"][:24],
            f"{det_score}%",
            f"{eff_score}%",
            f"{judge_score}%",
            f"{fact_score}%",
            f"{comp_score}%",
            status_str
        )

    console.print(table)
