"""Historical Evaluation Runs and Side-by-Side Comparison Engine."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional


class HistoryEngine:
    """Manages historical benchmark reports and builds multi-run comparison matrices."""

    def __init__(self, reports_dir: Optional[Path] = None):
        self.reports_dir = reports_dir or Path(__file__).parent / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def list_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all historical benchmark runs ordered newest first."""
        runs = []
        for file in sorted(self.reports_dir.glob("eval_run_*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                total_t = data.get("total_tests", len(data.get("results", [])))
                passed_t = data.get("passed_tests", sum(1 for r in data.get("results", []) if r.get("passed") or r.get("overall_passed")))
                pass_rate = data.get("pass_rate_pct", data.get("pass_rate", round(passed_t / total_t * 100, 1) if total_t else 0.0))
                avg_score = data.get("average_score_pct", data.get("overall_score", 0.0))
                if not avg_score and data.get("results"):
                    avg_score = round(sum(r.get("composite_score", r.get("overall_score", 0.0)) for r in data["results"]) / len(data["results"]) * 100, 1)

                perf = data.get("performance_metrics") or data.get("performance", {})

                runs.append({
                    "run_id": data.get("run_id", file.stem.replace("eval_run_", "")),
                    "filename": file.name,
                    "timestamp": data.get("timestamp", ""),
                    "agent_id": data.get("agent_id", "mcp_default"),
                    "agent_name": data.get("agent_name", "Agent"),
                    "model": data.get("model", ""),
                    "judge_model": data.get("judge_model", ""),
                    "total_tests": total_t,
                    "passed_tests": passed_t,
                    "pass_rate_pct": pass_rate,
                    "pass_rate": pass_rate,
                    "average_score_pct": avg_score,
                    "overall_score": avg_score,
                    "avg_latency_ms": data.get("avg_latency_ms", perf.get("avg_latency_ms", 0.0)),
                    "total_tokens": data.get("total_tokens", perf.get("total_tokens", 0))
                })
                if len(runs) >= limit:
                    break
            except Exception:
                continue
        return runs

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full details of a specific historical run."""
        json_file = self.reports_dir / f"eval_run_{run_id}.json"
        if not json_file.exists():
            matching = list(self.reports_dir.glob(f"*{run_id}*.json"))
            if matching:
                json_file = matching[0]
            else:
                return None
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            # Ensure full responses are populated if missing or truncated to 300 chars
            for r in data.get("results", []):
                curr_resp = r.get("response") or ""
                snippet = r.get("response_snippet") or ""
                if (not curr_resp or len(curr_resp) <= 300) and len(snippet) > 20:
                    try:
                        from llm_gateway.config import DB_PATH
                        import sqlite3
                        if DB_PATH.exists():
                            conn = sqlite3.connect(str(DB_PATH))
                            cursor = conn.cursor()
                            prefix = snippet[:60]
                            cursor.execute(
                                "SELECT response_content FROM llm_logs WHERE response_content LIKE ? ORDER BY LENGTH(response_content) DESC LIMIT 1",
                                (prefix + "%",)
                            )
                            row = cursor.fetchone()
                            if row and row[0] and len(row[0]) > len(snippet):
                                r["response"] = row[0]
                                r["response_snippet"] = row[0]
                            conn.close()
                    except Exception:
                        pass
                elif curr_resp and not snippet:
                    r["response_snippet"] = curr_resp
            return data
        except Exception:
            return None

    def get_run_logs(self, run_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve granular request/response interaction logs for a given benchmark run.
        Provides a 3-tier fallback strategy:
        1. SQLite database `llm_logs`
        2. JSONL file `gateway_audit.jsonl`
        3. Evaluated test case results from the run report itself
        """
        clean_id = run_id.replace("eval_run_", "").replace(".json", "")
        logs: List[Dict[str, Any]] = []

        # 1. Primary: SQLite database
        try:
            from llm_gateway.config import DB_PATH
            import sqlite3
            if DB_PATH.exists():
                conn = sqlite3.connect(str(DB_PATH))
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM llm_logs WHERE conversation_id LIKE ? OR session_id LIKE ? ORDER BY timestamp ASC",
                    (f"%{clean_id}%", f"%{clean_id}%")
                )
                rows = cursor.fetchall()
                for r in rows:
                    row_dict = dict(r)
                    for field in ("request_messages", "request_tools", "request_params", "response_tool_calls", "caller_context", "skill_names", "tool_names"):
                        if row_dict.get(field) and isinstance(row_dict[field], str):
                            try:
                                row_dict[field] = json.loads(row_dict[field])
                            except Exception:
                                pass
                    logs.append(row_dict)
                conn.close()
        except Exception:
            pass

        # 2. Secondary: gateway_audit.jsonl fallback
        if not logs:
            audit_file = Path(__file__).resolve().parent.parent / "gateway_audit.jsonl"
            if audit_file.exists():
                try:
                    with open(audit_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if clean_id in line:
                                try:
                                    entry = json.loads(line)
                                    conv = str(entry.get("conversation_id", ""))
                                    sess = str(entry.get("session_id", ""))
                                    if clean_id in conv or clean_id in sess:
                                        logs.append(entry)
                                except Exception:
                                    pass
                except Exception:
                    pass

        # 3. Tertiary: Synthesize from eval run report results if audit logs are unavailable/archived
        if not logs:
            run_data = self.get_run(clean_id)
            if run_data and "results" in run_data:
                for res in run_data["results"]:
                    runs_list = res.get("iteration_runs") or [res]
                    for it_run in runs_list:
                        prompt_text = it_run.get("prompt") or res.get("prompt", "")
                        resp_text = it_run.get("response") or res.get("response_snippet", "")
                        tools_exec = it_run.get("tool_calls_executed") or []
                        logs.append({
                            "id": it_run.get("turn_id", f"req_{res.get('id', 'test')}"),
                            "request_id": it_run.get("turn_id", f"req_{res.get('id', 'test')}"),
                            "turn_id": it_run.get("turn_id", ""),
                            "conversation_id": it_run.get("conversation_id", f"eval_{clean_id}"),
                            "session_id": it_run.get("session_id", f"eval_{clean_id}"),
                            "timestamp": run_data.get("timestamp", ""),
                            "caller_id": "evals_framework",
                            "agent_name": run_data.get("agent_name", "Evals Agent"),
                            "model": run_data.get("model", ""),
                            "request_messages": [{"role": "user", "content": prompt_text}],
                            "response_content": resp_text,
                            "response_tool_calls": tools_exec,
                            "prompt_tokens": it_run.get("total_prompt_tokens", res.get("total_prompt_tokens", 0)),
                            "completion_tokens": it_run.get("total_completion_tokens", res.get("total_completion_tokens", 0)),
                            "total_tokens": (it_run.get("total_prompt_tokens", res.get("total_prompt_tokens", 0)) +
                                            it_run.get("total_completion_tokens", res.get("total_completion_tokens", 0))),
                            "latency_ms": it_run.get("latency_ms", res.get("latency_ms", 0.0)),
                            "status": "SUCCESS" if (it_run.get("passed", res.get("passed", True))) else "FAILED",
                            "test_id": res.get("id"),
                            "test_name": res.get("name", res.get("id", "")),
                            "category": res.get("category", "general"),
                            "prompt": prompt_text,
                            "response": resp_text,
                            "tools_called": tools_exec,
                            "source": "report_fallback"
                        })

        return logs

    def compare_runs(self, run_ids: List[str]) -> Dict[str, Any]:
        """
        Build a side-by-side comparative matrix across multiple benchmark runs.
        Computes overall metrics, per-grader scores, latency/token efficiency, and per-test case comparisons.
        """
        runs_data = []
        for rid in run_ids:
            data = self.get_run(rid)
            if data:
                runs_data.append(data)

        if not runs_data:
            return {"error": "No valid runs found for specified run_ids", "runs": [], "matrix": [], "winner": None}

        # Build comparison summary cards
        summary = []
        winner = None
        max_score = -1.0

        for r in runs_data:
            total_t = r.get("total_tests", len(r.get("results", [])))
            passed_t = r.get("passed_tests", sum(1 for res in r.get("results", []) if res.get("passed") or res.get("overall_passed")))
            pass_rate = r.get("pass_rate_pct", r.get("pass_rate", round(passed_t / total_t * 100, 1) if total_t else 0.0))
            avg_score = r.get("average_score_pct", r.get("overall_score", 0.0))
            if not avg_score and r.get("results"):
                avg_score = round(sum(res.get("composite_score", res.get("overall_score", 0.0)) for res in r["results"]) / len(r["results"]) * 100, 1)
            
            perf = r.get("performance_metrics") or r.get("performance", {})

            run_card = {
                "run_id": r.get("run_id"),
                "timestamp": r.get("timestamp"),
                "agent_id": r.get("agent_id", "mcp_default"),
                "agent_name": r.get("agent_name", "Agent"),
                "model": r.get("model"),
                "judge_model": r.get("judge_model"),
                "total_tests": total_t,
                "passed_tests": passed_t,
                "pass_rate_pct": pass_rate,
                "pass_rate": pass_rate,
                "average_score_pct": avg_score,
                "overall_score": avg_score,
                "avg_latency_ms": r.get("avg_latency_ms", perf.get("avg_latency_ms", 0.0)),
                "total_tokens": r.get("total_tokens", perf.get("total_tokens", 0)),
                "graders": {
                    "deterministic": r.get("grader_averages", {}).get("deterministic", 0.0),
                    "efficiency": r.get("grader_averages", {}).get("efficiency", 0.0),
                    "llm_judge": r.get("grader_averages", {}).get("llm_judge", 0.0),
                    "fact_checker": r.get("grader_averages", {}).get("fact_checker", 0.0)
                }
            }
            summary.append(run_card)

            if avg_score > max_score:
                max_score = avg_score
                winner = run_card

        # Build per-test comparison matrix
        all_test_ids = []
        test_names_map = {}
        for r in runs_data:
            for item in r.get("results", []):
                tid = item.get("test_id", item.get("id"))
                if tid and tid not in all_test_ids:
                    all_test_ids.append(tid)
                    test_names_map[tid] = item.get("test_name", item.get("name", tid))

        matrix = []
        for tid in all_test_ids:
            row = {
                "test_id": tid,
                "test_name": test_names_map.get(tid, tid),
                "scores": {}
            }
            for r in runs_data:
                rid = r.get("run_id", "unknown")
                matching_res = next((res for res in r.get("results", []) if (res.get("test_id") == tid or res.get("id") == tid)), None)
                if matching_res:
                    row["scores"][rid] = {
                        "passed": matching_res.get("passed", True) or matching_res.get("overall_passed", True),
                        "overall_score": matching_res.get("composite_score", matching_res.get("overall_score", 0.0)),
                        "latency_ms": matching_res.get("latency_ms", 0.0),
                        "total_tokens": matching_res.get("total_prompt_tokens", 0) + matching_res.get("total_completion_tokens", 0)
                    }
                else:
                    row["scores"][rid] = None
            matrix.append(row)

        return {
            "runs": summary,
            "winner": winner,
            "matrix": matrix,
            "total_runs_compared": len(runs_data)
        }


# Global history engine instance
history_engine = HistoryEngine()
