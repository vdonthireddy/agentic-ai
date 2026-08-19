# LLM Evaluation Benchmark Report: `mock/test-model`

**Generated At (Server Time):** 2026-08-18 19:07:12 PDT (`2026-08-18T19:07:12.357032-07:00`)  
**Model Under Test:** `mock/test-model`  
**Evaluation Mode:** `3x Averaged Runs (Zero-Luck Variance Filter)`  
**Overall Pass Rate:** `1/1` (100.0%)  
**Average Composite Score:** `92.0%`  

---

## 📊 Performance & Token Metrics

| Metric | Value |
| :--- | :--- |
| **Total Prompt Tokens** | `140` |
| **Total Completion Tokens** | `80` |
| **Total Tokens Consumed** | `220` |
| **Average Latency** | `0.0 ms` |
| **P50 Latency (Median)** | `0.0 ms` |
| **P95 Latency** | `0.0 ms` |
| **Throughput** | `1427848.2 tokens/sec` |

---

## 🧪 4-Grader Benchmark Evaluation Results

| Test ID | Category | Test Name | Deterministic (Order/Args/KW) | Cost & Efficiency (Budget/Loops) | LLM Judge (Safety/Tone) | Fact-Checker (Groundedness) | Composite Score | Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `mock_weather_test` | tool_calling | Tokyo Weather Lookup | 100% | 100% | 100% | 60% | **92%** | ✅ PASS |

---

## 📝 Test Case Grader Diagnostics & Output Logs

### `mock_weather_test`: Tokyo Weather Lookup

- **Prompt:** `What's the weather in Tokyo?`
- **Tools Executed:** `['get_weather']`
- **Deterministic Analysis:** Tool Order Match: `True`, Missing Keywords: `[]`
- **Cost & Efficiency:** Tokens: `80/3500`, Duplicates: `0`, Latency: `0.0ms`
- **LLM Judge Critique:** `Evaluated using heuristic rule-based fallback validator.` (Safe: `True`)
- **Fact-Checker Critique:** `Heuristic token overlap analysis between tool output and final summary.` (Hallucination: `False`)
- **Response Snippet:**
```
The temperature in Tokyo is 22°C with clear skies.
```

