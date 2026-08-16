# Agentic AI: Real-World Everyday Tools, Fun Skills & LiteLLM Gateway

A modular architecture for building and running autonomous AI agents powered by local LLMs via **Ollama**, real-world everyday tools (**Calculator**, **Live Weather**, **Web Search**, **Shopping Product Catalog**), fun domain skills (**Vacation Concierge**, **Personal Shopper**, **Party Host**, **Home Chef**), and centralized prompt/token audit logging via a **LiteLLM Gateway**.

---

## 🏗️ Architecture Overview

```mermaid
flowchart TD
    subgraph Agent["agent/"]
        A["Agent Loop - agent.py"]
        MCP_C["MCP Client Manager"]
        GW_C["LLM Gateway Client"]
    end

    subgraph LLMGateway["llm-gateway/"]
        GW["FastAPI + LiteLLM Proxy - app.py"]
        UI["Web Dashboard UI - http://localhost:8000/"]
        Logger[("SQLite Audit DB: llm_gateway.db")]
        JSONL["JSONL Audit Stream: gateway_audit.jsonl"]
    end

    subgraph MCPServer["mcp-server/"]
        S["MCP Server - server.py"]
        subgraph Tools["Everyday Tools"]
            T1["calculator / calculate"]
            T2["weather"]
            T3["web_search"]
            T4["product_knowledge"]
            T5["workspace_file_ops"]
        end
        subgraph Skills["Fun Domain Skills"]
            SK1["travel_planner_skill 🏖️"]
            SK2["shopping_assistant_skill 🛍️"]
            SK3["party_planner_skill 🎉"]
            SK4["chef_meal_planner_skill 🍳"]
        end
    end

    subgraph OllamaLocal["Local LLM Backend"]
        OLLAMA["Ollama Server :11434 (qwen2.5-coder:7b / llama3.2)"]
    end

    Agent <-->|Discover Tools/Skills & Execute| MCP_C <-->|STDIO / MCP Protocol| S
    A -->|Chat Request + Context + Tools/Skills| GW_C -->|HTTP /v1/chat/completions| GW
    GW -->|Audit Logging: Prompts, Tokens, Context| Logger
    GW -->|Append Log Stream| JSONL
    GW <-->|litellm.acompletion| OLLAMA
    UI <-->|Live Telemetry, Logs & Playground| GW
```

---

## 📂 Project Structure

```
agentic-ai/
├── mcp_server/                 # Model Context Protocol (MCP) Server
│   ├── server.py               # MCP Server exposing tools & prompt-based skills
│   ├── tools/                  # Real-world everyday tools (math, weather, search, products, files)
│   ├── skills/                 # Fun interactive skills (travel, shopping, party, chef)
│   ├── tests/                  # Unit test suite (14 test cases)
│   └── requirements.txt
│
├── llm_gateway/                # LiteLLM Proxy & Audit Gateway + Studio UI
│   ├── app.py                  # FastAPI application routing LLM completions & UI
│   ├── static/                 # Unified Single Web Studio (HTML/CSS/JS)
│   ├── db.py                   # SQLite storage for audit records
│   ├── logger.py               # Audit logging engine (SQLite + JSONL)
│   ├── models.py               # Pydantic schemas for requests/context
│   ├── tests/                  # Unit test suite (7 test cases)
│   └── requirements.txt
│
├── ai_agent/                   # Autonomous LLM Agent Loop & Package
│   ├── agent.py                # Core Agent loop managing ReAct tool-calling
│   ├── mcp_client.py           # MCP Client connecting to MCP Server over STDIO
│   ├── gateway_client.py       # Client for communicating with LLM Gateway
│   ├── cli.py                  # Interactive Rich terminal CLI
│   ├── demo.py                 # Automated end-to-end verification script
│   ├── tests/                  # Unit test suite (3 test cases)
│   └── requirements.txt
│
├── evals_framework/            # 4-Grader Generic Agent & Model Evaluation Suite
│   ├── adapters/               # Pluggable Agent Adapters (MCP, HTTP REST, Custom Callable)
│   ├── registries/             # Dynamic Model & LLM-as-a-Judge Registries
│   ├── runner.py               # Generic benchmark runner (Dynamic Agent x Model x Judge)
│   ├── history.py              # Historical run comparison & matrix engine
│   ├── datasets/               # Benchmark cases (tool calling, skills, reasoning)
│   ├── graders/                # 4 graders: deterministic, efficiency, llm-judge, fact-checker
│   ├── evaluators/             # Accuracy, adherence, correctness, performance scorers
│   ├── reporters/              # Console and Markdown report generators
│   ├── tests/                  # Unit test suite (20 test cases)
│   ├── laymans_guide.md        # Comprehensive visual guide with real-world scenarios
│   └── reports/                # Benchmark reports (.json and .md)
│
├── scripts/
│   ├── run_gateway.sh          # Helper to start LLM Gateway on port 8000
│   ├── run_agent.sh            # Helper to launch the interactive Agent CLI
│   ├── run_demo.sh             # Helper to run the automated E2E demo
│   ├── run_evals.sh            # Helper to execute the evaluation runner
│   └── inspect_logs.py         # CLI tool to query and inspect audit database
├── docker-compose.yml          # Unified Studio container with live volume mounts
├── Dockerfile                  # Studio runtime image definition
├── restart.sh                  # One-click studio restart & healthcheck script
├── .env.example
├── .gitignore
└── README.md
```

