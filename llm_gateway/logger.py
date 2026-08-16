"""Audit logging engine for capturing and persisting LLM interactions."""

import json
import logging
import uuid
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path

from db import save_log_entry, init_db
from config import config

# Set up standard logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("llm_gateway")

class GatewayAuditLogger:
    """Manages audit logging to SQLite and structured JSONL."""
    
    def __init__(self, db_path: Path = config.db_path, json_log_path: Path = config.json_log_path):
        self.db_path = db_path
        self.json_log_path = json_log_path
        init_db(self.db_path)
        self.json_log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_call(
        self,
        caller_id: Optional[str],
        agent_name: Optional[str],
        session_id: Optional[str],
        caller_context: Optional[Dict[str, Any]],
        model: str,
        skill_names: List[str],
        tool_names: List[str],
        request_messages: List[Dict[str, Any]],
        request_tools: Optional[List[Dict[str, Any]]],
        request_params: Dict[str, Any],
        response_content: Optional[str],
        response_tool_calls: Optional[List[Dict[str, Any]]],
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        latency_ms: float,
        status: str = "SUCCESS",
        error_message: Optional[str] = None,
        conversation_id: Optional[str] = None,
        turn_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record a comprehensive 3-tier audit trail (Conversation -> Turn -> Request) of the interaction.
        """
        req_id = request_id or f"req_{uuid.uuid4().hex[:12]}"
        conv_id = conversation_id or session_id or (caller_context.get("conversation_id") if caller_context else None) or "conv_default"
        t_id = turn_id or (caller_context.get("turn_id") if caller_context else None) or f"turn_{req_id[:8]}"
        timestamp = datetime.now(timezone.utc).isoformat()

        record = {
            "id": req_id,
            "request_id": req_id,
            "turn_id": t_id,
            "conversation_id": conv_id,
            "session_id": conv_id,
            "timestamp": timestamp,
            "caller_id": caller_id or "anonymous",
            "agent_name": agent_name or "default_agent",
            "caller_context": caller_context or {},
            "model": model,
            "skill_names": skill_names or [],
            "tool_names": tool_names or [],
            "request_messages": request_messages,
            "request_tools": request_tools or [],
            "request_params": request_params,
            "response_content": response_content,
            "response_tool_calls": response_tool_calls or [],
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "latency_ms": round(latency_ms, 2),
            "status": status,
            "error_message": error_message
        }

        # 1. Save to SQLite
        try:
            save_log_entry(record, db_path=self.db_path)
        except Exception as e:
            logger.error(f"Failed to persist audit log to SQLite: {e}")

        # 2. Append to JSONL
        try:
            with open(self.json_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.error(f"Failed to append audit log to JSONL: {e}")

        # Log console summary
        logger.info(
            f" [LOGGED] Conv={conv_id} Turn={t_id} Req={req_id} Agent={record['agent_name']} "
            f"Model={model} Tokens=[Prompt:{prompt_tokens}, Comp:{completion_tokens}, Total:{total_tokens}] "
            f"Latency={round(latency_ms, 1)}ms Status={status}"
        )

        return record

audit_logger = GatewayAuditLogger()
