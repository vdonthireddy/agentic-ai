"""
Smart Router Engine for LLM Gateway.
Implements two-stage dynamic routing:
1. Reason: Calls default reasoning model to analyze the user prompt, categorize intent,
   evaluate confidence against category accuracy thresholds, and select the optimal model.
2. Execute: Dispatches prompt to the selected target model.
3. Trace: Records full end-to-end call log with prompts, reasoning output, decisions, target response, latencies, and tokens.
"""

import os
import re
import json
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query, Request

import litellm

from llm_gateway.config import config as global_config, GatewayConfig, resolve_ollama_base
from llm_gateway.router import resolve_model_name, build_litellm_kwargs, get_available_models
from llm_gateway.logger import audit_logger, logger
from llm_gateway.db import (
    save_smart_router_log,
    query_smart_router_logs,
    get_smart_router_log,
    clear_smart_router_logs,
    save_gateway_setting,
    get_gateway_settings
)


class CategoryConfig(BaseModel):
    name: str
    description: str
    accuracy_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    target_model: str
    fallback_model: Optional[str] = None


class SmartRouterConfig(BaseModel):
    enabled: bool = True
    default_reasoning_model: str = "ollama/llama3.2:latest"
    fallback_model: str = "ollama/mistral:latest"
    categories: Dict[str, CategoryConfig] = Field(default_factory=dict)


DEFAULT_CATEGORIES = {
    "coding": CategoryConfig(
        name="Coding & Software Engineering",
        description="Code generation, debugging, refactoring, algorithms, SQL queries, scripting, software design, unit tests",
        accuracy_threshold=0.75,
        target_model="ollama/qwen2.5-coder:7b",
        fallback_model="ollama/mistral:latest"
    ),
    "complex_work": {
        "name": "Complex Reasoning & Analysis",
        "description": "Multi-step logical reasoning, math proofs, deep technical evaluation, architecture trade-offs, analytical problem solving",
        "accuracy_threshold": 0.80,
        "target_model": "ollama/mistral:latest",
        "fallback_model": "ollama/qwen2.5-coder:7b"
    },
    "general_qa": {
        "name": "General Knowledge & QA",
        "description": "General question answering, broad world knowledge, explanations, conversational inquiries, conceptual overviews",
        "accuracy_threshold": 0.70,
        "target_model": "ollama/llama3.2:latest",
        "fallback_model": "ollama/mistral:latest"
    },
    "fast_lightweight": {
        "name": "Fast & Lightweight Tasks",
        "description": "Quick greetings, short text summaries, basic grammar/formatting, simple translations, low-latency lookups",
        "accuracy_threshold": 0.60,
        "target_model": "ollama/gemma2:2b",
        "fallback_model": "ollama/llama3.2:latest"
    },
    "creative_writing": {
        "name": "Creative & Nuanced Writing",
        "description": "Storytelling, brainstorming, creative ideation, copywriting, narrative prose, poetry, creative roleplay",
        "accuracy_threshold": 0.70,
        "target_model": "ollama/llama3.2:latest",
        "fallback_model": "ollama/mistral:latest"
    }
}


class RouteRequest(BaseModel):
    prompt: str
    reasoning_model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None
    turn_id: Optional[str] = None
    request_id: Optional[str] = None


class RoutingDecision(BaseModel):
    category: str
    confidence: float
    threshold: float
    threshold_met: bool
    selected_model: str
    target_model: str
    reasoning: str
    prompt_for_model: str


