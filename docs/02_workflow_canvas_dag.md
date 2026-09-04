# 🔱 02. Workflow Canvas (DAG Studio) — Step-by-Step UI Guide

> **Author**: Vijay Donthireddy  
> **Repository**: [vdonthireddy/agentic-ai](https://github.com/vdonthireddy/agentic-ai)  
> **Route**: `http://localhost:8000/canvas`  
> **Component Source**: [`webui/src/views/CanvasView.jsx`](file:///Users/donthireddy/code/github/agentic-ai/webui/src/views/CanvasView.jsx)  
> **Backend Engine**: [`ai_agent/router.py`](file:///Users/donthireddy/code/github/agentic-ai/ai_agent/router.py) (mounted via [`llm_gateway/app.py`](file:///Users/donthireddy/code/github/agentic-ai/llm_gateway/app.py) at `/api/canvas/execute`)  
> **Documentation Track**: [Phase 3: Visual Workflows & Multi-Agent Swarms](./README.md#phase-3-visual-workflows--multi-agent-swarms)  
> **Navigation**: [🏠 Docs Hub](./README.md) | [⬅️ Prev: 10. Memory Explorer](./10_memory_explorer.md) | **Step 8 of 18** | [➡️ Next: 13. Parallel Swarms & DAGs](./13_parallel_agent_execution_swarms.md)

---

> 🔗 **Related Deep-Dive Modules**:
> - 🐝 [13. Parallel Swarms & DAG Execution](./13_parallel_agent_execution_swarms.md) — Technical details of Kahn's topological sort and concurrency bounds.
> - 🤖 [09. Multi-Agent Orchestrator](./09_multi_agent_orchestrator.md) — Automatic supervisor decomposition without manual canvas wiring.
> - 🛡️ [14. Human-in-the-Loop (HITL) Safety](./14_human_in_the_loop_safety.md) — Deep dive into safety interception nodes and policies.
> - 💬 [01. AI Agent Chatbot](./01_ai_agent_chatbot.md) — Execute saved visual pipelines with conversational prompts.

---

## 🌟 1. What It Does (Plain English & Analogy)

The **Workflow Canvas (DAG Studio)** is an interactive 2D node-based visual orchestration builder. It allows you to build multi-agent graphs with **Forks (Fan-Out)** and **Joins (Fan-In)**, connecting Agent Reasoning nodes, MCP Tool nodes, Human-in-the-Loop (HITL) safety gates, and Semantic Memory stores.

> 💡 **The Real-World Analogy**:  
> Think of standard chat like a single worker assembling a car one bolt at a time. The **DAG Studio** is like an automated Tesla gigafactory assembly line: a supervisor decomposes the job, three specialized robotic arms work in parallel at the same time (Stage 2 swarm), a quality safety inspector checks the work (Stage 3 HITL), and an executive arbitrator signs off on the final car (Stage 4 Join).

---

## 🎯 2. Why & How It Helps (Value Proposition)

### "The Challenge Before" vs. "How This Solves It"

| The Challenge Before | How This Solves It |
|---|---|
| **Sequential Bottlenecks**: Running 3 independent tasks (search web, calculate taxes, lookup customer) sequentially takes 3x longer. | **Concurrent Stage Swarms**: Kahn's topological sort groups independent nodes into parallel execution waves (`asyncio.gather`), slashing latency by up to 70%. |
| **Uncontrolled AI Actions**: Agents executing high-stakes tools or large budget actions with zero human supervision. | **Wired HITL Safety Gates**: Halts execution at the exact gate stage and opens an interactive approval modal before any downstream actions occur. |
| **Accidental Infinite Loops**: A circular connection between agents (`A -> B -> A`) crashes agent frameworks. | **DFS Cycle Prevention**: Real-time visual validation and cycle rejection before execution. |
| **Isolated Experiments**: Graph experiments stay trapped in the editor without real user prompts. | **One-Click Save & Chatbot Integration**: Save any graph as a named pipeline and select it directly in the AI Chatbot dropdown to run live prompts. |

---

## 🚀 3. Real-World Step-by-Step Scenario

### Scenario: Building a 4-Stage Swarm with Calculation & HITL Safety Approval

```mermaid
flowchart TD
    S1["Stage 1: Supervisor Agent\n(Task Decomposer)"]
    
    subgraph Stage2["Stage 2: Concurrent Parallel Swarm"]
        S1 --> A2["Stage 2A: Analyst Agent\n(Worker 2)"]
        S1 --> T3["Stage 2B: MCP Tool: calculate\n(Worker 3)"]
        S1 --> H4["Stage 2C: 🛡️ HITL Approval Gate\n(Policy: Always Require Approval)"]
    end
    
    subgraph Stage3["Stage 3: Verified Web Research"]
        H4 -.->|If Approved [AUTH_200_OK]| T1["Stage 3A: MCP Tool: search_web\n(Worker 1)"]
    end
    
    subgraph Stage4["Stage 4: Final Synthesis"]
        A2 --> S4["Stage 4: Agent Reasoning Node\n(Consensus Synthesizer)"]
        T3 --> S4
        T1 --> S4
    end

    classDef cIndigo fill:#1e1b4b,stroke:#6366f1,stroke-width:2px,color:#fff;
    classDef cEmerald fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#fff;
    classDef cAmber fill:#78350f,stroke:#f59e0b,stroke-width:2px,color:#fff;
    classDef cCyan fill:#082f49,stroke:#0ea5e9,stroke-width:2px,color:#fff;
    classDef cFuchsia fill:#701a75,stroke:#d946ef,stroke-width:2px,color:#fff;
```

### Step-by-Step UI Actions:

#### Part 1: Build and Save Your Pipeline
1. In the **Workflow Canvas**, click **`[⚡ Presets]`** and choose **`1-to-3 Parallel Swarm Fork`** (or drag nodes onto the canvas).
2. Wire an **Agent Reasoning Node** (`Stage 1`) to three parallel nodes:
   - **Analyst Agent Node**
   - **Calculate Tool Node**
   - **HITL Approval Gate Node**
3. Wire the outputs to a **Final Synthesizer Node** (`Stage 4`).
4. Click **`[💾 Save Pipeline]`** and name it: `⚡ Vijay Pipeline`.

#### Part 2: Execute Your Pipeline with Live User Prompts in the Chatbot
1. Open **AI Agent Chatbot** (`http://localhost:8000/chat`).
2. In the top control bar, select `⚡ Vijay Pipeline` from the **`🔱 Workflow DAG`** dropdown.
3. Type: *"Plan a weekend trip and divide the budget among three people."*
4. Click **Send (Enter)**.

#### Part 3: Interactive Human-in-the-Loop (HITL) Sign-Off
1. When execution reaches the **HITL Approval Gate**, the backend pauses and displays the modal in your browser.
2. If you click **`[✅ Approve Action]`**, the clearance token `[AUTH_200_OK]` is granted and downstream stages execute immediately.
3. If you click **`[❌ Deny Action]`**, execution halts safely and downstream stages are blocked.

---

## 😄 4. Witty & Relatable Commentary

> *"Why make one AI agent do all the homework alone when you can spawn three agent workers in parallel, make them do the research at the same time, have a human sign off on the budget, and let a synthesizer agent take all the credit? That's what we call modern enterprise efficiency!"*

---

## 💻 5. Under-the-Hood Code & API Endpoints

- **DAG Execute Endpoint**: `POST /api/canvas/execute` (Kahn's Topological Sort with stage grouping and HITL circuit breaker)
- **DAG Pipelines CRUD**: `GET /api/canvas/pipelines`, `POST /api/canvas/pipelines`, `DELETE /api/canvas/pipelines/{id}`
- **HITL Verification**: [`mcp_server/hitl.py`](file:///Users/donthireddy/code/github/agentic-ai/mcp_server/hitl.py)
- **Frontend Studio**: [`webui/src/views/CanvasView.jsx`](file:///Users/donthireddy/code/github/agentic-ai/webui/src/views/CanvasView.jsx) and [`webui/src/views/ChatView.jsx`](file:///Users/donthireddy/code/github/agentic-ai/webui/src/views/ChatView.jsx)

---

## 🧭 Next Step in Your Journey

To dive deep into the concurrent execution mechanics, async worker pool, and topological grouping behind the DAG Studio:

👉 **[Continue to 13. Parallel Swarms & DAG Execution Guide](./13_parallel_agent_execution_swarms.md)**
