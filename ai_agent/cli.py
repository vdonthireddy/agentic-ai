"""Interactive Rich CLI for Agentic AI with MCP Tools & Skills and LLM Gateway."""

import asyncio
import sys
import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.markdown import Markdown

# Ensure local imports work
sys.path.insert(0, str(Path(__file__).parent))

from agent import AgenticLLMAgent
from mcp_client import MCPClientManager
from gateway_client import LLMGatewayClient

console = Console()

def event_callback(event_type: str, data: any):
    if event_type == "mcp_connected":
        table = Table(title="MCP Discovery", border_style="cyan")
        table.add_column("Type", style="bold yellow")
        table.add_column("Discovered Items", style="green")
        table.add_row("Tools", ", ".join(data.get("tools", [])))
        table.add_row("Skills", ", ".join(data.get("skills", [])))
        console.print(table)
    elif event_type == "skill_activated":
        console.print(f"[bold magenta]⚡ Skill Activated:[/bold magenta] [cyan]{data['skill']}[/cyan]")
    elif event_type == "tool_executing":
        console.print(Panel(
            f"[bold yellow]Tool:[/bold yellow] [green]{data['tool']}[/green]\n"
            f"[bold yellow]Arguments:[/bold yellow] {data['args']}",
            title="🛠️ MCP Tool Invocation",
            border_style="yellow"
        ))
    elif event_type == "tool_result":
        console.print(f"[dim green]✓ Tool Output Received: {data['output_preview'][:150]}...[/dim green]")
    elif event_type == "llm_calling":
        console.print(f"[dim blue]🤖 Routing to LLM Gateway ({data['model']}) [Iteration {data['iteration']}]...[/dim blue]")

async def main():
    console.print(Panel.fit(
        "[bold cyan]Agentic AI Assistant[/bold cyan]\n"
        "[dim]Powered by MCP Tools & Skills + LiteLLM Gateway + Ollama[/dim]",
        border_style="cyan"
    ))

    gateway_url = os.environ.get("GATEWAY_URL", "http://localhost:8000")
    model = os.environ.get("DEFAULT_MODEL", "ollama/qwen2.5-coder:7b")

    # Verify Gateway
    gw_client = LLMGatewayClient(base_url=gateway_url)
    try:
        health = await gw_client.check_health()
        console.print(f"[green]✓ Connected to LLM Gateway at {gateway_url} (Ollama Base: {health.get('ollama_api_base')})[/green]")
    except Exception as e:
        console.print(f"[bold red]✗ Cannot reach LLM Gateway at {gateway_url}.[/bold red]")
        console.print(f"[yellow]Please start the gateway in another terminal:[/yellow] [cyan]python llm-gateway/app.py[/cyan]")
        return

    agent = AgenticLLMAgent(
        gateway_url=gateway_url,
        agent_name="CLI-Agent",
        caller_id="terminal_user",
        model=model,
        on_step_callback=event_callback
    )

    try:
        await agent.initialize()
        skills = await agent.mcp.list_skills()
        
        console.print("\n[bold]Available Commands:[/bold]")
        console.print("  [cyan]/skill <name>[/cyan]  - Activate a specialized MCP skill prompt")
        console.print("  [cyan]/skills[/cyan]        - List all available skills")
        console.print("  [cyan]/stats[/cyan]         - View LLM Gateway audit statistics")
        console.print("  [cyan]/logs[/cyan]          - View recent audit logs from gateway")
        console.print("  [cyan]/exit[/cyan]          - Quit interactive session\n")

        while True:
            try:
                user_input = Prompt.ask("\n[bold green]You[/bold green]")
            except (KeyboardInterrupt, EOFError):
                break

            if not user_input.strip():
                continue

            cmd = user_input.strip()
            if cmd == "/exit":
                break
            elif cmd == "/skills":
                table = Table(title="Available MCP Skills", border_style="magenta")
                table.add_column("Skill Name", style="bold cyan")
                table.add_column("Description", style="white")
                for s in skills:
                    table.add_row(s["name"], s["description"])
                console.print(table)
                continue
            elif cmd.startswith("/skill "):
                skill_name = cmd.replace("/skill ", "").strip()
                match = next((s for s in skills if s["name"] == skill_name), None)
                if match:
                    args = {}
                    for a in match.get("arguments", []):
                        val = Prompt.ask(f"  Enter [cyan]{a['name']}[/cyan] ({a.get('description', '')})")
                        args[a["name"]] = val
                    await agent.activate_skill(skill_name, args)
                    console.print(f"[green]Skill '{skill_name}' activated for this session![/green]")
                else:
                    console.print(f"[red]Skill '{skill_name}' not found. Use /skills to see list.[/red]")
                continue
            elif cmd == "/stats":
                stats = await gw_client.get_gateway_stats()
                console.print(Panel(json.dumps(stats, indent=2), title="📊 LLM Gateway Stats", border_style="cyan"))
                continue
            elif cmd == "/logs":
                logs = await gw_client.get_audit_logs(limit=5, session_id=agent.session_id)
                console.print(f"[bold cyan]Audit Logs for Session {agent.session_id} ({len(logs)} calls):[/bold cyan]")
                for l in logs:
                    console.print(f" • [yellow]{l['id']}[/yellow] Model={l['model']} Tokens={l['total_tokens']} Latency={l['latency_ms']}ms Tools={l['tool_names']}")
                continue

            # Run agent query
            console.print("\n[bold cyan]Agent:[/bold cyan]")
            result = await agent.run(user_input, caller_context={"source": "cli_interactive"})
            console.print(Markdown(result.response))
            console.print(f"\n[dim]Tokens: Prompt={result.total_prompt_tokens}, Completion={result.total_completion_tokens} | Tools Executed={len(result.tool_calls_executed)}[/dim]")

    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())
