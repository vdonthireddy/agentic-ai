# 🔱 02. Workflow Canvas (DAG Studio) — Step-by-Step UI Guide

> **Author**: Vijay Donthireddy  
> **Route**: `http://localhost:8000/canvas`  
> **Component Source**: [`webui/src/views/CanvasView.jsx`](file:///Users/donthireddy/code/github/agentic-ai/webui/src/views/CanvasView.jsx)  
> **Backend Engine**: [`llm_gateway/app.py`](file:///Users/donthireddy/code/github/agentic-ai/llm_gateway/app.py) (`/api/canvas/execute`)

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

    class S1 cIndigo;
    class A2,T3 cEmerald;
    class H4 cAmber;
    class T1 cCyan;
    class S4 cFuchsia;
```

---

### 📋 Complete Step-by-Step UI Guide

#### Part 1: Design & Configure Your Pipeline on the Canvas
1. **Open the Canvas**: Navigate to **Workflow Canvas (DAG)** (`http://localhost:8000/canvas`).
2. **Add Nodes from the Palette**:
   - Click or drag **Agent Node** (set Role to `supervisor`).
   - Click or drag **MCP Tool Node** (select `calculate` or `search_web`).
   - Click or drag **HITL Gate Node** (select Approval Policy: `🔒 Always Require Approval` or `💰 Amount > $100`).
   - Click or drag **Agent Node** for the final output (set Role to `arbitrator`).
3. **Connect Wires**:
   - Drag from the **Pink Output Port** (right side) of the Supervisor to the **Cyan Input Ports** (left side) of your Stage 2 workers and the HITL gate.
   - Connect the HITL gate output wire to your downstream tool or synthesizer.
4. **Name Your Pipeline**:
   - In the top action bar, type a custom name in the **`📝 Name:`** field (e.g. `Vijay Pipeline`).
5. **Test on Canvas**:
   - Click **`[▶ Run Workflow DAG]`** to run a visual simulation. The nodes illuminate sequentially through each stage.
6. **Save Your Pipeline**:
   - Click **`[💾 Save Pipeline]`**. A green banner will confirm: `Pipeline Saved: "Vijay Pipeline"`.

---

#### Part 2: Execute Your Pipeline with Live User Prompts in the Chatbot
1. **Open the AI Agent Chatbot**: Click **AI Agent Chatbot** in the left navigation sidebar (`http://localhost:8000/chat`).
2. **Select Your Saved Pipeline**:
   - Look at the top control bar and click the **`🔱 Workflow DAG`** dropdown.
   - Select your saved pipeline: **`⚡ Vijay Pipeline`**.
   - The indicator badge at the bottom will display: `🔱 Active Workflow DAG: Vijay Pipeline [X Disable DAG]`.
3. **Enter Your Live Prompt**:
   - Type your task in the chat input box:
     ```text
     plan a weekend trip and divide the budget among three people.
     ```
   - Click **Send (Enter)**.

---

#### Part 3: Interactive Human-in-the-Loop (HITL) Sign-Off

When execution reaches the **HITL Approval Gate**, the backend pauses and displays the glowing modal in your browser:

* **If you click `[✅ Approve Action]`**:
  1. The clearance token `[AUTH_200_OK]` is granted.
  2. The pipeline immediately executes all downstream stages (Stage 3 and Stage 4).
  3. The final synthesized vacation breakdown is rendered in the chat with a **4 STAGES • 6 NODES EXECUTED** badge.

* **If you click `[❌ Deny Action]`**:
  1. Execution **halts immediately** at Stage 2.
  2. Downstream stages (Stage 3 and Stage 4) are **strictly blocked from execution**.
  3. The Chatbot displays the security compliance banner:
     > ⛔ **Workflow Execution Aborted**: Human-in-the-Loop approval was **DENIED** by human operator for node `5. HITL Approval Gate`. Downstream pipeline stages were blocked from execution to maintain system safety and compliance.

---

## 😄 4. Witty & Relatable Commentary

> *"Why make one AI agent do all the homework alone when you can spawn three agent workers in parallel, make them do the research at the same time, have a human sign off on the budget, and let a synthesizer agent take all the credit? That's what we call modern enterprise efficiency!"*

---

## 💻 5. Under-the-Hood Code & API Endpoints

- **DAG Execute Endpoint**: `POST /api/canvas/execute` (Kahn's Topological Sort with stage grouping and HITL circuit breaker)
- **DAG Pipelines CRUD**: `GET /api/canvas/pipelines`, `POST /api/canvas/pipelines`, `DELETE /api/canvas/pipelines/{id}`
- **HITL Verification**: [`mcp_server/hitl.py`](file:///Users/donthireddy/code/github/agentic-ai/mcp_server/hitl.py)
- **Frontend Studio**: [`webui/src/views/CanvasView.jsx`](file:///Users/donthireddy/code/github/agentic-ai/webui/src/views/CanvasView.jsx) and [`webui/src/views/ChatView.jsx`](file:///Users/donthireddy/code/github/agentic-ai/webui/src/views/ChatView.jsx)
