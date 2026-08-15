#!/usr/bin/env python3
"""Standalone script to inspect the LLM Gateway SQLite audit database."""

import sys
import json
import argparse
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add gateway dir to path
gateway_dir = Path(__file__).parent.parent / "llm-gateway"
sys.path.insert(0, str(gateway_dir))

from db import query_logs, get_stats, DB_PATH

console = Console()

def main():
    parser = argparse.ArgumentParser(description="Inspect LLM Gateway Audit Logs")
    parser.add_argument("--limit", type=int, default=20, help="Number of records to show")
    parser.add_argument("--session", type=str, default=None, help="Filter by session ID")
    parser.add_argument("--agent", type=str, default=None, help="Filter by agent name")
    parser.add_argument("--stats-only", action="store_true", help="Only show aggregate statistics")
    parser.add_argument("--detail", type=str, default=None, help="Show full detail for a specific Call ID")
    parser.add_argument("--db", type=str, default=str(DB_PATH), help="Path to sqlite database")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        console.print(f"[bold red]Database file not found at {db_path}[/bold red]")
        return

    if args.detail:
        logs = query_logs(limit=1000, db_path=db_path)
        record = next((l for l in logs if l["id"] == args.detail), None)
        if not record:
            console.print(f"[bold red]Record {args.detail} not found.[/bold red]")
            return
        
        console.print(Panel.fit(f"[bold cyan]Audit Record Details: {record['id']}[/bold cyan]", border_style="cyan"))
        console.print(f"[bold]Timestamp:[/bold] {record['timestamp']}")
        console.print(f"[bold]Caller ID:[/bold] {record['caller_id']} | [bold]Agent:[/bold] {record['agent_name']} | [bold]Session:[/bold] {record['session_id']}")
        console.print(f"[bold]Model:[/bold] {record['model']} | [bold]Status:[/bold] {record['status']} | [bold]Latency:[/bold] {record['latency_ms']}ms")
        console.print(f"[bold]Tokens:[/bold] Prompt={record['prompt_tokens']}, Completion={record['completion_tokens']}, Total={record['total_tokens']}")
        console.print(f"[bold]Caller Context:[/bold] {json.dumps(record.get('caller_context', {}), indent=2)}")
        console.print(f"[bold]Skills:[/bold] {record.get('skill_names', [])}")
        console.print(f"[bold]Tools Discovered:[/bold] {record.get('tool_names', [])}")
        
        console.print("\n[bold yellow]--- Request Messages ---[/bold yellow]")
        for m in record.get("request_messages", []):
            role = m.get("role")
            content = m.get("content", "")
            console.print(f"[[bold blue]{role.upper()}[/bold blue]]: {content if content else m.get('tool_calls')}")
            
        console.print("\n[bold green]--- Assistant Response ---[/bold green]")
        console.print(record.get("response_content") or "[Tool Call Output]")
        if record.get("response_tool_calls"):
            console.print(f"[bold yellow]Tool Calls Made:[/bold yellow] {json.dumps(record['response_tool_calls'], indent=2)}")
        return

    # Show Stats
    stats = get_stats(db_path=db_path)
    console.print(Panel(
        f"[bold]Total LLM Calls:[/bold] {stats['total_calls']} ([green]Success: {stats['successful_calls']}[/green], [red]Errors: {stats['error_calls']}[/red])\n"
        f"[bold]Token Usage:[/bold] Prompt={stats['token_usage']['prompt_tokens']}, Completion={stats['token_usage']['completion_tokens']}, Total={stats['token_usage']['total_tokens']}\n"
        f"[bold]Avg Latency:[/bold] {stats['average_latency_ms']}ms\n"
        f"[bold]Models:[/bold] {stats['models_usage']}\n"
        f"[bold]Tools Used:[/bold] {stats['tools_usage_frequency']}\n"
        f"[bold]Skills Used:[/bold] {stats['skills_usage_frequency']}",
        title="📊 LLM Gateway Audit Summary",
        border_style="cyan"
    ))

    if args.stats_only:
        return

    # Show Table of Recent Calls
    logs = query_logs(
        limit=args.limit,
        session_id=args.session,
        agent_name=args.agent,
        db_path=db_path
    )

    table = Table(title=f"Recent LLM Calls (Showing up to {args.limit})", border_style="cyan")
    table.add_column("Call ID", style="yellow")
    table.add_column("Timestamp", style="dim")
    table.add_column("Agent / Caller", style="blue")
    table.add_column("Model", style="magenta")
    table.add_column("Skills", style="cyan")
    table.add_column("Tools Used", style="green")
    table.add_column("Tokens (P/C/T)", style="white")
    table.add_column("Latency", style="dim")
    table.add_column("Status", style="bold green")

    for l in logs:
        tokens_str = f"{l['prompt_tokens']}/{l['completion_tokens']}/{l['total_tokens']}"
        skills_str = ", ".join(l.get("skill_names", [])) or "-"
        tools_str = ", ".join(l.get("tool_names", [])) or "-"
        caller_str = f"{l['agent_name']}\n({l['caller_id']})"
        status_style = "green" if l["status"] == "SUCCESS" else "red"
        table.add_row(
            l["id"],
            l["timestamp"][11:19],
            caller_str,
            l["model"],
            skills_str,
            tools_str[:25] + ("..." if len(tools_str) > 25 else ""),
            tokens_str,
            f"{l['latency_ms']}ms",
            f"[{status_style}]{l['status']}[/{status_style}]"
        )

    console.print(table)
    console.print("[dim]Tip: Use --detail <call_id> to inspect complete prompts, responses, and parameters.[/dim]")

if __name__ == "__main__":
    main()
