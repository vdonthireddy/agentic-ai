# 🛠️ 03. MCP Tools & Sandbox — Step-by-Step UI Guide

> **Author**: Vijay Donthireddy  
> **Repository**: [vdonthireddy/agentic-ai](https://github.com/vdonthireddy/agentic-ai)  
> **Route**: `http://localhost:8000/tools`  
> **Component Source**: [`webui/src/views/ToolsView.jsx`](file:///Users/donthireddy/code/github/agentic-ai/webui/src/views/ToolsView.jsx)  
> **Backend Engine**: [`llm_gateway/app.py`](file:///Users/donthireddy/code/github/agentic-ai/llm_gateway/app.py) (`/api/tools/execute`) & [`mcp_server/tools/`](file:///Users/donthireddy/code/github/agentic-ai/mcp_server/tools/)  
> **Documentation Track**: [Phase 2: Single-Agent Mechanics & Tool Power](./README.md#phase-2-single-agent-mechanics--tool-power)  
> **Navigation**: [🏠 Docs Hub](./README.md) | [⬅️ Prev: 15. Context Compaction](./15_context_compaction_engine.md) | **Step 4 of 18** | [➡️ Next: 04. Domain Skills Hub](./04_domain_skills_hub.md)

---

> 🔗 **Related Deep-Dive Modules**:
> - ✨ [04. Domain Skills Hub](./04_domain_skills_hub.md) — Connect everyday tools to high-level persona guidance.
> - 📁 [05. Workspace Files Explorer](./05_workspace_files.md) — Inspect files read and written by `workspace_file_ops`.
> - 🛡️ [17. Security Firewall & Defense](./17_security_firewall_prompt_defense.md) — Learn how AST scanning and path traversal protections block malicious inputs.
> - 💬 [01. AI Agent Chatbot](./01_ai_agent_chatbot.md) — See how the ReAct loop dynamically invokes these MCP tools.

---

## 🌟 1. What It Does (Plain English & Analogy)

The **MCP Tools & Sandbox** is an interactive developer workbench, diagnostic test harness, and secure execution environment for all registered Model Context Protocol (MCP) tools. It allows engineers to inspect standardized tool JSON schemas, execute isolated test payloads without spending LLM tokens, and benchmark real-time tool latencies.

### 🧪 What is a "Sandbox"?
A **Sandbox** is an isolated, controlled testing environment where software components or code can be safely executed without affecting the rest of the application or the host operating system. In this platform, sandboxing exists at two distinct levels:

1. **The MCP Tool Diagnostic Sandbox (`/tools`)**: A zero-token testing playground where you can feed raw JSON arguments directly into any tool (e.g., `get_weather`, `calculate`, `workspace_file_ops`, `product_knowledge`) to verify its return values, validate schemas, and measure latency before handing it to an autonomous AI agent.
2. **The Python Code Interpreter Sandbox (`python_sandbox`)**: A security-restricted runtime environment that dynamically executes generated Python scripts, captures standard output, generates interactive Plotly visualizations, and blocks dangerous system calls (like `os.system` or `shutil.rmtree`).

> 💡 **The Real-World Analogy**:  
> - **The Flight Simulator**: An airline pilot doesn't test a new engine maneuver with 300 passengers in mid-air. They test it first in a flight simulator (the sandbox) where mistakes cost nothing.  
> - **The Chemistry Fume Hood**: A chemist mixes volatile compounds inside a reinforced glass fume hood with its own ventilation. If something explodes, the lab is completely protected.

---

## 🎯 2. Why & How It Helps (Value Proposition)

### "The Challenge Before" vs. "How This Solves It"

| The Challenge Before | How This Solves It |
|---|---|
| **Blind Tool Debugging**: Discovering that a tool has a bad parameter schema only when an LLM fails and crashes a live 10-turn conversation. | **Interactive JSON Sandbox**: Live parameter editor with pre-filled sample payloads, schema validation, and instant test execution. |
| **Token Waste on Tool Testing**: Forcing an LLM to call tools just to test if the Python code works, burning API credits and adding latency. | **Zero-Token Direct Execution**: Directly invokes the Python backend handler via `POST /api/tools/execute` without calling any AI model. |
| **Security Risks from Code Execution**: Allowing AI agents to execute arbitrary Python code can lead to server compromise or data deletion. | **AST Security Scanning & Memory Sandboxing**: The Python sandbox inspects code AST, blocks dangerous syscalls, and runs inside a memory-bounded context. |
| **Unpredictable Tool Latencies**: Slow third-party APIs dragging down agent responsiveness without visibility. | **Sub-Millisecond Benchmarking**: Displays exact round-trip execution latency (`latency_ms`) for every single tool invocation. |

---

## 🏗️ 3. How the Sandbox is Created & How It Works Under the Hood

```mermaid
flowchart TD
    Dev["👨‍💻 Developer / Test Harness\n(Selects tool & inputs JSON arguments)"] --> API["⚡ Gateway Endpoint\nPOST /api/tools/execute"]
    
    subgraph Sandbox["🛡️ Secure MCP Sandbox Environment"]
        API --> Val["1. Schema & Type Validation\n(Verifies against Anthropic MCP schema)"]
        Val --> Sec["2. Security & Path Traversal Filter\n(Blocks os.system, ../, destructive ops)"]
        Sec --> Runner["3. Isolated Function Execution\n(Captures stdout, binds timeout timer)"]
    end

    Runner --> Metrics["4. Latency & Telemetry Tracker\n(Records latency_ms and status)"]
    Metrics --> Resp["5. Structured JSON Output\n(Returns payload + latency badge to UI)"]

    classDef cIndigo fill:#1e1b4b,stroke:#6366f1,stroke-width:2px,color:#fff;
    classDef cCyan fill:#082f49,stroke:#0ea5e9,stroke-width:2px,color:#fff;
    classDef cAmber fill:#78350f,stroke:#f59e0b,stroke-width:2px,color:#fff;
    classDef cEmerald fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#fff;
    classDef cFuchsia fill:#701a75,stroke:#d946ef,stroke-width:2px,color:#fff;

    class Dev cIndigo;
    class Sandbox cCyan;
    class Metrics cAmber;
    class Resp cEmerald;
```

---

## 🚀 4. Real-World Step-by-Step Scenarios

### Scenario A: Testing the Weather Tool with Zero LLM Tokens
1. Navigate to **`http://localhost:8000/tools`**.
2. Select **`get_weather`** from the left tool sidebar.
3. Observe the generated Anthropic MCP schema in the Schema tab.
4. In the JSON Arguments editor, enter:
   ```json
   {
     "city": "Tokyo"
   }
   ```
5. Click **`[⚡ Execute Tool Sandbox]`**.
6. The right panel instantly displays the JSON result (`{"temp_c": 22, "condition": "Clear"}`) and a green execution badge: `2.4ms • 200 OK`.

### Scenario B: Testing the Python Sandbox with a Dynamic Plotly Chart
1. Select **`python_sandbox`** from the tool list.
2. In the arguments box, input a script generating a sales chart:
   ```json
   {
     "code": "import plotly.graph_objects as go\nfig = go.Figure(data=[go.Bar(x=['Q1', 'Q2', 'Q3', 'Q4'], y=[120, 180, 240, 310])])\nfig.show()\nprint('Chart generated successfully!')"
   }
   ```
3. Click **`[⚡ Execute Tool Sandbox]`**.
4. The sandbox safely captures standard output and returns the Plotly JSON specification without executing any unsafe operating system commands.

---

## 😄 5. Witty & Relatable Commentary

> *"Never let an AI agent use a tool you haven't tested yourself in the sandbox first. It's like giving your teenage cousin the keys to a twin-turbo sports car without checking if the brakes work! Test it in the sandbox for 1 millisecond, verify the schema, and sleep soundly knowing your agent won't hallucinate."*

---

## 💻 6. Under-the-Hood Code & API Endpoints

- **List Tools Endpoint**: `GET /api/tools` (Returns full Anthropic MCP schemas)
- **Execute Sandbox Endpoint**: `POST /api/tools/execute`
- **Tool Catalog Directory**: [`mcp_server/tools/`](file:///Users/donthireddy/code/github/agentic-ai/mcp_server/tools/)
- **Python Sandbox Engine**: [`mcp_server/tools/python_tool.py`](file:///Users/donthireddy/code/github/agentic-ai/mcp_server/tools/python_tool.py)
- **UI Component**: [`webui/src/views/ToolsView.jsx`](file:///Users/donthireddy/code/github/agentic-ai/webui/src/views/ToolsView.jsx)

---

## 🧭 Next Step in Your Journey

Now that you know how tools execute in isolation, learn how to wrap tools into specialized agent personas and system prompt skills:

👉 **[Continue to 04. Domain Skills Hub Guide](./04_domain_skills_hub.md)**