class SmartRouter:
    """Smart dynamic router managing category thresholds, reasoning-based dispatch, and execution tracing."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or global_config.smart_router_config_path
        self._load_config()

    def _load_config(self):
        """Loads configuration from JSON file or initializes defaults."""
        raw_cats = {}
        for k, v in DEFAULT_CATEGORIES.items():
            if isinstance(v, CategoryConfig):
                raw_cats[k] = v
            elif isinstance(v, dict):
                raw_cats[k] = CategoryConfig(**v)

        self.config = SmartRouterConfig(
            enabled=global_config.smart_router_enabled,
            default_reasoning_model=global_config.smart_router_default_model,
            fallback_model=global_config.fallback_model,
            categories=raw_cats
        )

        # 1. Try reading from persistent SQLite settings first
        try:
            settings = get_gateway_settings(global_config.db_path)
            if "smart_router_config" in settings:
                saved = json.loads(settings["smart_router_config"])
                self._apply_dict_config(saved)
                return
        except Exception as e:
            logger.debug(f"Could not load smart router config from db: {e}")

        # 2. Try reading from JSON config file
        if self.config_path and Path(self.config_path).exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._apply_dict_config(data)
            except Exception as e:
                logger.warning(f"Failed to read smart_router_config.json: {e}")

    def _apply_dict_config(self, data: Dict[str, Any]):
        if "use_smart_routing" in data:
            self.config.enabled = bool(data["use_smart_routing"])
        elif "enabled" in data:
            self.config.enabled = bool(data["enabled"])
        if "default_reasoning_model" in data and data["default_reasoning_model"]:
            self.config.default_reasoning_model = data["default_reasoning_model"]
        if "fallback_model" in data and data["fallback_model"]:
            self.config.fallback_model = data["fallback_model"]
        if "categories" in data and isinstance(data["categories"], dict):
            for cat_id, cat_data in data["categories"].items():
                if isinstance(cat_data, dict):
                    self.config.categories[cat_id] = CategoryConfig(
                        name=cat_data.get("name", cat_id),
                        description=cat_data.get("description", ""),
                        accuracy_threshold=float(cat_data.get("accuracy_threshold", 0.70)),
                        target_model=cat_data.get("target_model", "ollama/llama3.2:latest"),
                        fallback_model=cat_data.get("fallback_model")
                    )

    def save_config(self, new_data: Dict[str, Any]) -> Dict[str, Any]:
        """Updates configuration in memory, persists to JSON file and SQLite."""
        self._apply_dict_config(new_data)
        global_config.smart_router_enabled = self.config.enabled
        global_config.use_smart_routing = self.config.enabled

        # Persist to SQLite
        try:
            dumped = self.config.model_dump()
            save_gateway_setting("smart_router_config", json.dumps(dumped), global_config.db_path)
            save_gateway_setting("smart_router_enabled", str(self.config.enabled).lower(), global_config.db_path)
            if "default_reasoning_model" in new_data:
                save_gateway_setting("smart_router_default_model", str(new_data["default_reasoning_model"]), global_config.db_path)
        except Exception as e:
            logger.error(f"Failed to persist smart router config to DB: {e}")

        # Persist to JSON config file
        try:
            if self.config_path:
                Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(self.config.model_dump(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write smart_router_config.json: {e}")

        return self.get_config_dict()

    def get_config_dict(self) -> Dict[str, Any]:
        """Returns the serialized configuration dictionary."""
        available_models = [m["id"] for m in get_available_models(global_config)]
        return {
            "enabled": self.config.enabled,
            "use_smart_routing": self.config.enabled,
            "default_reasoning_model": self.config.default_reasoning_model,
            "fallback_model": self.config.fallback_model,
            "categories": {k: v.model_dump() for k, v in self.config.categories.items()},
            "available_models": available_models
        }

    def _normalize_model_name(self, model_candidate: str) -> str:
        """Resolves fuzzy model names to valid registered provider/model IDs."""
        if not model_candidate:
            return self.config.fallback_model

        s = model_candidate.strip()

        # Check if already an exact known registered model ID
        try:
            available_ids = [m["id"] for m in get_available_models(global_config)]
            if s in available_ids:
                return s
        except Exception:
            pass

        # Extract model name without provider prefix to prevent 'ollama' matching substring 'llama'
        name_only = s.split("/")[-1].lower()

        if "gemma" in name_only:
            return "ollama/gemma2:2b"
        if "qwen" in name_only or "coder" in name_only:
            return "ollama/qwen2.5-coder:7b"
        if "mistral" in name_only:
            return "ollama/mistral:latest"
        if "llama" in name_only or "3.2" in name_only:
            return "ollama/llama3.2:latest"

        return resolve_model_name(s, self.config.default_reasoning_model)

    def _heuristic_classify(self, prompt: str) -> Dict[str, Any]:
        """
        Production Portability & Zero-Dependency Graceful Fallback:
        Deterministic heuristic classification when reasoning model is offline or parsing fails.
        """
        p_lower = prompt.lower()

        # Coding triggers
        code_patterns = [
            r"\b(python|javascript|typescript|c\+\+|java|rust|html|css|sql|bash|regex)\b",
            r"\b(function|def |class |async |await |return |import |const |let |var )\b",
            r"\b(algorithm|refactor|debug|compile|syntax|endpoint|api|git|docker)\b",
            r"```",
            r"\b(write a script|write code|unit test|fix the bug)\b"
        ]
        if any(re.search(pat, p_lower) for pat in code_patterns):
            cat = "coding"
            cat_cfg = self.config.categories.get(cat) or DEFAULT_CATEGORIES["coding"]
            return {
                "category": cat,
                "confidence": 0.92,
                "selected_model": cat_cfg.target_model if isinstance(cat_cfg, CategoryConfig) else cat_cfg["target_model"],
                "reasoning": "Detected programming language constructs, code syntax, or software engineering keywords.",
                "prompt_for_model": prompt
            }

        # Creative Writing triggers
        creative_patterns = [
            r"\b(write a story|story|poem|poetic|poetry|fiction|novel|dialogue|creative|brainstorm ideas|metaphor)\b"
        ]
        if any(re.search(pat, p_lower) for pat in creative_patterns):
            cat = "creative_writing"
            cat_cfg = self.config.categories.get(cat) or DEFAULT_CATEGORIES["creative_writing"]
            return {
                "category": cat,
                "confidence": 0.85,
                "selected_model": cat_cfg.target_model if isinstance(cat_cfg, CategoryConfig) else cat_cfg["target_model"],
                "reasoning": "Query asks for imaginative storytelling, creative prose, poetry, or ideation.",
                "prompt_for_model": prompt
            }

        # Complex Work / Reasoning triggers
        complex_patterns = [
            r"\b(trade-offs|tradeoffs|architecture|architectural|microservices|distributed|consensus)\b",
            r"\b(proof|theorem|mathematical|logic puzzle|multi-step|evaluate|compare and contrast)\b",
            r"\b(in-depth|deep dive|comprehensive analysis|design a system)\b"
        ]
        if any(re.search(pat, p_lower) for pat in complex_patterns):
            cat = "complex_work"
            cat_cfg = self.config.categories.get(cat) or DEFAULT_CATEGORIES["complex_work"]
            return {
                "category": cat,
                "confidence": 0.86,
                "selected_model": cat_cfg.target_model if isinstance(cat_cfg, CategoryConfig) else cat_cfg["target_model"],
                "reasoning": "Query involves architectural trade-offs, multi-step logical deduction, or deep technical analysis.",
                "prompt_for_model": prompt
            }

        # Fast / Lightweight triggers (brief greetings, simple translation requests)
        short_words = len(prompt.split())
        fast_patterns = [
            r"^(hi|hello|hey|good morning|good evening|thanks|thank you|bye|ok|okay)[.!?]?$",
            r"\b(translate|french|spanish|german|japanese)\b"
        ]
        if (short_words <= 3 and not prompt.endswith("?") and not any(q in p_lower for q in ["what", "why", "who", "where", "how"])) or any(re.search(pat, p_lower) for pat in fast_patterns):
            cat = "fast_lightweight"
            cat_cfg = self.config.categories.get(cat) or DEFAULT_CATEGORIES["fast_lightweight"]
            return {
                "category": cat,
                "confidence": 0.88,
                "selected_model": cat_cfg.target_model if isinstance(cat_cfg, CategoryConfig) else cat_cfg["target_model"],
                "reasoning": "Query is concise, a routine greeting, simple translation, or requires low-latency lightweight processing.",
                "prompt_for_model": prompt
            }

        # Default: General QA
        cat = "general_qa"
        cat_cfg = self.config.categories.get(cat) or DEFAULT_CATEGORIES["general_qa"]
        return {
            "category": cat,
            "confidence": 0.80,
            "selected_model": cat_cfg.target_model if isinstance(cat_cfg, CategoryConfig) else cat_cfg["target_model"],
            "reasoning": "Query is informational general knowledge, conceptual inquiry, or conversational QA.",
            "prompt_for_model": prompt
        }

    def _parse_reasoning_output(self, raw_output: str, prompt: str) -> Dict[str, Any]:
        """Extracts and validates JSON decision from reasoning model response."""
        parsed = None

        # Clean markdown code blocks if present
        clean_text = raw_output.strip()
        if "```json" in clean_text:
            match = re.search(r"```json\s*(.*?)\s*```", clean_text, re.DOTALL)
            if match:
                clean_text = match.group(1).strip()
        elif "```" in clean_text:
            match = re.search(r"```\s*(.*?)\s*```", clean_text, re.DOTALL)
            if match:
                clean_text = match.group(1).strip()

        # Try direct JSON parse
        try:
            parsed = json.loads(clean_text)
        except Exception:
            # Try finding outermost braces
            start = clean_text.find("{")
            end = clean_text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    parsed = json.loads(clean_text[start:end+1])
                except Exception:
                    pass

            # Auto-repair truncated JSON (e.g. unclosed quotes or missing closing brace)
            if not parsed and start != -1:
                snippet = clean_text[start:]
                for suffix in ['"}', '}', '"\n}', '\n}']:
                    try:
                        parsed = json.loads(snippet + suffix)
                        break
                    except Exception:
                        pass

            # Robust regex extraction if JSON was cut off mid-stream
            if not parsed:
                cat_match = re.search(r'"category"\s*:\s*"([^"]+)"', clean_text, re.IGNORECASE)
                model_match = re.search(r'"(?:selected_model|model)"\s*:\s*"([^"]+)"', clean_text, re.IGNORECASE)
                conf_match = re.search(r'"confidence"\s*:\s*([0-9.]+)', clean_text)
                reason_match = re.search(r'"reasoning"\s*:\s*"((?:[^"\\]|\\.)*)', clean_text)
                prompt_match = re.search(r'"prompt_for_model"\s*:\s*"((?:[^"\\]|\\.)*)', clean_text)

                if cat_match or model_match:
                    parsed = {
                        "category": cat_match.group(1) if cat_match else "general_qa",
                        "confidence": float(conf_match.group(1)) if conf_match else 0.85,
                        "selected_model": model_match.group(1) if model_match else "",
                        "reasoning": reason_match.group(1).replace('\\"', '"') if reason_match else "Model selected based on task domain requirements.",
                        "prompt_for_model": prompt_match.group(1).replace('\\"', '"') if prompt_match else prompt
                    }

        if not parsed or not isinstance(parsed, dict):
            # Graceful heuristic fallback
            fallback = self._heuristic_classify(prompt)
            fallback["reasoning"] = f"(Heuristic fallback - model returned non-JSON text): {clean_text[:120]}..."
            return fallback

        category = str(parsed.get("category", "general_qa")).strip().lower()
        if category not in self.config.categories:
            category = "general_qa"

        try:
            confidence = float(parsed.get("confidence", 0.80))
            confidence = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            confidence = 0.80

        raw_model = parsed.get("selected_model") or parsed.get("model")
        selected_model = self._normalize_model_name(str(raw_model))

        reasoning = str(parsed.get("reasoning", "Model selected based on task domain requirements.")).strip()
        prompt_for_model = str(parsed.get("prompt_for_model") or prompt).strip()

        return {
            "category": category,
            "confidence": confidence,
            "selected_model": selected_model,
            "reasoning": reasoning,
            "prompt_for_model": prompt_for_model
        }

    async def route_and_execute(
        self,
        request: RouteRequest,
        gateway_config: Optional[GatewayConfig] = None
    ) -> Dict[str, Any]:
        """
        Full 2-Stage Smart Router Execution:
        Stage 1: Call Default Reasoning Model to determine optimal model route.
        Stage 2: Forward prompt to target model and generate final response.
        Persistence: Full call log with both prompts, responses, latencies, and decisions.
        """
        cfg = gateway_config or global_config
        trace_id = request.request_id or f"sr_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now(timezone.utc).isoformat()
        reasoning_model = resolve_model_name(
            request.reasoning_model or self.config.default_reasoning_model,
            self.config.default_reasoning_model
        )

        prompt = request.prompt.strip()
        stage1_start = time.time()

        if self.config.enabled:
            # Build Stage 1 Meta-Prompt
            categories_desc = "\n".join([
                f"- {cat_id}: {c.description} (Accuracy Threshold: {c.accuracy_threshold:.2f}, Recommended Target: {c.target_model})"
                for cat_id, c in self.config.categories.items()
            ])

            system_reasoning_prompt = (
                "You are an expert AI Model Router and Dispatcher.\n"
                "Your objective is to analyze the user's prompt, classify it into the single most appropriate task category, "
                "evaluate its accuracy/complexity requirements, and select the optimal model from the available models.\n\n"
                "Categories & Thresholds:\n"
                f"{categories_desc}\n\n"
                "Available Models:\n"
                "- ollama/qwen2.5-coder:7b: State-of-the-art coding, debugging, refactoring, SQL, scripting.\n"
                "- ollama/mistral:latest: Deep reasoning, architectural trade-offs, math logic, multi-step problem solving.\n"
                "- ollama/llama3.2:latest: Fast conversational QA, broad knowledge retrieval, creative writing, nuanced responses.\n"
                "- ollama/gemma2:2b: Ultra-fast lightweight model for greetings, simple translations, text formatting, quick lookups.\n\n"
                "Instructions:\n"
                "Respond ONLY with a JSON object in this exact schema (no preamble, no markdown, no other text):\n"
                "{\n"
                '  "category": "<one of: coding, complex_work, general_qa, fast_lightweight, creative_writing>",\n'
                '  "confidence": <float between 0.00 and 1.00 indicating confidence that the chosen model satisfies accuracy requirements>,\n'
                '  "selected_model": "<exact model ID from available models>",\n'
                '  "reasoning": "<1-3 concise sentences explaining why this model was chosen>",\n'
                '  "prompt_for_model": "<the prompt to send to this model, or leave as empty string \\\"\\\" to forward the original prompt unchanged>"\n'
                "}"
            )

            stage1_messages = [
                {"role": "system", "content": system_reasoning_prompt},
                {"role": "user", "content": f"User Prompt to Route:\n\"\"\"{prompt}\"\"\""}
            ]

            # ----------------------------------------------------------------------
            # STAGE 1: Call Default Reasoning Model
            # ----------------------------------------------------------------------
            reasoning_raw_response = ""
            reasoning_tokens = 0
            error_msg = None

            try:
                litellm_kwargs = build_litellm_kwargs(
                    target_model=reasoning_model,
                    messages=stage1_messages,
                    config=cfg,
                    temperature=0.1,  # Low temperature for deterministic routing decision
                    max_tokens=800
                )
                stage1_resp = await litellm.acompletion(**litellm_kwargs)
                choice = stage1_resp.choices[0]
                reasoning_raw_response = getattr(choice.message, "content", "") or ""
                if hasattr(stage1_resp, "usage") and stage1_resp.usage:
                    reasoning_tokens = getattr(stage1_resp.usage, "total_tokens", 0)
            except Exception as e:
                logger.warning(f"SmartRouter Stage 1 reasoning call failed ({reasoning_model}): {e}. Using graceful fallback.")
                error_msg = f"Stage 1 fallback: {str(e)}"
                # Graceful fallback heuristic
                heuristic = self._heuristic_classify(prompt)
                reasoning_raw_response = json.dumps(heuristic)

            stage1_latency_ms = (time.time() - stage1_start) * 1000

            # Parse & Validate Decision
            parsed_decision = self._parse_reasoning_output(reasoning_raw_response, prompt)
            detected_cat = parsed_decision["category"]
            confidence = parsed_decision["confidence"]
            suggested_model = parsed_decision["selected_model"]
            rationale = parsed_decision["reasoning"]
            target_prompt = (parsed_decision.get("prompt_for_model") or "").strip()
            # If target_prompt is empty or was truncated into a fragment, use the full original prompt
            if not target_prompt or (len(target_prompt) < len(prompt) * 0.4 and len(prompt) > 40):
                target_prompt = prompt

            # Evaluate against Category Accuracy Threshold
            cat_config = self.config.categories.get(detected_cat)
            threshold = cat_config.accuracy_threshold if cat_config else 0.70
            threshold_met = confidence >= threshold

            # Apply Threshold Logic:
            # If confidence satisfies threshold -> route to model.
            # If confidence falls below threshold -> route to category fallback model or default model.
            actual_target_model = suggested_model
            if not threshold_met:
                fallback = (cat_config.fallback_model if cat_config else None) or self.config.fallback_model
                actual_target_model = fallback
                rationale += f" (Note: Confidence {confidence:.2f} was below category accuracy threshold {threshold:.2f}. Safely routed to fallback model {fallback})."

            # Final normalization
            actual_target_model = resolve_model_name(actual_target_model, self.config.fallback_model)

            routing_decision = {
                "category": detected_cat,
                "category_name": cat_config.name if cat_config else detected_cat,
                "confidence": round(confidence, 2),
                "threshold": round(threshold, 2),
                "threshold_met": threshold_met,
                "selected_model": suggested_model,
                "actual_routed_model": actual_target_model,
                "reasoning": rationale,
                "prompt_for_model": target_prompt
            }
        else:
            # ----------------------------------------------------------------------
            # SMART ROUTING DISABLED (USE_SMART_ROUTING=False)
            # Bypass Stage 1 reasoning and directly route to default or fallback model
            # ----------------------------------------------------------------------
            stage1_latency_ms = 0.0
            actual_target_model = resolve_model_name(
                self.config.fallback_model or cfg.default_model,
                cfg.default_model
            )
            detected_cat = "direct_bypass"
            confidence = 1.0
            threshold = 0.0
            threshold_met = True
            suggested_model = actual_target_model
            target_prompt = prompt
            reasoning_model = "bypassed (smart routing disabled)"
            rationale = "Smart routing is disabled (USE_SMART_ROUTING=False). Bypassed Stage 1 reasoning dispatch and directly executed on default model."
            reasoning_raw_response = json.dumps({
                "category": "direct_bypass",
                "confidence": 1.0,
                "selected_model": actual_target_model,
                "reasoning": rationale,
                "prompt_for_model": target_prompt
            })
            reasoning_tokens = 0
            routing_decision = {
                "category": detected_cat,
                "category_name": "Direct Bypass (USE_SMART_ROUTING=False)",
                "confidence": 1.0,
                "threshold": 0.0,
                "threshold_met": True,
                "selected_model": actual_target_model,
                "actual_routed_model": actual_target_model,
                "reasoning": rationale,
                "prompt_for_model": target_prompt
            }

        # ----------------------------------------------------------------------
        # STAGE 2: Call Selected Target Model
        # ----------------------------------------------------------------------
        stage2_start = time.time()
        target_response_content = ""
        prompt_tokens = 0
        completion_tokens = 0
        target_total_tokens = 0

        stage2_messages = []
        if request.system_prompt:
            stage2_messages.append({"role": "system", "content": request.system_prompt})
        stage2_messages.append({"role": "user", "content": target_prompt})

        try:
            target_kwargs = build_litellm_kwargs(
                target_model=actual_target_model,
                messages=stage2_messages,
                config=cfg,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            stage2_resp = await litellm.acompletion(**target_kwargs)
            choice2 = stage2_resp.choices[0]
            target_response_content = getattr(choice2.message, "content", "") or ""
            if hasattr(stage2_resp, "usage") and stage2_resp.usage:
                prompt_tokens = getattr(stage2_resp.usage, "prompt_tokens", 0)
                completion_tokens = getattr(stage2_resp.usage, "completion_tokens", 0)
                target_total_tokens = getattr(stage2_resp.usage, "total_tokens", prompt_tokens + completion_tokens)
        except Exception as e:
            logger.error(f"SmartRouter Stage 2 execution failed on target {actual_target_model}: {e}")
            stage2_latency_ms = (time.time() - stage2_start) * 1000
            total_latency_ms = (time.time() - stage1_start) * 1000
            error_details = f"Target model execution error ({actual_target_model}): {str(e)}"
            
            # Record failed trace
            trace_record = {
                "id": trace_id,
                "timestamp": timestamp,
                "prompt": prompt,
                "reasoning_model": reasoning_model,
                "reasoning_raw_response": reasoning_raw_response,
                "routing_decision": routing_decision,
                "category": detected_cat,
                "confidence": confidence,
                "threshold": threshold,
                "threshold_met": threshold_met,
                "selected_model": suggested_model,
                "target_model": actual_target_model,
                "target_prompt": target_prompt,
                "target_response": f"⚠️ Error communicating with model {actual_target_model}: {e}",
                "stage1_latency_ms": round(stage1_latency_ms, 2),
                "stage2_latency_ms": round(stage2_latency_ms, 2),
                "total_latency_ms": round(total_latency_ms, 2),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": reasoning_tokens + target_total_tokens,
                "status": "ERROR",
                "error_message": error_details
            }
            save_smart_router_log(trace_record, cfg.db_path)
            return {
                "success": False,
                "error": error_details,
                "trace": trace_record,
                "response": trace_record["target_response"]
            }

        stage2_latency_ms = (time.time() - stage2_start) * 1000
        total_latency_ms = (time.time() - stage1_start) * 1000
        combined_total_tokens = reasoning_tokens + target_total_tokens

        # ----------------------------------------------------------------------
        # STAGE 3: Full Call Log & Persistence
        # ----------------------------------------------------------------------
        trace_record = {
            "id": trace_id,
            "timestamp": timestamp,
            "prompt": prompt,
            "reasoning_model": reasoning_model,
            "reasoning_raw_response": reasoning_raw_response,
            "routing_decision": routing_decision,
            "category": detected_cat,
            "confidence": confidence,
            "threshold": threshold,
            "threshold_met": threshold_met,
            "selected_model": suggested_model,
            "target_model": actual_target_model,
            "target_prompt": target_prompt,
            "target_response": target_response_content,
            "stage1_latency_ms": round(stage1_latency_ms, 2),
            "stage2_latency_ms": round(stage2_latency_ms, 2),
            "total_latency_ms": round(total_latency_ms, 2),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": combined_total_tokens,
            "status": "SUCCESS",
            "error_message": None
        }

        # Persist to SQLite Smart Router table
        save_smart_router_log(trace_record, cfg.db_path)

        # Also log to main gateway audit logger for unified auditing
        audit_logger.log_call(
            caller_id=request.session_id or "smart_router_client",
            agent_name="SmartRouter",
            session_id=request.session_id or request.conversation_id or f"sr_{trace_id}",
            caller_context={"smart_router_trace_id": trace_id, "routing": routing_decision},
            model=actual_target_model,
            skill_names=["smart_routing"],
            tool_names=[],
            request_messages=stage2_messages,
            request_tools=None,
            request_params={"reasoning_model": reasoning_model, "category": detected_cat},
            response_content=target_response_content,
            response_tool_calls=[],
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=combined_total_tokens,
            latency_ms=total_latency_ms,
            status="SUCCESS",
            conversation_id=request.conversation_id,
            turn_id=request.turn_id,
            request_id=trace_id
        )

        return {
            "success": True,
            "response": target_response_content,
            "target_model": actual_target_model,
            "trace": trace_record
        }


# Singleton instance
smart_router = SmartRouter()


# ==============================================================================
# FastAPI APIRouter Endpoints for Smart Router
# ==============================================================================

router = APIRouter(prefix="/api/smart-router", tags=["Smart Router"])


@router.post("/route")
async def route_prompt_endpoint(req: RouteRequest):
    """
    Execute dynamic two-stage smart routing for a given user prompt.
    Returns the target model response and the full call trace.
    """
    res = await smart_router.route_and_execute(req)
    return res


@router.get("/config")
async def get_smart_router_config_endpoint():
    """Retrieve active Smart Router configuration, thresholds, and candidate models."""
    return smart_router.get_config_dict()


@router.post("/config")
async def update_smart_router_config_endpoint(payload: Dict[str, Any]):
    """Update and persist Smart Router configuration, thresholds, and model mappings."""
    return smart_router.save_config(payload)


@router.get("/logs")
async def get_smart_router_logs_endpoint(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    category: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """Retrieve paginated and filtered Smart Router execution traces."""
    return query_smart_router_logs(
        limit=limit,
        offset=offset,
        category=category,
        model=model,
        search=search,
        db_path=global_config.db_path
    )


@router.get("/logs/{log_id}")
async def get_single_smart_router_log_endpoint(log_id: str):
    """Retrieve full trace details for a single Smart Router invocation."""
    log = get_smart_router_log(log_id, db_path=global_config.db_path)
    if not log:
        raise HTTPException(status_code=404, detail="Smart router trace not found")
    return log


@router.delete("/logs")
async def clear_smart_router_logs_endpoint():
    """Clear all stored Smart Router traces."""
    count = clear_smart_router_logs(db_path=global_config.db_path)
    return {"deleted": count, "message": f"Successfully deleted {count} smart router logs"}

