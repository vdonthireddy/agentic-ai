"""Example script demonstrating how to use OpenAI models with LiteLLM and LLM Gateway."""

import os
import sys
import json
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_agent.gateway_client import LLMGatewayClient
from ai_agent.agent import AgenticLLMAgent


async def main():
    gateway_url = os.environ.get("GATEWAY_URL", "http://localhost:8000")
    openai_key = os.environ.get("OPENAI_API_KEY", "mock-or-real-key")
    
    print("=" * 60)
    print("🚀 LiteLLM & OpenAI API Multi-Provider Capability Example")
    print("=" * 60)
    
    # 1. Direct Gateway Client using OpenAI model
    print("\n1. Direct LLM Gateway Completion with OpenAI GPT-4o:")
    client = LLMGatewayClient(base_url=gateway_url, agent_name="OpenAIExampleClient")
    
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant powered by OpenAI via LiteLLM Gateway."},
        {"role": "user", "content": "Explain the advantage of an LLM Gateway in 2 sentences."}
    ]
    
    print(f"Target Model: openai/gpt-4o-mini")
    print(f"Messages: {messages[-1]['content']}")
    
    try:
        # Note: If running without a live OpenAI API key, ensure OPENAI_API_KEY is exported in your environment.
        response = await client.chat_completion(
            messages=messages,
            model="openai/gpt-4o-mini",
            temperature=0.2
        )
        print("\nGateway Response:")
        print(json.dumps(response, indent=2))
    except Exception as e:
        print(f"\n[Note] Request sent to Gateway: {e}")
        print("To execute against live OpenAI endpoints, export OPENAI_API_KEY='your-key-here'.")

    # 2. Running Autonomous Agent with MCP Tools using OpenAI model
    print("\n" + "=" * 60)
    print("2. Running Agentic AI Agent with OpenAI Model & MCP Tools:")
    agent = AgenticLLMAgent(
        gateway_url=gateway_url,
        agent_name="OpenAIAgent",
        model="openai/gpt-4o-mini",
        session_id="openai_demo_session"
    )
    
    try:
        await agent.initialize()
        print(f"Discovered Tools: {[t['function']['name'] for t in agent.tools_schema]}")
        print("Running prompt: 'Calculate the total of $125 with 20% tip using calculator'")
        result = await agent.run("Calculate the total of $125 with 20% tip using calculator")
        print(f"\nAgent Response:\n{result.response}")
    except Exception as e:
        print(f"\n[Note] Agent run: {e}")
        print("Ensure LLM Gateway is running and OPENAI_API_KEY is configured.")


if __name__ == "__main__":
    asyncio.run(main())
