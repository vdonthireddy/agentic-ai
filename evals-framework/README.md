# Evals Framework: LLM & Agent Benchmarking Suite

A modular, standalone evaluation framework designed to benchmark local LLMs (via Ollama & LiteLLM Gateway) across MCP tool calling, domain skill adherence, numerical correctness, and latency.

---

## 📂 Folder Structure

```
evals-framework/
├── runner.py                 # Core evaluation runner and benchmark engine
├── compare_models.py         # Multi-model comparative benchmark script
├── datasets/                 # Benchmark test suites & ground-truth assertions
│   ├── tool_calling_evals.json     # Arithmetic, Python execution, file ops, diagnostics, search
│   ├── skill_adherence_evals.json  # Data analyst & code reviewer skill compliance
│   └── reasoning_evals.json        # Multi-step reasoning and tool chaining
├── evaluators/               # Evaluation metric scorers
│   ├── tool_accuracy.py      # Tool selection precision/recall & argument schema validation
│   ├── skill_adherence.py    # Structured output section & criteria compliance
│   ├── correctness.py        # Ground-truth mathematical and logical verification
│   └── performance.py        # Latency (P50/P95), token usage, and throughput (tok/s)
├── reporters/                # Report generation
│   ├── console_reporter.py   # Rich terminal scorecards
│   └── markdown_reporter.py  # Markdown benchmark report generator
├── reports/                  # Generated benchmark reports (.md)
├── pyproject.toml
└── requirements.txt
```

---

## 🚀 Quick Start

### 1. Run Evaluation Suite on a Model
```bash
# From workspace root:
./scripts/run_evals.sh ollama/qwen2.5-coder:7b

# Or run directly inside evals-framework:
python evals-framework/runner.py --model ollama/qwen2.5-coder:7b
```

### 2. Compare Multiple Models Head-to-Head
```bash
python evals-framework/compare_models.py --models ollama/qwen2.5-coder:7b ollama/llama3.2
```

### 3. Generated Reports
Benchmark reports with detailed token breakdowns, P50/P95 latencies, and tool execution logs are automatically written to `evals-framework/reports/`.
