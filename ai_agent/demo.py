"""Automated End-to-End Demonstration and Verification of Real-World Everyday Agent."""

import asyncio
import json
import os
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Ensure imports work
sys.path.insert(0, str(Path(__file__).parent))

from agent import AgenticLLMAgent
from gateway_client import LLMGatewayClient

console = Console()

def event_logger(event_type: str, data: any):
    if event_type == "tool_executing":
        console.print(f"  [bold yellow]↳ Invoking Tool:[/bold yellow] [green]{data['tool']}[/green] with args: {data['args']}")
    elif event_type == "tool_result":
        console.print(f"  [dim green]↳ Tool Result:[/dim green] {str(data['output_preview'])[:120]}...")
    elif event_type == "skill_activated":
        console.print(f"  [bold magenta]⚡ Skill Injected:[/bold magenta] [cyan]{data['skill']}[/cyan]")
    elif event_type == "llm_calling":
        console.print(f"  [dim blue]🤖 Routing to Gateway (Iteration {data['iteration']})...[/dim blue]")

async def run_demo():
    console.print(Panel.fit(
        "[bold cyan]🌟 Real-World AI Agent: Everyday Tools & Fun Domain Skills[/bold cyan]\n"
        "[dim]Demonstrating Calculator, Live Weather, Web Search, Shopping Catalog, and Vacation Planning[/dim]",
        border_style="cyan"
    ))

    gateway_url = os.environ.get("GATEWAY_URL", "http://localhost:8000")
    model = os.environ.get("DEFAULT_MODEL", "ollama/gemma2:2b")

    gw_client = LLMGatewayClient(base_url=gateway_url)
    
    # 1. Gateway Health Check
    console.print("\n[bold]1. Connecting to LiteLLM Gateway & Local Ollama...[/bold]")
    try:
        health = await gw_client.check_health()
        models = await gw_client.list_models()
        console.print(f"[green]✓ Gateway is online at {gateway_url}[/green]")
        console.print(f"[green]✓ Available Models: {[m['id'] for m in models]}[/green]")
    except Exception as e:
        console.print(f"[bold red]✗ Failed to connect to LLM Gateway: {e}[/bold red]")
        console.print("[yellow]Ensure gateway is running with: python llm-gateway/app.py[/yellow]")
        return

    # Create Agent instance
    session_id = f"everyday_sess_{os.getpid()}"
    agent = AgenticLLMAgent(
        gateway_url=gateway_url,
        agent_name="EverydayAssistant",
        caller_id="everyday_user",
        model=model,
        session_id=session_id,
        on_step_callback=event_logger
    )

    try:
        # 2. MCP Discovery
        console.print("\n[bold]2. Initializing Everyday Tools & Skills via MCP...[/bold]")
        await agent.initialize()
        tools = [t["function"]["name"] for t in agent.tools_schema]
        skills = await agent.mcp.list_skills()
        console.print(f"[green]✓ Tools Discovered: {tools}[/green]")
        console.print(f"[green]✓ Skills Discovered: {[s['name'] for s in skills]}[/green]")

        # Scenario A: Restaurant Bill Splitter
        console.print("\n[bold cyan]=== Scenario A: 🍕 Dinner Bill & Tip Calculator ===[/bold cyan]")
        query_a = "Our dinner bill for 4 people is $184.50. Calculate an 18% tip and the total split per person using the calculator tool."
        console.print(f"[bold]User Prompt:[/bold] {query_a}")
        result_a = await agent.run(query_a, caller_context={"scenario": "dinner_bill_calculator"})
        console.print(Panel(result_a.response, title="Agent Response", border_style="green"))

        # Scenario B: Vacation Itinerary & Weather Lookup
        agent.clear_history()
        console.print("\n[bold cyan]=== Scenario B: 🏖️ Vacation Planning & Live Weather Lookup ===[/bold cyan]")
        await agent.activate_skill("travel_planner_skill", {
            "destination": "Paris, France",
            "duration_days": "3",
            "travel_vibe": "quaint bakeries, art museums, sunset walks along the Seine"
        })
        query_b = "Check the live weather in Paris using the weather tool and give me a 3-day vacation itinerary with bakery recommendations and packing tips."
        console.print(f"[bold]User Prompt:[/bold] {query_b}")
        result_b = await agent.run(query_b, caller_context={"scenario": "paris_vacation_planner"})
        console.print(Panel(result_b.response, title="Agent Response (Vacation Concierge)", border_style="magenta"))

        # Scenario C: Personal Shopping Assistant
        agent.clear_history()
        console.print("\n[bold cyan]=== Scenario C: 🛍️ Personal Shopping & Discount Finder ===[/bold cyan]")
        await agent.activate_skill("shopping_assistant_skill", {
            "shopper_goal": "Find a top-rated espresso maker on sale",
            "recipient": "my morning routine",
            "budget_usd": "Under $250"
        })
        query_c = "Find the smart espresso machine in the shopping catalog using product_knowledge, calculate the discounted price with the calculator, and summarize customer reviews."
        console.print(f"[bold]User Prompt:[/bold] {query_c}")
        result_c = await agent.run(query_c, caller_context={"scenario": "shopping_deal_finder"})
        console.print(Panel(result_c.response, title="Agent Response (Personal Shopper)", border_style="cyan"))

        # Scenario D: Workspace Vacation Notes
        agent.clear_history()
        console.print("\n[bold cyan]=== Scenario D: 📝 Saving Packing List to Workspace File ===[/bold cyan]")
        query_d = "Save a checklist titled 'Paris Trip Checklist: Passport, CloudBeats Headphones, Sherpa Hoodie, Walking Shoes' to 'paris_trip_checklist.txt' using workspace_file_ops."
        console.print(f"[bold]User Prompt:[/bold] {query_d}")
        result_d = await agent.run(query_d, caller_context={"scenario": "save_packing_list"})
        console.print(Panel(result_d.response, title="Agent Response", border_style="yellow"))

        # Audit Verification
        console.print("\n[bold]3. Verifying Persisted Gateway Audit Trail...[/bold]")
        logs_response = await gw_client.get_audit_logs(session_id=session_id)
        logs = logs_response if isinstance(logs_response, list) else logs_response.get("logs", logs_response)

        table = Table(title=f"Audit Trail for Everyday Session: {session_id}", border_style="blue")
        table.add_column("Call ID", style="cyan")
        table.add_column("Agent", style="white")
        table.add_column("Skills", style="magenta")
        table.add_column("Tools Dispatched", style="yellow")
        table.add_column("Tokens (P/C/Tot)", style="green")
        table.add_column("Latency (ms)", style="dim")
        table.add_column("Status", style="bold green")

        for log in logs:
            table.add_row(
                log["id"],
                log["agent_name"],
                ", ".join(log.get("skill_names") or []) or "-",
                ", ".join(log.get("tool_names") or []) or "-",
                f"{log['prompt_tokens']}/{log['completion_tokens']}/{log['total_tokens']}",
                f"{log['latency_ms']:.1f}",
                log["status"]
            )
        console.print(table)
        console.print(f"\n[bold green]✓ Real-World Demo Completed Successfully! Total Session Tokens: {sum(l['total_tokens'] for l in logs)}[/bold green]")
        console.print(f"[dim]Inspect live dashboard at: http://localhost:8000/[/dim]\n")

    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(run_demo())
