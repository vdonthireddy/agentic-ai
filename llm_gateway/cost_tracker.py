"""Per-model cost tracking and forecasting for the LLM Gateway.

Calculates estimated costs based on token usage and a configurable
pricing table. Supports aggregation by caller, model, and time period.
"""

import json
import os
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta


# Default pricing table: cost per 1M tokens (input/output)
# Source: Published pricing as of mid-2026
DEFAULT_PRICING: Dict[str, Dict[str, float]] = {
    # OpenAI
    "openai/gpt-4o": {"input": 2.50, "output": 10.00},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "openai/o3-mini": {"input": 1.10, "output": 4.40},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    
    # Anthropic
    "anthropic/claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
    "anthropic/claude-3-haiku": {"input": 0.25, "output": 1.25},
    "claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    
    # Google Gemini
    "gemini/gemini-2.0-flash": {"input": 0.075, "output": 0.30},
    "gemini/gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    
    # Groq
    "groq/llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
    "groq/llama3-8b-8192": {"input": 0.05, "output": 0.08},
    
    # Mistral
    "mistral/mistral-large-latest": {"input": 2.00, "output": 6.00},
    "mistral/mistral-small-latest": {"input": 0.20, "output": 0.60},
    
    # DeepSeek
    "deepseek/deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek/deepseek-coder": {"input": 0.14, "output": 0.28},
}


