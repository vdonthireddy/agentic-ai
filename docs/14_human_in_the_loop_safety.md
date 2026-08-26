# 🛡️ 14. Human-in-the-Loop (HITL) Safety & Policy Guardrails

> **Author**: Vijay Donthireddy  
> **Repository**: [vdonthireddy/agentic-ai](https://github.com/vdonthireddy/agentic-ai)  
> **Route**: All Views (Chatbot, Workflow Canvas, Tools)  
> **Component Sources**: [`mcp_server/hitl.py`](file:///Users/donthireddy/code/github/agentic-ai/mcp_server/hitl.py), [`webui/src/views/ChatView.jsx`](file:///Users/donthireddy/code/github/agentic-ai/webui/src/views/ChatView.jsx), [`llm_gateway/app.py`](file:///Users/donthireddy/code/github/agentic-ai/llm_gateway/app.py)  
> **Documentation Track**: [Phase 4: Enterprise Safety, Guardrails & Governance](./README.md#phase-4-enterprise-safety-guardrails--governance)  
> **Navigation**: [🏠 Docs Hub](./README.md) | [⬅️ Prev: 12. Multi-Agent Debate](./12_multi_agent_debate_protocol.md) | **Step 12 of 18** | [➡️ Next: 17. Security Firewall & Defense](./17_security_firewall_prompt_defense.md)

---

> 🔗 **Related Deep-Dive Modules**:
> - 🛡️ [17. Security Firewall & Prompt Defense](./17_security_firewall_prompt_defense.md) — Protect against prompt injections, secret leakage, and path traversal.
> - 💰 [18. Rate Limiting & Cost Tracking](./18_rate_limiting_and_cost_tracking.md) — Prevent token resource exhaustion and budget blowouts.
> - 🔱 [02. Workflow Canvas (DAG)](./02_workflow_canvas_dag.md) — Wire HITL approval gate nodes visually into multi-stage pipelines.
> - 📜 [07. Audit Logs](./07_audit_logs.md) — Inspect cryptographically signed `[AUTH_200_OK]` approval tokens.

---

## 🌟 1. What It Does (Plain English & Analogy)

The **Human-in-the-Loop (HITL) Safety & Guardrails Engine** acts as an intelligent supervisor and safety checkpoint. Whenever an autonomous agent or a workflow pipeline attempts a high-stakes action (such as issuing a customer refund over $100, deleting files, modifying production databases, or reaching an explicit DAG approval gate), the engine intercepts execution, pauses the pipeline, and displays an interactive approval modal for human verification before proceeding.

> 💡 **The Real-World Analogy**:  
> Think of the "Dual-Key System" in a bank vault or a commercial aircraft cockpit. The pilot can fly the plane on autopilot, but turning off the engines or dumping fuel requires explicit human confirmation and a physical switch flip.

---

## 🎯 2. Why & How It Helps (Value Proposition)

### "The Challenge Before" vs. "How This Solves It"

| The Challenge Before | How This Solves It |
|---|---|
| **Runaway Autonomous Damage**: Agents accidentally executing destructive commands (e.g., `DELETE FROM users` or issuing large refunds). | **Configurable Policy Interception**: High-risk actions are automatically trapped and held in a pending state until a human signs off. |
| **Pipeline Continues After Denial**: Denying an action still leaves downstream pipeline stages running. | **Strict Circuit Breaker**: Denying any approval gate immediately aborts the pipeline and blocks all downstream stages from executing. |
| **Complete System Freezing**: Pausing the entire server for human approval blocks other users and threads. | **Asynchronous Non-Blocking Queues**: Uses async event loops so other agent threads continue while waiting for approval on specific request IDs. |
| **No Audit of Approved Actions**: Unclear who approved an agent's destructive action. | **Cryptographic Approval Tokens**: Generates unique `[AUTH_200_OK]` tokens with timestamps and approver identities stored in the audit DB. |

---

## 🚀 3. Real-World Step-by-Step Scenarios

### Mode A: Intercepting a Protected Tool Action in Standard Chat
```mermaid
sequenceDiagram
    autonumber
    actor Customer as 👤 User
    participant Agent as 🤖 AI Agent
    participant HITL as 🛡️ HITL Guardrail Engine
    actor Admin as 👨‍💼 Human Admin (UI)
    participant Tool as 💳 Payment API Tool

    Customer->>Agent: "Please process a $350 refund for Order #9912"
    Agent->>HITL: Request tool_call: issue_refund(amount=350)
    Note over HITL: Policy Check: amount > $100 -> TRIGGER HITL
    HITL-->>Admin: Displays Modal: "Approve $350 Refund for Order #9912?"
    
    alt Admin Clicks "Approve"
        Admin->>HITL: POST /api/hitl/approve/{request_id}
        HITL->>Tool: Releases execution with [AUTH_200_OK]
        Tool-->>Agent: Refund Successful
        Agent-->>Customer: "Your $350 refund has been approved and processed."
    else Admin Clicks "Deny"
        Admin->>HITL: POST /api/hitl/deny/{request_id}
        HITL-->>Agent: Execution Rejected by Admin
        Agent-->>Customer: "Refund request requires manager review and was not authorized."
    end
```

---

### Mode B: Wired HITL Approval Node in Workflow Canvas DAG

#### 1. Wiring the Node in Workflow Canvas (`/canvas`)
1. Drag a **🛡️ HITL Approval Gate Node** onto the canvas.
2. Select the trigger policy:
   - `⚡ Always Require Approval`: Stops every time execution reaches this node.
   - `💰 Financial Threshold (> $100)`: Only triggers if payload contains financial amounts $\ge \$100$.
   - `🗑️ File Deletions / Writes`: Triggers when files are modified or deleted.
3. Wire the gate between upstream data sources and downstream execution stages.
4. Click **`[💾 Save Pipeline]`**.

#### 2. Running with Live Prompts in the Chatbot (`/chat`)
1. Select your saved pipeline in the **`🔱 Workflow DAG`** dropdown.
2. Type your prompt and click **Send**.
3. When the pipeline hits the HITL gate:
   - The glowing **🛡️ Human Approval Required** modal appears in the center of the screen.
   - It displays the prompt, node ID, and policy reason.

#### 3. Handling the Approval Modal
* **Click `[✅ Approve Action]`**:
  - The gate issues token `[AUTH_200_OK]`.
  - The remaining downstream stages execute seamlessly to completion.
* **Click `[❌ Deny Action]`**:
  - The DAG **halts immediately**.
  - All downstream nodes are **blocked**.
  - A red security alert banner explains that execution was safely aborted by the operator.

---

## 😄 4. Witty & Relatable Commentary

> *"An autonomous agent without HITL guardrails is like giving your credit card to your toddler and walking out of the room. It only takes 30 seconds before you've bought 500 cases of candy. Keep the keys in human hands!"*

---

## 💻 5. Under-the-Hood Code & API Endpoints

- **Pending Approvals Endpoint**: `GET /api/hitl/pending`
- **Approve Request Endpoint**: `POST /api/hitl/approve/{request_id}`
- **Deny Request Endpoint**: `POST /api/hitl/deny/{request_id}`
- **HITL Engine Source**: [`mcp_server/hitl.py`](file:///Users/donthireddy/code/github/agentic-ai/mcp_server/hitl.py)
- **DAG Execution Engine**: [`llm_gateway/app.py`](file:///Users/donthireddy/code/github/agentic-ai/llm_gateway/app.py) (`/api/canvas/execute`)

---

## 🧭 Next Step in Your Journey

Now that you know how human gates protect high-stakes actions, learn how the Security Firewall blocks prompt injections and masks sensitive PII:

👉 **[Continue to 17. Security Firewall & Prompt Defense Guide](./17_security_firewall_prompt_defense.md)**
