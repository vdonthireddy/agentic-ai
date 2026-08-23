# ⚡ 13. Parallel Agent Execution & Concurrent Swarms

> **Author**: Vijay Donthireddy  
> **Route**: `http://localhost:8000/canvas` and `http://localhost:8000/chat`  
> **Component Sources**: [`llm_gateway/app.py`](file:///Users/donthireddy/code/github/agentic-ai/llm_gateway/app.py), [`webui/src/views/CanvasView.jsx`](file:///Users/donthireddy/code/github/agentic-ai/webui/src/views/CanvasView.jsx)

---

## 🌟 1. What It Does (Plain English & Analogy)

**Parallel Agent Execution (Swarms)** is a Directed Acyclic Graph (DAG) orchestration architecture that breaks a complex workflow into independent parallel tasks (Fan-Out / Fork) executed simultaneously using **Kahn's Topological Sorting Algorithm** and asynchronous worker swarms (`asyncio.gather`), before consolidating results into a unified synthesis (Fan-In / Join).

> 💡 **The Real-World Analogy**:  
> Imagine planning a luxury weekend wedding in Paris.  
> - **Sequential Approach**: One person calls airlines for 45 minutes, then checks 10 hotels for 45 minutes, then looks up weather for 15 minutes, then calculates the restaurant budget for 15 minutes (Total: **120 minutes**).  
> - **Parallel Swarm Approach**: You assign 3 specialist assistants at the exact same moment—Assistant 1 books flights, Assistant 2 checks hotels, Assistant 3 checks weather and budgets. All 3 report back in **45 minutes**, and the head planner delivers the complete itinerary in record time.

---

## 🎯 2. Why & How It Helps (Value Proposition)

### "The Challenge Before" vs. "How This Solves It"

| The Challenge Before | How This Solves It |
|---|---|
| **Cumulative Latency (Waterfall Delays)**: Running 4 tools sequentially (e.g. 2.5s each) forces the user to wait 10+ seconds for a reply. | **Parallel Stage Waves**: Independent nodes execute concurrently in non-blocking async tasks (`asyncio.gather`), reducing total wait time to the slowest single node (~2.6s). |
| **Complex Dependencies Crashing**: Manually scripting which agent runs first leads to race conditions and missing data. | **Kahn's Topological Ordering**: Automatically computes dependency in-degrees ($d=0$), guaranteeing upstream data is available before downstream nodes trigger. |
| **Stale Context Overhead**: Agents repeating basic instructions over and over across separate chats. | **Clean Parent-Context Injection**: Downstream nodes receive only the clean outputs of their explicit parent dependencies. |

---

## 🚀 3. Real-World Step-by-Step Scenario

### Real-World E-Commerce Scenario: Customer Support Refund & Fraud Triage Swarm

```mermaid
flowchart TD
    UserQuery["Customer Ticket #4829:\n'I received damaged headphones. Requesting $240 refund to original card.'"]
    
    subgraph Stage 1: Supervisor Decomposer
        UserQuery --> Supervisor["Stage 1: Supervisor Agent\n(Triage & Entity Extractor)"]
    end
    
    subgraph Stage 2: Concurrent Parallel Swarm (Fan-Out)
        Supervisor -->|Fork| Tool1["Stage 2A: MCP Tool\n(product_knowledge: Verify Return Policy)"]
        Supervisor -->|Fork| Tool2["Stage 2B: MCP Tool\n(workspace_file_ops: Check Order Log)"]
        Supervisor -->|Fork| Agent3["Stage 2C: Risk Agent\n(Fraud & Account Health Check)"]
    end
    
    subgraph Stage 3: Human-in-the-Loop Safety Gate
        Tool1 --> HITL["Stage 3: HITL Safety Gate\n(Policy: Auto-approve < $100; Require sign-off >= $100)"]
        Tool2 --> HITL
        Agent3 --> HITL
    end
    
    subgraph Stage 4: Consensus Synthesizer (Fan-In)
        HITL --> Synthesizer["Stage 4: Synthesizer Agent\n(Generates customer response & dispatch instructions)"]
    end

    classDef s1 fill:#1e1b4b,stroke:#6366f1,stroke-width:2px,color:#fff;
    classDef s2 fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#fff;
    classDef s3 fill:#78350f,stroke:#f59e0b,stroke-width:2px,color:#fff;
    classDef s4 fill:#701a75,stroke:#d946ef,stroke-width:2px,color:#fff;

    class Supervisor s1;
    class Tool1,Tool2,Agent3 s2;
    class HITL s3;
    class Synthesizer s4;
```

### Step-by-Step UI Execution:

1. Open **Visual Workflow Canvas** (`http://localhost:8000/canvas`).
2. Click **`🔱 1-to-3 Parallel Swarm Fork`** template.
3. Configure the 3 parallel Stage 2 nodes:
   - **Node 2A (Tool)**: `product_knowledge`
   - **Node 2B (Agent)**: `Risk & Compliance Officer`
   - **Node 2C (Tool)**: `calculate`
4. Set the pipeline name: **`📝 Name: Refund & Warranty Triage Swarm`**.
5. Click **`[💾 Save Pipeline]`**.
6. Switch to **AI Agent Chatbot** (`/chat`), select **`⚡ Refund & Warranty Triage Swarm`** from the **Workflow DAG** selector.
7. Type: *"Customer requested refund on $240 wireless headphones order #891"*.
8. Hit **Send**:
   - The UI runs Stage 1 (Decomposer) $\rightarrow$ Stage 2 (Swarm: 3 nodes execute in parallel) $\rightarrow$ Stage 3 (Synthesizer).
   - A complete **DAG Execution Trace Card** with stage durations and final customer letter renders in seconds!

---

## 😄 4. Witty & Relatable Commentary

> *"Waiting for 4 sequential AI tool calls is like standing in line at the DMV while the clerk processes one person, takes a 10-minute coffee break, and walks over to the filing cabinet. With Parallel Swarms, we hire 4 clerks who work at the exact same instant!"*

---

## 💻 5. Under-the-Hood Code & API Endpoints

### Kahn's Algorithm Topological Sorting Implementation:
```python
# llm_gateway/app.py -> /api/canvas/execute
@app.post("/api/canvas/execute")
async def canvas_execute_api(req: CanvasExecuteRequest):
    # 1. Compute in-degrees and adjacency
    node_map = {n["id"]: n for n in req.nodes}
    adj = defaultdict(list)
    in_degree = {n["id"]: 0 for n in req.nodes}
    
    for edge in req.edges:
        src, tgt = edge["source"], edge["target"]
        if src in node_map and tgt in node_map:
            adj[src].append(tgt)
            in_degree[tgt] += 1

    # 2. Extract topological waves (stages)
    queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
    stages = []
    
    while queue:
        current_stage = list(queue)
        stages.append(current_stage)
        queue.clear()
        
        for u in current_stage:
            for v in adj[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)

    # 3. Execute each stage concurrently
    node_outputs = {}
    for stage_node_ids in stages:
        stage_tasks = [execute_single_node(nid, node_map, node_outputs, req.initial_input) for nid in stage_node_ids]
        # PARALLEL SWARM EXECUTION
        results = await asyncio.gather(*stage_tasks)
        for r in results:
            node_outputs[r["node_id"]] = r["output"]

    return {
        "status": "success",
        "stages_count": len(stages),
        "execution_trace": execution_trace,
        "final_output": synthesize_output(stages[-1], node_outputs)
    }
```