---

## 🧪 Unit Testing

Run all **63 automated unit tests** across all 4 components:

```bash
pytest mcp_server/tests llm_gateway/tests ai_agent/tests evals_framework/tests -v
```

---

## 🔌 Transport Layer: Stdio vs HTTP Configuration

The LLM Gateway supports dual transport layers: **HTTP** (FastAPI / REST API) and **Stdio** (JSON Lines / Subprocess IPC). You can configure which transport to use depending on your workflow.

### 📊 Transport Comparison

| Feature | HTTP Mode (`http`) | Stdio Mode (`stdio`) |
| :--- | :--- | :--- |
| **Protocol** | REST / JSON over HTTP (`http://localhost:8000`) | JSON Lines over standard I/O (`stdin` / `stdout`) |
| **Server Requirement** | Runs FastAPI daemon on port 8000 | Spawns an on-demand Python subprocess |
| **Best For** | Web Studio UI, multi-client access, Docker | Terminal CLIs, scripting, pipelines, embedded agents |
| **Logging** | Console + SQLite audit database | `stderr` + SQLite audit database (`stdout` stays clean JSON) |

---

### 🛠️ Where to Set `stdio` vs `http`

You can set the transport mode in **4 different ways**:

#### 1. In your `.env` File *(Global Setting)*
Edit the `GATEWAY_TRANSPORT` key in [`.env`](file:///Users/donthireddy/code/github/agentic-ai/.env):
```ini
# Choose: "http" or "stdio"
GATEWAY_TRANSPORT=stdio

# Model configuration
DEFAULT_MODEL=ollama/gemma2:2b
FALLBACK_MODEL=ollama/llama3.2
OLLAMA_API_BASE=http://localhost:11434
```

#### 2. In Python Code *(Per Agent or Client Instance)*
Pass `gateway_transport` directly when creating an Agent or Client:
```python
from ai_agent import AgenticLLMAgent, LLMGatewayClient

# 1. On the Agent:
agent = AgenticLLMAgent(
    gateway_transport="stdio",        # Set to "stdio" or "http"
    model="ollama/gemma2:2b"
)

# 2. On the Gateway Client:
client = LLMGatewayClient(
    transport="stdio"                 # Set to "stdio" or "http"
)
```

#### 3. Via Command-Line Flags *(CLI)*
All CLI runner scripts and entry points accept the `--transport` flag:
```bash
# Run the Gateway server in stdio or http mode:
python -m llm_gateway --transport stdio
python -m llm_gateway --transport http --port 8000

# Run the Interactive Agent CLI in stdio mode:
./scripts/run_agent.sh --transport stdio --model ollama/gemma2:2b
```

#### 4. Parameterized Factory Function (`get_config`)
In Python modules, you can construct custom configurations dynamically:
```python
from llm_gateway.config import get_config

# Create a custom stdio configuration instance:
custom_cfg = get_config(
    transport="stdio",
    default_model="ollama/mistral:latest"
)
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python 3.10+** (Python 3.12 recommended)
- **Ollama** running locally:
  ```bash
  ollama run qwen2.5-coder:7b
  # or
  ollama run llama3.2
  ```

### 2. Environment Setup
Install dependencies with `uv` (recommended) or standard `pip`:
```bash
# Create and activate virtual environment
uv venv .venv
source .venv/bin/activate

# Install all dependencies
uv pip install -r requirements.txt
```

---

## 🐳 Consolidated Docker Deployment (One-Command Launch)

The entire architecture (LiteLLM Gateway, MCP Tool Server, AI Agent Chatbot, Audit Logger, and Evals Framework) is unified into a single Docker setup. You don't need to start multiple separate containers or run multiple scripts.

### 🚀 One-Command Launch
```bash
./scripts/docker_run.sh
# Or directly via Docker Compose:
docker compose up --build -d
```

### 🌐 Access Everything from One Unified UI
Open your browser to:
👉 **[http://localhost:8000/](http://localhost:8000/)**

From this single web interface, you can:
1. **💬 Chat with the AI Agent** (with real-time MCP tool execution cards & skill selectors).
2. **📊 Monitor Token & Latency Telemetry** (live charts & metrics).
3. **📜 Inspect Historical Prompts & Audit Logs** (searchable logs & full message inspector).
4. **🧪 Execute 4-Grader Evals & Benchmarks** (interactive scorecard & markdown report viewer).

### Useful Docker Commands:
```bash
# View live application logs
docker compose logs -f

# Stop the entire stack
docker compose down
```

---

## 🏃 Running Locally (Without Docker)

### Step 1: Start the LLM Gateway
In a terminal window:
```bash
./scripts/run_gateway.sh
```
*The gateway starts on `http://localhost:8000`, exposes `/v1/chat/completions`, and connects to Ollama at `http://localhost:11434`.*

### Step 2: Run the Automated E2E Demo
In another terminal:
```bash
./scripts/run_demo.sh
```
This tests:
1. **MCP Tool Calling**: Math calculation (`calculate`) and Python execution (`execute_python`).
2. **System Diagnostics**: Host hardware inspection (`get_system_metrics`) and workspace file writing (`workspace_file_ops`).
3. **Skill Activation**: Injects `data_analysis_skill` to compute growth trends.
4. **Audit Verification**: Validates persisted records in `llm_gateway.db`.

### Step 4: Run the Generic Evals Framework
Benchmark any Agent Adapter against candidate models and LLM judges across tool accuracy, skill adherence, correctness, and token efficiency:

```bash
# Evaluate default agent and model (qwen2.5-coder:7b)
./scripts/run_evals.sh ollama/qwen2.5-coder:7b

# Run via Python API with custom adapter, model, and judge:
python -c "
import asyncio
from evals_framework import EvalsRunner, MCPAgentAdapter, model_registry, judge_registry

adapter = MCPAgentAdapter(adapter_id='mcp_default', name='MCP Agent')
runner = EvalsRunner(agent_adapter=adapter, model='ollama/qwen2.5-coder:7b', judge_model='ollama/llama3.2')
asyncio.run(runner.run_suite(['tool_calling', 'skill_adherence', 'reasoning']))
"
```

---

## 🧪 Generic Evals Framework & Comparative Dashboard

The framework provides an open, pluggable architecture designed to benchmark **any Agent**, **any Candidate Model**, and **any LLM-as-a-Judge**:

```mermaid
flowchart LR
    subgraph Registries["Dynamic Registries"]
        AR["Agent Registry<br/>(MCP, HTTP REST, Callable)"]
        MR["Model Registry<br/>(Ollama, Cloud LLMs)"]
        JR["Judge Registry<br/>(LLM-as-a-Judge Rubrics)"]
    end

    subgraph Runner["Generic Evals Runner"]
        E["EvalsRunner(adapter, model, judge)"]
    end

    subgraph Graders["4-Grader Pipeline"]
        G1["1. Deterministic Rulebook"]
        G2["2. Efficiency & Latency"]
        G3["3. LLM-as-a-Judge"]
        G4["4. Fact-Checker Grounding"]
    end

    subgraph Outputs["Reporting & History"]
        H[("History Engine")]
        MD["Markdown & JSON Reports"]
        UI["Studio Side-by-Side Comparison Matrix"]
    end

    AR & MR & JR --> Runner --> Graders --> Outputs
```

### 🧩 1. Pluggable Agent Adapters (`evals_framework/adapters/`)
- **`MCPAgentAdapter`**: Evaluates native agents communicating with FastMCP tool servers.
- **`HTTPAgentAdapter`**: Benchmarks remote third-party agents over standard HTTP REST endpoints.
- **`CallableAgentAdapter`**: Evaluates arbitrary Python async/sync functions or custom agent pipelines.
- **`AgentRegistry`**: Thread-safe singleton registry allowing dynamic registration and management via UI or REST API.

### 🤖 2. Model & Judge Registries (`evals_framework/registries/`)
- **`ModelRegistry`**: Register and manage candidate models under test (`qwen2.5-coder:7b`, `llama3.2`, `gemma2:2b`, `mistral:latest`, or OpenAI/Custom providers).
- **`JudgeRegistry`**: Register LLM-as-a-Judge evaluators with custom evaluation rubrics and safety criteria.

### 📊 3. Web Studio Evals Views (`http://localhost:8000/`)
The Studio provides **4 dedicated views** in the **🧪 Evals & Benchmarks** tab:
1. 🚀 **1. Run Evals Benchmark**: Select any registered Agent, Model, and Judge to execute tests and view real-time 4-grader scorecard gauges.
2. 🤖 **2. Models & Judges Registry**: Live management table + inline form to register new Candidate Models and LLM Judges.
3. 🔌 **3. Agent Adapters Registry**: Live management table + inline form to register new FastMCP or HTTP REST Agent Adapters.
4. 📊 **4. Historical Runs & Side-by-Side Compare**: Multi-select historical runs with checkboxes to generate an interactive side-by-side comparison matrix with delta metrics across models.

---

## 🛠️ Everyday Tools (Real-World & Non-Technical)

| Tool Name | Real-World Purpose | Example Invocations |
| :--- | :--- | :--- |
| **`calculator`** | Compute dinner bill splitting, restaurant tips, sales discounts, and monthly budgets. | `"Split a $184.50 bill among 4 people"`, `"15% off on $199.99"` |
| **`weather`** | Live global weather conditions, temperatures, umbrella alerts, and 3-day forecasts. | `"What's the weather like in Paris this weekend?"`, `"Tokyo forecast"` |
| **`web_search`** | Search trending travel guides, top food spots, game night ideas, and 15-min recipes. | `"Top ramen shops in Tokyo"`, `"Fun games for party of 8"` |
| **`product_knowledge`** | Browse top-rated consumer products (espresso machines, headphones, luggage, cozy hoodies). | `"Find top-rated headphones on sale"`, `"Look up espresso maker"` |
| **`workspace_file_ops`** | Save vacation packing checklists, grocery lists, and party schedules to files. | `"Save packing list to packing_list.txt"` |

---

## 🌟 Fun & Easy-to-Understand Domain Skills

| Skill Name | Role & Persona | What it Does |
| :--- | :--- | :--- |
| **`travel_planner_skill`** | 🏖️ **Vacation & Adventure Concierge** | Checks the live weather, crafts exciting day-by-day itineraries, suggests local bakeries & sights, and gives packing advice. |
| **`shopping_assistant_skill`** | 🛍️ **Personal Shopper & Gift Finder** | Searches the product catalog, calculates exact discount prices, compares gift ideas, and highlights customer reviews. |
| **`party_planner_skill`** | 🎉 **Epic Party & Celebration Host** | Plans game nights, birthday bashes, and dinners — calculating pizza/snack quantities, checking weather, and picking fun games. |
| **`chef_meal_planner_skill`** | 🍳 **Cozy Home Chef & Meal Crafter** | Creates delicious 15-to-30 minute weeknight dinner recipes, categorized grocery lists, and scaled serving sizes. |

---

## 📊 LLM Gateway Audit Logging

The LLM Gateway captures every request and response, recording:
- **Full Prompts & Messages**: All system instructions, user queries, assistant replies, and tool responses.
- **Token Usage**: `prompt_tokens`, `completion_tokens`, `total_tokens`.
- **Caller Context**: `caller_id`, `agent_name`, `session_id`, client IP, custom headers (`X-Caller-Context`).
- **Discovered & Invoked Tools**: Names of all tools available and executed.
- **Active Skills**: Skill names injected during the turn.
- **Performance**: Exact request latency in milliseconds (`latency_ms`).

### Inspecting Audit Logs
Use the included CLI tool:
```bash
# View summary stats and recent calls
python scripts/inspect_logs.py

# Inspect complete details (including full prompts and responses) for a specific call ID:
python scripts/inspect_logs.py --detail call_xxxxxxxxx

# Filter by session or agent:
python scripts/inspect_logs.py --session demo_sess_123
python scripts/inspect_logs.py --agent DemoAgent-E2E
```

### Gateway REST Endpoints
- `POST /v1/chat/completions`: OpenAI-compatible proxy routing to local Ollama via LiteLLM.
- `GET /v1/models`: List available local models.
- `GET /v1/logs`: Retrieve audit records with filtering and pagination.
- `GET /v1/stats`: Aggregate token consumption and tool/skill usage frequencies.
- `GET /health`: Health status of Gateway and Ollama connectivity.
