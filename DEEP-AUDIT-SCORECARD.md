# 🔬 Deep Architectural Audit — Agentic AI Platform
### Independent Cross-Check Against Production Best Practices

**Audit Date:** 2026-09-12  
**Audited By:** Claude Opus 4.6 (Thinking) — 4 parallel research agents  
**Codebase:** `/Users/donthireddy/code/github/agentic-ai/`  
**Self-Assessed Score (ARCH-REVIEW.md):** 98/100  
**Independent Audit Score: 61/100 — "Strong Prototype with Critical Production Gaps"**

---

## 📊 Scoring Summary (10 Pillars, 100 Points)

| # | Pillar | Weight | Score | Grade | Verdict |
|---|--------|--------|-------|-------|---------|
| 1 | **Security & Sandboxing** | 20 | **6/20** | 🚨 F | Critical RCE, disconnected firewall/rate limiter, zero auth |
| 2 | **Core Agent Logic** | 15 | **10/15** | ⚠️ B | ReAct loop works but has edge-case crashes and no streaming |
| 3 | **Multi-Agent Orchestration** | 10 | **6/10** | ⚠️ C | Deadlock bug in self-healing; double synthesis waste |
| 4 | **LLM Gateway & Routing** | 10 | **6/10** | ⚠️ C | Streaming crashes; smart router drops history & tools |
| 5 | **Memory & Knowledge** | 8 | **6/8** | ✅ B+ | Excellent fallback design; SQLite connection leaks |
| 6 | **Observability & Audit** | 10 | **4/10** | 🚨 D | Cost permanently $0.00; Prometheus crashes; OTel orphaned |
| 7 | **Human-in-the-Loop Safety** | 8 | **4/8** | ⚠️ D+ | Decorator doesn't intercept; gates not wired to execution |
| 8 | **Testing & Quality** | 10 | **5/10** | ⚠️ D+ | 294 tests but critical paths untested; zero CI/CD |
| 9 | **Infrastructure & Deployment** | 9 | **5/9** | ⚠️ D+ | Docker runs as root; unpinned deps; no lockfiles |
| 10 | **Documentation & UX** | 10 | **9/10** | 🌟 A+ | Extraordinary 5,200-line guide; polished 13-tab WebUI |

---

## 🚨 CRITICAL Findings (Severity: Must-Fix Before Any Deployment)

