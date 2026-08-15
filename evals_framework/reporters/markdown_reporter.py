"""Markdown report generation for LLM Evaluation results with 4 specialized graders."""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

def generate_markdown_report(
    model_name: str,
    test_results: List[Dict[str, Any]],
    performance_metrics: Dict[str, Any],
    output_dir: str = "./evals_framework/reports"
) -> str:
    """
    Saves a detailed markdown report of the evaluation run with 4 specialized grader scores.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    clean_model = model_name.replace("/", "_").replace(":", "_")
    filename = f"eval_report_{clean_model}_{timestamp}.md"
    file_path = out_path / filename

    total_tests = len(test_results)
    passed_tests = sum(1 for t in test_results if t.get("overall_passed"))
    pass_rate = round(passed_tests / total_tests * 100, 1) if total_tests else 0
    avg_score = round((sum(t.get("composite_score", 0.0) for t in test_results) / total_tests) * 100, 1) if total_tests else 0

    content = f"""# LLM Evaluation Benchmark Report: `{model_name}`

**Generated At:** {datetime.now(timezone.utc).isoformat()}  
**Model Under Test:** `{model_name}`  
**Overall Pass Rate:** `{passed_tests}/{total_tests}` ({pass_rate}%)  
**Average Composite Score:** `{avg_score}%`  

---

## 📊 Performance & Token Metrics

| Metric | Value |
| :--- | :--- |
| **Total Prompt Tokens** | `{performance_metrics.get('total_prompt_tokens', 0):,}` |
| **Total Completion Tokens** | `{performance_metrics.get('total_completion_tokens', 0):,}` |
| **Total Tokens Consumed** | `{performance_metrics.get('total_tokens', 0):,}` |
| **Average Latency** | `{performance_metrics.get('avg_latency_ms', 0):.1f} ms` |
| **P50 Latency (Median)** | `{performance_metrics.get('p50_latency_ms', 0):.1f} ms` |
| **P95 Latency** | `{performance_metrics.get('p95_latency_ms', 0):.1f} ms` |
| **Throughput** | `{performance_metrics.get('tokens_per_second', 0):.1f} tokens/sec` |

---

## 🧪 4-Grader Benchmark Evaluation Results

| Test ID | Category | Test Name | Deterministic (Order/Args/KW) | Cost & Efficiency (Budget/Loops) | LLM Judge (Safety/Tone) | Fact-Checker (Groundedness) | Composite Score | Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
"""

    for t in test_results:
        status = "✅ PASS" if t.get("overall_passed") else "❌ FAIL"
        det_score = int(t.get("deterministic_score", t.get("tool_score", 1.0)) * 100)
        eff_score = int(t.get("efficiency_score", 1.0) * 100)
        judge_score = int(t.get("judge_score", 1.0) * 100)
        fact_score = int(t.get("fact_check_score", t.get("correctness_score", 1.0)) * 100)
        comp_score = int(t.get("composite_score", 0.0) * 100)

        content += f"| `{t['id']}` | {t['category']} | {t['name']} | {det_score}% | {eff_score}% | {judge_score}% | {fact_score}% | **{comp_score}%** | {status} |\n"

    content += "\n---\n\n## 📝 Test Case Grader Diagnostics & Output Logs\n\n"

    for t in test_results:
        content += f"### `{t['id']}`: {t['name']}\n\n"
        content += f"- **Prompt:** `{t['prompt']}`\n"
        content += f"- **Tools Executed:** `{t.get('executed_tools', [])}`\n"
        
        if "deterministic_eval" in t:
            det_det = t["deterministic_eval"].get("details", {})
            content += f"- **Deterministic Analysis:** Tool Order Match: `{det_det.get('order_passed')}`, Missing Keywords: `{det_det.get('missing_keywords', [])}`\n"
        if "efficiency_eval" in t:
            eff_det = t["efficiency_eval"].get("details", {})
            content += f"- **Cost & Efficiency:** Tokens: `{eff_det.get('total_tokens_used')}/{eff_det.get('max_tokens_budget')}`, Duplicates: `{eff_det.get('duplicate_calls', 0)}`, Latency: `{eff_det.get('latency_ms')}ms`\n"
        if "judge_eval" in t:
            judge_det = t["judge_eval"].get("details", {})
            content += f"- **LLM Judge Critique:** `{judge_det.get('critique', '')}` (Safe: `{judge_det.get('safe', True)}`)\n"
        if "fact_check_eval" in t:
            fact_det = t["fact_check_eval"].get("details", {})
            content += f"- **Fact-Checker Critique:** `{fact_det.get('critique', '')}` (Hallucination: `{fact_det.get('hallucination_detected', False)}`)\n"

        content += f"- **Response Snippet:**\n```\n{t.get('response_snippet', '')}\n```\n\n"

    file_path.write_text(content, encoding="utf-8")
    return str(file_path)