class CostTracker:
    """Tracks per-request costs and provides aggregation and forecasting.
    
    Cost data is stored in the existing audit SQLite database via
    an added `cost_usd` column, and optionally in a separate cost
    aggregation table for fast lookups.
    """

    def __init__(self, pricing: Optional[Dict[str, Dict[str, float]]] = None):
        self.pricing = pricing or dict(DEFAULT_PRICING)
        
        # Load custom pricing from env var if set
        custom_path = os.environ.get("COST_PRICING_FILE")
        if custom_path and Path(custom_path).exists():
            try:
                with open(custom_path, "r") as f:
                    custom = json.load(f)
                self.pricing.update(custom)
            except Exception:
                pass

    def calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate the estimated USD cost for a single LLM call.
        
        Returns 0.0 for local Ollama models or unknown models.
        """
        # Local models are free
        if model.startswith("ollama/") or model.startswith("ollama_chat/"):
            return 0.0
        
        # Look up pricing (try exact match, then normalized key)
        pricing = self.pricing.get(model)
        if not pricing:
            # Try without provider prefix
            parts = model.split("/", 1)
            if len(parts) == 2:
                pricing = self.pricing.get(parts[1])
            if not pricing:
                # Try matching by prefix (e.g. "gpt-4o" matches "openai/gpt-4o")
                for key, val in self.pricing.items():
                    if model in key or key in model:
                        pricing = val
                        break
        
        if not pricing:
            return 0.0

        # Cost per 1M tokens
        input_cost = (prompt_tokens / 1_000_000) * pricing.get("input", 0.0)
        output_cost = (completion_tokens / 1_000_000) * pricing.get("output", 0.0)
        return round(input_cost + output_cost, 8)

    def get_cost_summary(self, db_path: Path) -> Dict[str, Any]:
        """Get aggregate cost breakdown from the audit database."""
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if cost_usd column exists
        cursor.execute("PRAGMA table_info(llm_logs)")
        columns = [col[1] for col in cursor.fetchall()]
        has_cost = "cost_usd" in columns
        
        if has_cost:
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(cost_usd), 0.0) as total_cost,
                    COUNT(*) as total_calls
                FROM llm_logs WHERE cost_usd > 0
            """)
            row = cursor.fetchone()
            total_cost = row[0]
            paid_calls = row[1]
            
            # Per-model breakdown
            cursor.execute("""
                SELECT model, 
                       SUM(cost_usd) as model_cost,
                       SUM(prompt_tokens) as model_prompt_tokens,
                       SUM(completion_tokens) as model_completion_tokens,
                       COUNT(*) as call_count
                FROM llm_logs 
                WHERE cost_usd > 0
                GROUP BY model
                ORDER BY model_cost DESC
            """)
            model_breakdown = [
                {
                    "model": r[0],
                    "cost_usd": round(r[1], 6),
                    "prompt_tokens": r[2],
                    "completion_tokens": r[3],
                    "call_count": r[4]
                }
                for r in cursor.fetchall()
            ]
            
            # Per-caller breakdown
            cursor.execute("""
                SELECT caller_id,
                       SUM(cost_usd) as caller_cost,
                       COUNT(*) as call_count
                FROM llm_logs 
                WHERE cost_usd > 0
                GROUP BY caller_id
                ORDER BY caller_cost DESC
            """)
            caller_breakdown = [
                {
                    "caller_id": r[0],
                    "cost_usd": round(r[1], 6),
                    "call_count": r[2]
                }
                for r in cursor.fetchall()
            ]
        else:
            # Fallback: compute costs on the fly from stored token counts
            cursor.execute("""
                SELECT model, 
                       SUM(prompt_tokens) as pt,
                       SUM(completion_tokens) as ct,
                       COUNT(*) as cnt
                FROM llm_logs
                GROUP BY model
            """)
            total_cost = 0.0
            paid_calls = 0
            model_breakdown = []
            for r in cursor.fetchall():
                cost = self.calculate_cost(r[0], r[1] or 0, r[2] or 0)
                if cost > 0:
                    paid_calls += r[3]
                total_cost += cost
                model_breakdown.append({
                    "model": r[0],
                    "cost_usd": round(cost, 6),
                    "prompt_tokens": r[1] or 0,
                    "completion_tokens": r[2] or 0,
                    "call_count": r[3]
                })
            model_breakdown.sort(key=lambda x: x["cost_usd"], reverse=True)
            caller_breakdown = []
        
        conn.close()
        
        return {
            "total_cost_usd": round(total_cost, 6),
            "paid_calls": paid_calls,
            "by_model": model_breakdown,
            "by_caller": caller_breakdown,
            "pricing_table_models": len(self.pricing)
        }

    def get_cost_forecast(self, db_path: Path, days_ahead: int = 30) -> Dict[str, Any]:
        """Forecast monthly cost based on recent usage patterns.
        
        Uses the last 7 days of data to project costs for the specified period.
        """
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        
        # Check for cost_usd column
        cursor.execute("PRAGMA table_info(llm_logs)")
        columns = [col[1] for col in cursor.fetchall()]
        has_cost = "cost_usd" in columns
        
        if has_cost:
            cursor.execute("""
                SELECT COALESCE(SUM(cost_usd), 0.0), COUNT(*)
                FROM llm_logs
                WHERE timestamp >= ? AND cost_usd > 0
            """, (seven_days_ago,))
            row = cursor.fetchone()
            recent_cost = row[0]
            recent_calls = row[1]
        else:
            cursor.execute("""
                SELECT model, SUM(prompt_tokens), SUM(completion_tokens), COUNT(*)
                FROM llm_logs
                WHERE timestamp >= ?
                GROUP BY model
            """, (seven_days_ago,))
            recent_cost = 0.0
            recent_calls = 0
            for r in cursor.fetchall():
                recent_cost += self.calculate_cost(r[0], r[1] or 0, r[2] or 0)
                recent_calls += r[3]
        
        conn.close()
        
        daily_rate = recent_cost / 7.0 if recent_cost > 0 else 0.0
        projected = daily_rate * days_ahead
        
        return {
            "lookback_days": 7,
            "recent_cost_usd": round(recent_cost, 6),
            "recent_calls": recent_calls,
            "daily_average_usd": round(daily_rate, 6),
            "projected_days": days_ahead,
            "projected_cost_usd": round(projected, 6)
        }

    def get_pricing_table(self) -> Dict[str, Dict[str, float]]:
        """Return the current pricing table."""
        return dict(self.pricing)

    def update_pricing(self, model: str, input_per_1m: float, output_per_1m: float):
        """Update pricing for a specific model."""
        self.pricing[model] = {"input": input_per_1m, "output": output_per_1m}


# Global singleton instance
cost_tracker = CostTracker()