### C1. Unrestricted Remote Code Execution (RCE) in `math_tools.py`
**File:** [`mcp_server/tools/math_tools.py`](file:///Users/donthireddy/code/github/agentic-ai/mcp_server/tools/math_tools.py) — Lines 204–213  
**Impact:** Any user or agent prompt can execute arbitrary system commands.  
```python
# CRITICAL: raw __import__ in sandbox builtins
allowed_builtins = { ... "__import__": __import__ }
scope = {"__builtins__": allowed_builtins}
exec(code_to_run, scope)  # __import__('os').system('rm -rf /')
```
**Status:** `python_tool.py` has AST validation and whitelisted builtins, but `math_tools.py:execute_python_code` is a completely separate, unprotected execution path that bypasses all sandbox guardrails.

---

### C2. Security Firewall Completely Disconnected from Chat Proxy
**File:** [`llm_gateway/app.py`](file:///Users/donthireddy/code/github/agentic-ai/llm_gateway/app.py) — Lines 253–528  
**Impact:** All PII masking, prompt injection detection, and tainted data sanitization is theater — never called on actual completions.  
- `firewall` is imported but only used on the isolated preview route `POST /api/firewall/inspect`.  
- User prompts pass through `/v1/chat/completions` with zero PII redaction and zero injection scanning.
- The entire firewall module is essentially documentation-only.

---

### C3. Rate Limiter Completely Disconnected from Chat Proxy
**File:** [`llm_gateway/app.py`](file:///Users/donthireddy/code/github/agentic-ai/llm_gateway/app.py) — Lines 253–528  
**Impact:** No RPM/TPM throttling on any actual LLM calls. A runaway agent or attacker can burn unlimited cloud API credits.  
- `rate_limiter` is imported and has a working `check_request()` method, but it is never called inside `chat_completions()`.

---

### C4. Zero API Authentication on All Endpoints
**File:** [`llm_gateway/app.py`](file:///Users/donthireddy/code/github/agentic-ai/llm_gateway/app.py) — Lines 111–117, 838–882  
**Impact:** Anyone with network access to port 8000 can:
- Execute arbitrary code via sandbox tools
- Read/write/delete workspace files
- Overwrite cloud API keys via `POST /api/config`
- Trigger expensive LLM generation
- Approve/deny HITL safety gates  

Combined with `allow_origins=["*"]` + `allow_credentials=True` CORS (violates W3C spec), this is exploitable from any website.

---

### C5. HITL Safety Gates Never Actually Intercept Execution
**File:** [`mcp_server/hitl.py`](file:///Users/donthireddy/code/github/agentic-ai/mcp_server/hitl.py) — Lines 385–407  
**Impact:** The `@requires_approval` decorator only stores metadata (`func._hitl_rule = HITLRule(...)`) — it does **not** wrap the function or block execution. File deletions and memory deletions execute instantly without approval.  
Neither `server.py` nor `router.py` call `check_requires_approval()` before executing dangerous operations.

---

### C6. Sandbox Timeout Never Enforced — Server DoS
**File:** [`mcp_server/tools/python_tool.py`](file:///Users/donthireddy/code/github/agentic-ai/mcp_server/tools/python_tool.py) — Lines 83, 221  
**Impact:** `timeout_seconds` parameter exists but is decorative. `exec(actual_code, safe_globals, local_vars)` runs synchronously on the main thread. An infinite loop (`while True: pass`) permanently freezes the server process.

---

### C7. Path Traversal Bypass via String Prefix Check
**Files:** [`mcp_server/tools/file_tools.py`](file:///Users/donthireddy/code/github/agentic-ai/mcp_server/tools/file_tools.py) L16–18, [`mcp_server/router.py`](file:///Users/donthireddy/code/github/agentic-ai/mcp_server/router.py) L291, L307, L323  
**Impact:** `str(resolved).startswith(str(WORKSPACE_ROOT))` doesn't enforce path separator boundaries. If workspace is `/app/workspace`, then `/app/workspace_secret/keys.env` passes the check.  
**Fix:** Use `resolved.is_relative_to(WORKSPACE_ROOT)`.

---

### C8. Streaming Completions Crash
**File:** [`llm_gateway/app.py`](file:///Users/donthireddy/code/github/agentic-ai/llm_gateway/app.py) — Line 428  
**Impact:** When `stream=True`, `litellm.acompletion` returns an `AsyncGenerator`. Line 428 immediately calls `response.choices[0]`, raising `AttributeError: 'async_generator' object has no attribute 'choices'`. The `streaming.py` module exists but is completely orphaned — never imported or used by `app.py`.

---

### C9. Cost Tracking Permanently Reports $0.00
**Files:** [`llm_gateway/cost_tracker.py`](file:///Users/donthireddy/code/github/agentic-ai/llm_gateway/cost_tracker.py) L109–116, [`llm_gateway/db.py`](file:///Users/donthireddy/code/github/agentic-ai/llm_gateway/db.py) L80, L134–139  
**Impact:** `db.py` creates the `cost_usd` column but `save_log_entry` never populates it. The column is always `0.0`. `get_cost_summary` queries `WHERE cost_usd > 0`, finds 0 rows, and the fallback calculation is skipped. Tests mask this by manually inserting `cost_usd: 0.0075` into a synthetic database.

---

### C10. Orchestrator Deadlock in Adaptive Self-Healing
**File:** [`ai_agent/orchestrator.py`](file:///Users/donthireddy/code/github/agentic-ai/ai_agent/orchestrator.py) — Lines 301–309  
**Impact:** When an upstream task fails, the adaptive healing code filters `depends_on` to keep tasks with `status in ("completed", "failed")`. But `get_ready_tasks()` checks `all(dep in completed_ids ...)` where `completed_ids` contains **only** `status == "completed"` tasks. Failed tasks remain in `depends_on` but are never in `completed_ids`, so downstream tasks are **never marked ready**. The loop breaks, and the DAG halts permanently with all downstream tasks stuck in `pending`.

---

## ⚠️ HIGH Severity Findings

### H1. SQL Read-Only Mode Bypass
**File:** [`mcp_server/tools/db_tools.py`](file:///Users/donthireddy/code/github/agentic-ai/mcp_server/tools/db_tools.py) — Lines 40–47, 96, 99  
- Keyword blacklist splits on whitespace, missing SQL comments: `SELECT/**/1;INSERT/**/INTO...`
- Database opened in read-write mode (`sqlite3.connect(str(db_file))` without `?mode=ro`)
- `PRAGMA` allowed, enabling `load_extension` attacks
- Arbitrary `db_path` creates directories anywhere on filesystem

### H2. Debate Arbitrator Receives Wrong Proposal
**File:** [`ai_agent/debate.py`](file:///Users/donthireddy/code/github/agentic-ai/ai_agent/debate.py) — Lines 167–168  
- Arbitrator receives **only** the original Round 1 proposal, never the revised version after incorporating critic feedback
- Both arguments truncated to 800 characters
- All intermediate debate rounds discarded
- `confidence_score` hardcoded to `94.5` regardless of debate outcome (Line 183)

### H3. ReAct Loop Oscillation Bypass
**File:** [`ai_agent/agent.py`](file:///Users/donthireddy/code/github/agentic-ai/ai_agent/agent.py) — Lines 485–491  
- Duplicate detection only checks the immediately previous call
- Tool oscillation (`tool_a` → `tool_b` → `tool_a` → `tool_b`...) resets the counter every step
- Agent can loop indefinitely on alternating tools until `max_tool_iterations` is exhausted

### H4. Smart Router Drops Multi-Turn Context & Tools
**Files:** [`llm_gateway/app.py`](file:///Users/donthireddy/code/github/agentic-ai/llm_gateway/app.py) L353–358, [`llm_gateway/smart_router.py`](file:///Users/donthireddy/code/github/agentic-ai/llm_gateway/smart_router.py) L586–589  
- `RouteRequest` only accepts `prompt: str`, so all prior conversation turns are discarded
- Tool schemas are dropped even though `/v1/models` advertises `supports_tools: True`

### H5. SSE Transport Silently Ignored in Federation
**File:** [`ai_agent/federation.py`](file:///Users/donthireddy/code/github/agentic-ai/ai_agent/federation.py) — Lines 34–40  
- If `transport == "sse"`, nothing happens — no client created, no error raised
- Cumulative description mutation on repeated `refresh_tools_catalog()` calls (Line 68)
- Tool name collisions overwrite server mappings silently

### H6. OpenTelemetry Module Completely Orphaned
**File:** [`llm_gateway/telemetry_otel.py`](file:///Users/donthireddy/code/github/agentic-ai/llm_gateway/telemetry_otel.py) — Entire file  
- Never imported or used in runtime gateway code
- No `SpanProcessor` or `Exporter` attached — spans are generated and immediately dropped
- W3C trace IDs are non-standard format

### H7. Prometheus Endpoint Crashes Silently
**File:** [`llm_gateway/app.py`](file:///Users/donthireddy/code/github/agentic-ai/llm_gateway/app.py) — Line 686  
- `cost_tracker.get_cost_summary()` called without required `db_path` argument
- `TypeError` is swallowed, all cost metrics report `0.000000`

### H8. Unbounded Agent History — No Context Window Management
**File:** [`ai_agent/agent.py`](file:///Users/donthireddy/code/github/agentic-ai/ai_agent/agent.py) — Lines 267, 455, 552  
- `self.messages` grows indefinitely across turns with no sliding window, token budget, or truncation
- Long sessions inevitably exceed model context window limits
- `/compact` exists but is never auto-triggered

### H9. Broken Skill Renderers
**Files:** [`mcp_server/skills/code_review.py`](file:///Users/donthireddy/code/github/agentic-ai/mcp_server/skills/code_review.py) L12, [`mcp_server/skills/data_analysis.py`](file:///Users/donthireddy/code/github/agentic-ai/mcp_server/skills/data_analysis.py) L12, [`mcp_server/server.py`](file:///Users/donthireddy/code/github/agentic-ai/mcp_server/server.py) L669–706  
- Required parameters missing defaults → `TypeError` on `render_skill()`
- Parameter transposition: language assigned to `code_snippet`, monthly income to `investment_horizon`
- Skills reference non-existent tool name `execute_python` (registered as `python_sandbox`)

### H10. Docker Container Runs as Root
**File:** [`Dockerfile`](file:///Users/donthireddy/code/github/agentic-ai/Dockerfile)  
- No `USER` directive — FastAPI server, Python sandbox, and all tools run as `root`
- `build-essential` (gcc, make) left in production image, expanding attack surface

---

## 📈 MEDIUM Severity Findings

| # | Issue | File(s) | Summary |
|---|-------|---------|---------|
| M1 | **Pervasive silent `except: pass`** | `agent.py` (12+ locations) | DB errors, serialization failures, telemetry crashes silently swallowed |
| M2 | **Synchronous blocking I/O in async paths** | `router.py` L358, `logger.py` L111, `voice_endpoints.py` L37, `web_search_tools.py` | `urlopen`, SQLite writes, Whisper inference block the event loop |
| M3 | **Gateway client connection churn** | `gateway_client.py` L78–183 | New `httpx.AsyncClient` created and destroyed on every call — no connection pooling |
| M4 | **Rate limiter unbounded memory growth** | `rate_limiter.py` L67–91 | Per-caller bucket dicts never evict stale entries |
| M5 | **Compact splits tool call/response pairs** | `compact.py` L126–128 | Message slicing can orphan `tool` responses, causing LiteLLM HTTP 400 |
| M6 | **Double synthesis in orchestrator** | `orchestrator.py` (task_planner + _synthesize) | DAG includes a "synthesis" worker task AND supervisor runs a second synthesis pass |
| M7 | **Race condition on concurrent agent use** | `agent.py` L74, 161, 267 | `self._connected` and `self.messages` mutated without `asyncio.Lock` |
| M8 | **Upstream task output injection** | `orchestrator.py` L150–160 | Unsanitized upstream results concatenated directly into downstream prompts |
| M9 | **ChromaDB metadata serialization mismatch** | `memory_backend.py` L103–108 vs L135 | Nested dicts stored as JSON strings but not decoded on recall in ChromaDB backend |
| M10 | **`stdout` hijacking race condition** | `python_tool.py` L122, `math_tools.py` L212 | `sys.stdout` mutated globally without thread lock during concurrent sandbox calls |
| M11 | **Unpinned Python dependencies** | `requirements.txt` (all) | Every dep uses `>=` with no lockfile — builds are non-deterministic |
| M12 | **Missing `.env` in `.dockerignore`** | `.dockerignore` L28 | Secrets potentially baked into Docker image layers |
| M13 | **Zero router.py test coverage** | `mcp_server/tests/` | None of the 28 FastAPI REST endpoints in `mcp_server/router.py` are tested |
| M14 | **Duplicate line** | `agent.py` L434–435 | `assistant_msg["tool_calls"] = tool_calls` repeated twice |
| M15 | **Canned greeting on non-greeting failure** | `agent.py` L605 | If model exhausts iterations on "Analyze this SQL schema", returns "Hello! How can I help you?" |

---

## 🧪 Test Coverage Gaps

### Critical Paths With Zero Test Coverage

| Component | Untested Critical Path | Risk |
|-----------|----------------------|------|
| `agent.py` | `run()` — full ReAct loop execution | Core product functionality |
| `agent.py` | Raw JSON extraction from assistant text | Small model compatibility |
| `agent.py` | Consecutive duplicate loop breaking | Infinite loop prevention |
| `orchestrator.py` | `_execute_dag()` — parallel DAG evaluation | Multi-agent correctness |
| `orchestrator.py` | `_execute_worker()` — self-healing retries | Resilience claim |
| `app.py` | `stream=True` chat completions | Streaming feature |
| `app.py` | Firewall integration on completions | Security claim |
| `app.py` | Rate limiter integration on completions | Safety claim |
| `router.py` (MCP) | All 28 REST endpoints | API contract |
| `federation.py` | `connect_all()`, `execute_tool()` | Federation feature |
| `debate.py` | Multi-round debates (`rounds >= 2`) | Debate revision logic |
| `memory_backend.py` | `ChromaMemoryBackend` | Vector memory feature |
| `cost_tracker.py` | Production `cost_usd` write path | Cost tracking claim |

### Tests That Mask Production Bugs

| Test File | What It Masks |
|-----------|--------------|
| `test_cost_tracker.py` | Manually inserts `cost_usd: 0.0075` — never written by `save_log_entry` in production |
| `test_domain_skills.py` | Passes arguments matching broken signatures, hiding `TypeError` crashes |
| `test_observability.py` | Checks Prometheus metric text presence, doesn't detect `get_cost_summary` TypeError |

---

## 🏗️ Infrastructure & DevOps Assessment

| Area | Status | Notes |
|------|--------|-------|
| **CI/CD** | ❌ None | No `.github/workflows/`, Jenkinsfile, or any CI pipeline |
| **Pre-commit hooks** | ❌ None | No `.pre-commit-config.yaml` |
| **Python linting** | ❌ None | No ruff, flake8, black, or isort configuration |
| **JS linting** | ❌ None | No ESLint or Prettier in `webui/` |
| **Type checking** | ⚠️ Minimal | `pyrightconfig.json` exists but doesn't enable strict mode |
| **Dependency locking** | ❌ None | No `uv.lock`, `poetry.lock`, or `requirements.lock` |
| **Docker security** | 🚨 Root | No non-root user; `build-essential` in production image |
| **Secrets management** | ⚠️ Partial | `.gitignore` excludes `.env`, but `.dockerignore` doesn't |
| **Local DX** | 🌟 Excellent | `restart.sh` is 398 lines of polished orchestration |

---

## 🌟 What's Genuinely Excellent

Despite the critical gaps, the project has remarkable strengths that deserve recognition:

1. **📖 Documentation is world-class** — 5,200-line `BUILD_YOUR_OWN_AGENTIC_AI.md` with 5-pillar explanations, Mermaid diagrams, case studies, and FAQ is better than most commercial products
2. **🧠 Architectural design patterns are correct** — WAL checkpoints, Tool-RAG, dual-backend memory, HITL registry design, multi-provider gateway abstraction, AST code validation
3. **🎨 WebUI is polished** — 13-tab React Spectrum studio with glassmorphism dark theme, real-time SSE streaming, drag-and-drop canvas, interactive approval hub
4. **🔄 Zero-dependency fallbacks** — ChromaDB → SQLite, NetworkX → BFS, cloud → Ollama — consistent design philosophy
5. **🧪 Test isolation** — `conftest.py` redirects all SQLite to `tmp_path` preventing test pollution — excellent pattern
6. **🛠️ `restart.sh`** — 398 lines handling PID management, port cleanup, venv bootstrapping, Docker mount collision repair, health polling, and comprehensive CLI dashboard output
7. **🎯 Tool-RAG concept** — Dynamically scoping tool schemas to reduce context bloat is a genuinely novel and valuable pattern
8. **📊 4-Grader eval framework** — Deterministic + Efficiency + LLM-Judge + Fact-Checker with variance averaging is architecturally sound

---

## 📐 Score Breakdown & Justification

### Pillar 1: Security & Sandboxing — 6/20

| What Works | What Doesn't |
|------------|-------------|
| AST validation in `python_tool.py` | RCE via `__import__` in separate `math_tools.py` |
| PII regex patterns defined | Firewall never called on actual completions |
| Prompt injection regex defined | Rate limiter never called on actual completions |
| HITL rules defined | `@requires_approval` doesn't intercept execution |
| Path traversal check exists | Uses `.startswith()` instead of `.is_relative_to()` |
| | Zero authentication on all endpoints |
| | CORS `*` with credentials |
| | Docker runs as root |

### Pillar 2: Core Agent Logic — 10/15

| What Works | What Doesn't |
|------------|-------------|
| ReAct loop with iteration bounds | No SSE streaming (module orphaned) |
| Dual tool calling (native + JSON fallback) | Unbounded message history |
| Tool-RAG semantic scoping | Oscillating tool loop bypass |
| SHA-256 idempotency cache | Potential `IndexError` in idempotency path |
| Skill activation & progressive disclosure | Silent failures on DB/serialization errors |
| Session hydration from SQLite | Race conditions on concurrent use |

### Pillar 3: Multi-Agent Orchestration — 6/10

| What Works | What Doesn't |
|------------|-------------|
| LLM-powered task decomposition | Deadlock bug in adaptive self-healing |
| Semaphore-bounded parallel workers | Race condition on `_current_run_id` |
| Self-healing retry with error reflection | Double synthesis redundancy |
| SQLite node checkpointing | Unsanitized upstream task injection |
| Worker resource cleanup (`finally: close()`) | |

### Pillar 4: LLM Gateway & Routing — 6/10

| What Works | What Doesn't |
|------------|-------------|
| Multi-provider abstraction via LiteLLM | Streaming crashes (`AttributeError`) |
| Model alias resolution & normalization | Smart router drops conversation history |
| Smart router 2-stage design | Smart router drops tool schemas |
| Provider-specific kwargs construction | Blocking `urlopen` in async path |
| SSE audit log broadcasting | Missing Azure/Bedrock provider branches |

### Pillar 5: Memory & Knowledge — 6/8

| What Works | What Doesn't |
|------------|-------------|
| ChromaDB + SQLite fallback design | SQLite connection leaks (no context managers) |
| GraphRAG with NetworkX + BFS fallback | ChromaDB metadata serialization mismatch |
| Namespace-scoped memory isolation | 200-item hard recall limit in SQLite |
| WAL mode + busy timeout in SQLite | Case sensitivity mismatch in BFS vs SQL |

### Pillar 6: Observability & Audit — 4/10

| What Works | What Doesn't |
|------------|-------------|
| 3-tier audit trail design (Conversation→Turn→Request) | Cost permanently $0.00 (column never populated) |
| SSE real-time log broadcasting | Prometheus endpoint TypeError crash |
| JSONL append-only backup log | OTel module completely orphaned |
| Detailed request metadata capture | Synchronous disk I/O in async logger |
| | Full prompts logged in plaintext (PII leak) |

### Pillar 7: Human-in-the-Loop Safety — 4/8

| What Works | What Doesn't |
|------------|-------------|
| HITLRegistry design with rules & policies | `@requires_approval` doesn't wrap functions |
| Durable polling with restart hydration | HITL checks not called before tool execution |
| WebUI Approvals Hub with countdown timers | Unauthenticated approve/deny endpoints |
| Timeout auto-deny mechanism | Multi-process `asyncio.Event` desync |

### Pillar 8: Testing & Quality — 5/10

| What Works | What Doesn't |
|------------|-------------|
| 294 passing tests, 1 skipped | `agent.run()` has zero tests |
| Excellent `conftest.py` test isolation | DAG execution has zero tests |
| Good tool unit test coverage for basic tools | `router.py` (MCP) has zero tests |
| Reasonable breadth across modules | Tests that mask production bugs |
| | Zero CI/CD automation |
| | No linting or formatting enforcement |

### Pillar 9: Infrastructure & Deployment — 5/9

| What Works | What Doesn't |
|------------|-------------|
| Multi-stage Docker build | Runs as root |
| Excellent `restart.sh` (398 lines) | Unpinned Python deps, no lockfiles |
| Dual topology (dev + Docker production) | `.env` not in `.dockerignore` |
| `.env.example` well-documented | `smart_router_config.json` missing from image |
| Health check in Dockerfile | `build-essential` not pruned from production |

### Pillar 10: Documentation & UX — 9/10

| What Works | What Doesn't |
|------------|-------------|
| 5,200-line comprehensive guide | Only 6 eval benchmark test cases |
| 5-pillar feature explanations | |
| Mermaid architecture diagrams | |
| 3 detailed enterprise case studies | |
| Polished 13-tab WebUI | |
| React Spectrum + glassmorphism theme | |
| 25 frontend Vitest tests | |

---

## 🎯 Prioritized Remediation Roadmap

### Phase 1: Security Critical (Days 1–3)
1. **Remove `__import__` from `math_tools.py`** or deprecate `execute_python_code` in favor of `python_tool.py`
2. **Wire firewall into `chat_completions()`** — call `inspect_prompt_safety()` on inbound and `sanitize_tool_output()` on tool results
3. **Wire rate limiter into `chat_completions()`** — call `check_request()` before LiteLLM dispatch
4. **Add Bearer token auth middleware** on all `/api/*` and `/v1/*` routes
5. **Fix path traversal** — replace `.startswith()` with `.is_relative_to()` everywhere
6. **Enforce sandbox timeout** — use `concurrent.futures.ProcessPoolExecutor` with strict timeout kills
7. **Fix CORS** — restrict `allow_origins` to explicit hosts, remove `allow_credentials=True` with wildcard
8. **Harden `db_tools.py`** — enforce `mode=ro`, restrict `db_path` to workspace, remove `PRAGMA`

### Phase 2: Correctness (Days 4–7)
9. **Fix orchestrator deadlock** — update `get_ready_tasks()` to treat failed dependencies as resolved
10. **Fix streaming** — integrate `streaming.py` into `app.py:chat_completions()`
11. **Fix cost tracking** — populate `cost_usd` in `save_log_entry()`, fix `get_cost_summary()` argument
12. **Wire HITL interception** — make `@requires_approval` actually wrap and block function execution
13. **Fix debate arbitrator** — pass final revised proposal, all rounds, and compute real confidence score
14. **Fix skill renderers** — add missing default parameters, correct argument mappings in `server.py`

### Phase 3: Quality & Operations (Days 8–14)
15. **Add CI/CD** — GitHub Actions running pytest, npm test, Docker build, and trivy scan
16. **Pin dependencies** — generate `uv.lock` or compiled `requirements.lock`
17. **Harden Docker** — add non-root user, prune `build-essential`, add `.env` to `.dockerignore`
18. **Add missing tests** — `agent.run()`, DAG execution, `router.py` endpoints, ChromaDB backend
19. **Add linting** — ruff for Python, ESLint for JS, pre-commit hooks
20. **Expand eval dataset** — from 6 to 50+ test cases across edge cases and failure modes

---

> **Bottom Line:** The *architecture and design intent* of this project is genuinely excellent — the patterns are correct, the documentation is extraordinary, and the feature breadth is remarkable. The gap is between **design** and **integration**: security modules exist but aren't wired in, rate limiting exists but isn't called, HITL exists but doesn't intercept, cost tracking exists but writes $0.00. Closing that gap moves this from a strong prototype to a genuine enterprise reference architecture.
