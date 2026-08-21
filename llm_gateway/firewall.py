"""
PII Masking & Real-Time Prompt Injection Firewall (llm_gateway/firewall.py).
Protects external model calls by redacting sensitive data and intercepting adversarial prompt injections.
"""

import re
from typing import Dict, Any, List, Tuple

class SecurityFirewall:
    """Detects prompt injection attempts and masks PII in flight with bi-directional restoration."""

    # PII Regex Patterns
    SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")
    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
    PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
    API_KEY_PATTERN = re.compile(r"\b(?:sk-[a-zA-Z0-9]{20,}|AIza[0-9A-Za-z-_]{35}|ghp_[a-zA-Z0-9]{36})\b")

    # Prompt Injection & Jailbreak Signatures
    INJECTION_PATTERNS = [
        re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions", re.I),
        re.compile(r"system\s+prompt\s+override", re.I),
        re.compile(r"you\s+are\s+now\s+in\s+(?:developer|dan|god)\s+mode", re.I),
        re.compile(r"disregard\s+(?:all\s+)?safety\s+guidelines", re.I),
        re.compile(r"reveal\s+your\s+(?:system\s+prompt|hidden\s+instructions|master\s+key)", re.I),
        re.compile(r"exfiltrate\s+database\s+credentials", re.I),
    ]

    def __init__(self, enabled: bool = True, block_injections: bool = True):
        self.enabled = enabled
        self.block_injections = block_injections

    def inspect_prompt_safety(self, text: str) -> Dict[str, Any]:
        """Check for adversarial prompt injection signatures."""
        if not self.enabled or not self.block_injections:
            return {"safe": True, "flags": []}

        flags = []
        for pattern in self.INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                flags.append(f"Prompt injection pattern detected: '{match.group(0)}'")

        return {
            "safe": len(flags) == 0,
            "blocked": len(flags) > 0,
            "flags": flags
        }

    def redact_pii(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Redacts PII tokens in text with placeholders and returns the mapping for subsequent restoration.
        """
        if not self.enabled or not text:
            return text, {}

        redaction_map = {}
        redacted_text = text

        # 1. API Keys
        for i, match in enumerate(self.API_KEY_PATTERN.finditer(text)):
            val = match.group(0)
            token = f"[REDACTED_API_KEY_{i+1}]"
            redaction_map[token] = val
            redacted_text = redacted_text.replace(val, token)

        # 2. SSN
        for i, match in enumerate(self.SSN_PATTERN.finditer(redacted_text)):
            val = match.group(0)
            token = f"[REDACTED_SSN_{i+1}]"
            redaction_map[token] = val
            redacted_text = redacted_text.replace(val, token)

        # 3. Credit Cards
        for i, match in enumerate(self.CREDIT_CARD_PATTERN.finditer(redacted_text)):
            val = match.group(0)
            token = f"[REDACTED_CC_{i+1}]"
            redaction_map[token] = val
            redacted_text = redacted_text.replace(val, token)

        # 4. Emails
        for i, match in enumerate(self.EMAIL_PATTERN.finditer(redacted_text)):
            val = match.group(0)
            token = f"[REDACTED_EMAIL_{i+1}]"
            redaction_map[token] = val
            redacted_text = redacted_text.replace(val, token)

        # 5. Phone Numbers
        for i, match in enumerate(self.PHONE_PATTERN.finditer(redacted_text)):
            val = match.group(0)
            token = f"[REDACTED_PHONE_{i+1}]"
            redaction_map[token] = val
            redacted_text = redacted_text.replace(val, token)

        return redacted_text, redaction_map

    def restore_pii(self, text: str, redaction_map: Dict[str, str]) -> str:
        """Restores original PII values back into the output text for authorized local user display."""
        if not text or not redaction_map:
            return text
        restored = text
        for token, original in redaction_map.items():
            restored = restored.replace(token, original)
        return restored

# Global singleton
firewall = SecurityFirewall()
