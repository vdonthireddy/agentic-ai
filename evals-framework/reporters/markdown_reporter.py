"""Markdown report generation for LLM Evaluation results."""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

def generate_markdown_report(
    model_name: str,
    test_results: List[Dict[str, Any]],
    performance_metrics: Dict[str, Any],
    output_dir: str = "./evals-framework/reports"
) -> str:
    """
    Saves a detailed markdown report of the evaluation run.
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
| **Total Prompt Tokens** | `{performance_metrics.get('total_prompt_tokens', 0)}` |
| **Total Completion Tokens** | `{performance_metrics.get('total_completion_tokens', 0)}` |
| **Total Tokens Consumed** | `{performance_metrics.get('total_tokens', 0)}` |
| **Average Latency** | `{performance_metrics.get('avg_latency_ms', 0)} ms` |
| **P50 Latency (Median)** | `{performance_metrics.get('p50_latency_ms', 0)} ms` |
| **P95 Latency** | `{performance_metrics.get('p95_latency_ms', 0)} ms` |
| **Throughput** | `{performance_metrics.get('tokens_per_second', 0)} tokens/sec` |

---

## 🧪 Detailed Benchmark Test Results

| Test ID | Category | Test Name | Tool Accuracy | Skill Adherence | Correctness | Composite Score | Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
"""

    for t in test_results:
        status = "✅ PASS" if t.get("overall_passed") else "❌ FAIL"
        content += f"| `{t['id']}` | {t['category']} | {t['name']} | {int(t.get('tool_score', 1.0)*100)}% | {int(t.get('skill_score', 1.0)*100)}% | {int(t.get('correctness_score', 1.0)*100)}% | **{int(t.get('composite_score', 0.0)*100)}%** | {status} |\n"

    content += "\n---\n\n## 📝 Test Case Output Logs\n\n"

    for t in test_results:
        content += f"### `{t['id']}`: {t['name']}\n\n"
        content += f"- **Prompt:** `{t['prompt']}`\n"
        content += f"- **Tools Executed:** `{t.get('executed_tools', [])}`\n"
        content += f"- **Response Snippet:**\n```\n{t.get('response_snippet', '')}\n```\n\n"

    file_path.write_text(content, encoding="utf-8")
    return str(file_path)
