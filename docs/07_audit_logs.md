# 📜 07. Audit Logs — Step-by-Step UI Guide

> **Author**: Vijay Donthireddy  
> **Route**: `http://localhost:8000/logs`  
> **Component Source**: [`webui/src/views/AuditLogsView.jsx`](file:///Users/donthireddy/code/github/agentic-ai/webui/src/views/AuditLogsView.jsx)

---

## 🌟 1. What It Does (Plain English & Analogy)

The **Audit Logs** view is the comprehensive forensic recorder and flight data recorder for every single request that passes through the LLM Gateway. It captures full prompts, raw responses, tool execution arguments, session IDs, turn IDs, caller context, latency, and token metrics.

> 💡 **The Real-World Analogy**:  
> Think of the **Audit Logs** as the impenetrable "Black Box" flight recorder on an airplane. If an agent takes an unexpected action or fails a tool call, you can replay the exact sequence of events millisecond-by-millisecond to see what happened.

---

## 🎯 2. Why & How It Helps (Value Proposition)

### "The Challenge Before" vs. "How This Solves It"

| The Challenge Before | How This Solves It |
|---|---|
| **Black Box AI**: You have no idea what system prompt or raw tokens the model actually saw. | **Full Raw Prompt & Completion Capture**: Complete visibility into system messages, user inputs, and assistant outputs. |
| **Untraceable Multi-Turn Conversations**: Debugging turn 5 of a long conversation is impossible when logs are disconnected. | **Hierarchical Session & Turn IDs**: Groups logs by `conversation_id` and `turn_id` for end-to-end conversation tracing. |
| **Compliance & Audit Failures**: Enterprise AI requires strict proof of what tools were executed. | **Structured JSONL & SQLite Audit DB**: Certified append-only audit trail with export to CSV/JSON. |

---

## 🚀 3. Real-World Step-by-Step Scenario

### Scenario: Finding a Failed Tool Call or Inspecting Token Consumption

```mermaid
flowchart LR
    User["Search & Filter Bar"] --> Filter["Filter: model='gemma2:2b', status='200'"]
    Filter --> Table["Audit Log Table"]
    Table --> Expand["Click Row to Expand Full JSON"]
    Expand --> Export["Click 'Export CSV/JSON'"]

    classDef cIndigo fill:#1e1b4b,stroke:#6366f1,stroke-width:2px,color:#fff;
    classDef cCyan fill:#082f49,stroke:#0ea5e9,stroke-width:2px,color:#fff;
    classDef cAmber fill:#78350f,stroke:#f59e0b,stroke-width:2px,color:#fff;
    classDef cEmerald fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#fff;
    classDef cFuchsia fill:#701a75,stroke:#d946ef,stroke-width:2px,color:#fff;

    class User cIndigo;
    class Filter cCyan;
    class Table cAmber;
    class Expand cEmerald;
    class Export cFuchsia;
```

### Step-by-Step UI Actions:

1. **Open Audit Logs**: Click **Audit Logs** in the left navigation sidebar.
2. **Search & Filter**:
   - Filter by **Model**: Select `ollama/gemma2:2b` or `openai/gpt-4o`.
   - Filter by **Session / Turn ID**: Paste a specific `turn_id` or `conversation_id`.
   - Filter by **Status**: View only errors (`4xx/5xx`) or successful completions (`200`).
3. **Inspect Request Details**:
   - Click on any row to expand the accordion view.
   - View formatted **Prompt History**, **Executed Tool Calls**, and **Raw Assistant Response**.
4. **Export Data**: Click the **`⬇️ Export CSV`** or **`⬇️ Export JSON`** button to download log records for offline compliance audits.

---

## 😄 4. Witty & Relatable Commentary

> *"When your AI agent accidentally orders 500 pizzas instead of 5, you don't want to be guessing what went wrong. One search in the Audit Logs and you'll find the exact prompt turn that said 'make it extra large'!"*

---

## 💻 5. Under-the-Hood Code & API Endpoints

- **Query Logs Endpoint**: `GET /api/logs`
- **Hierarchical Logs Endpoint**: `GET /api/logs/hierarchical`
- **Source Database**: `llm_gateway.db` (SQLite) & `gateway_audit.jsonl` (JSONL)
- **Database Handler**: [`llm_gateway/db.py`](file:///Users/donthireddy/code/github/agentic-ai/llm_gateway/db.py)
