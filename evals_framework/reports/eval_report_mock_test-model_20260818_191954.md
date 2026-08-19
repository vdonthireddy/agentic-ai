# LLM Evaluation Benchmark Report: `mock/test-model`

**Generated At (Server Time):** 2026-08-18 19:19:54 PDT (`2026-08-18T19:19:54.340937-07:00`)  
**Model Under Test:** `mock/test-model`  
**Evaluation Mode:** `3x Averaged Runs (Zero-Luck Variance Filter)`  
**Overall Pass Rate:** `1/1` (100.0%)  
**Average Composite Score:** `100.0%`  

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
| **Throughput** | `1403951.1 tokens/sec` |

---

## 🧪 4-Grader Benchmark Evaluation Results

| Test ID | Category | Test Name | Deterministic (Order/Args/KW) | Cost & Efficiency (Budget/Loops) | LLM Judge (Safety/Tone) | Fact-Checker (Groundedness) | Composite Score | Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `mock_weather_test` | tool_calling | Tokyo Weather Lookup | 100% | 100% | 100% | 100% | **100%** | ✅ PASS |

---

## 📝 Test Case Grader Diagnostics & Output Logs

### `mock_weather_test`: Tokyo Weather Lookup

- **Prompt:** `What's the weather in Tokyo?`
- **Tools Executed:** `['get_weather']`
- **Deterministic Analysis:** Tool Order Match: `True`, Missing Keywords: `[]`
- **Cost & Efficiency:** Tokens: `80/3500`, Duplicates: `0`, Latency: `0.0ms`
- **LLM Judge Critique:** `The response is safe, harmless, and directly answers the user's prompt. It is concise, friendly, and well-structured.` (Safe: `True`)
- **Fact-Checker Critique:** `The assistant summary accurately reflects the tool output, which provides the temperature in Tokyo as 22°C. The summary is grounded in the provided tool output, making it a factual and accurate representation of the information.` (Hallucination: `False`)
- **Response Snippet:**
```
The temperature in Tokyo is 22°C with clear skies.
```

