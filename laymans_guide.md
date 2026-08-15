# 🏰 The Layman's Grand Tour of Agentic AI
### *How All 4 Projects Work Together as One Supercharged AI Assistant*

---

## 🌟 The Big Picture in 30 Seconds

Think of this entire project as building a **World-Class AI Concierge Agency**:

```mermaid
flowchart TD
    User["👤 You (in the Web UI or Chat)"] --> Agent["🧠 1. The Autonomous Agent (ai_agent)<br/>*Understands your goal & plans steps*"]
    
    Agent <-->|"Reaches into toolbelt"| MCP["🛠️ 2. The Toolbelt (mcp_server)<br/>*Calculator, Live Weather, Product Store, Web Search*"]
    
    Agent <-->|"Sends thought requests"| Gateway["🛂 3. The Receptionist & Accountant (llm_gateway)<br/>*Counts words, logs receipts & talks to Ollama*"]
    
    Gateway <-->|"Local Brain"| LocalLLM["💻 Local Ollama Brain (qwen2.5 / llama3.2)"]
    
    Evals["🧪 4. The Quality Inspector (evals_framework)<br/>*Grades the agent with 4 tests before going live*"] -.-> Agent
```

---

## 🏢 The 4 Team Members Explained Simply

| Folder | Name & Analogy | What It Does For You |
| :--- | :--- | :--- |
| 🛠️ [**`mcp_server/`**](file:///Users/donthireddy/code/github/agentic-ai/mcp_server/laymans_guide.md) | **The Toolbelt & Hands** | Gives the AI real-world tools: calculating bill splits, looking up live weather, searching 15-min pasta recipes, and checking product prices. |
| 🧠 [**`ai_agent/`**](file:///Users/donthireddy/code/github/agentic-ai/ai_agent/laymans_guide.md) | **The Smart Concierge** | Solves multi-step problems (Think ➔ Act ➔ Observe ➔ Answer) and wears specialized skill hats (Vacation Guide, Shopper, Party Host, Chef). |
| 🛂 [**`llm_gateway/`**](file:///Users/donthireddy/code/github/agentic-ai/llm_gateway/laymans_guide.md) | **The Air Traffic Controller & Accountant** | Logs every conversation receipt, counts word tokens, tracks speed, and hosts the **Unified Web Studio UI** at `http://localhost:8000/`. |
| 🧪 [**`evals_framework/`**](file:///Users/donthireddy/code/github/agentic-ai/evals_framework/laymans_guide.md) | **The Driving Test & Quality Inspector** | Grades the AI with 4 judges: Rulebook compliance, Token budget efficiency, Safety, and Truthfulness (no hallucinations). |

---

## 🎬 A Real-World Story: Planning a Weekend in Paris

Here is what happens when you type:
> *"I'm going to Paris with a friend. What's the weather, what's a good 2-day itinerary with cozy bakeries, and how much is a $190 dinner split between 2 people?"*

```mermaid
sequenceDiagram
    autonumber
    actor You as 👤 You
    participant UI as 🖥️ Unified Web Studio (Port 8000)
    participant Agent as 🧠 Agent Client (Vacation Skill)
    participant MCP as 🛠️ MCP Server (Tools)
    participant GW as 🛂 LLM Gateway
    participant Ollama as 💻 Local Ollama Brain

    You->>UI: Types question
    UI->>Agent: Passes goal to Vacation Concierge
    
    Note over Agent: Step 1: Check Live Weather
    Agent->>MCP: Call weather('Paris')
    MCP-->>Agent: Returns '68°F, Partly Cloudy'
    
    Note over Agent: Step 2: Calculate Dinner Split
    Agent->>MCP: Call calculator('190 / 2')
    MCP-->>Agent: Returns '$95.00'
    
    Note over Agent: Step 3: Draft Final Recommendations
    Agent->>GW: Request final response
    GW->>Ollama: Generate friendly vacation summary
    Ollama-->>GW: Returns response text
    GW-->>UI: Saves timestamped token receipt to Database
    
    UI->>You: "Paris is 68°F and beautiful! Here is your 2-day bakery itinerary, and dinner is $95/person! 🥐"
```

---

## 🚀 How to Experience It in 1 Step

You can launch the entire ecosystem in **one single command**:

```bash
# Start the unified studio
./scripts/docker_run.sh
```

Then open your browser to:
👉 [**`http://localhost:8000/`**](http://localhost:8000/)

* Chat with the AI using real-world tools.
* Watch token meters and live charts.
* Run the 4-grader evaluation benchmark suite with one click!
