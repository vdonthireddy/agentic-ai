import re
import base64
import unicodedata
from typing import Dict, Any, List, Tuple

class SecurityFirewall:
    """Detects prompt injection attempts, sanitizes tainted tool data, and masks PII in flight with bi-directional restoration."""

    # PII Regex Patterns
    SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")
    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
    PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
    API_KEY_PATTERN = re.compile(r"\b(?:sk-[a-zA-Z0-9]{20,}|AIza[0-9A-Za-z-_]{35}|ghp_[a-zA-Z0-9]{36})\b")

    # Prompt Injection & Jailbreak Signatures
    INJECTION_PATTERNS = [
        re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions", re.I),
        re.compile(r"system\s+prompt\s+override", re.I),
        re.compile(r"you\s+are\s+now\s+in\s+(?:developer|dan|god|unrestricted|jailbreak)\s+mode", re.I),
        re.compile(r"disregard\s+(?:all\s+)?safety\s+guidelines", re.I),
        re.compile(r"reveal\s+your\s+(?:system\s+prompt|hidden\s+instructions|master\s+key|initial\s+prompt)", re.I),
        re.compile(r"print\s+(?:all\s+)?(?:system\s+instructions|hidden\s+prompts)", re.I),
        re.compile(r"exfiltrate\s+database\s+credentials", re.I),
        re.compile(r"<\s*\|\s*im_start\s*\|\s*>\s*system", re.I),
        re.compile(r"\[\s*INST\s*\]\s*<<\s*SYS\s*>>", re.I),
        re.compile(r"<\s*system\s*>\s*(?:you\s+are|override)", re.I),
    ]

    BASE64_CANDIDATE_PATTERN = re.compile(r"(?:[A-Za-z0-9+/]{4}){6,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?")

    def __init__(self, enabled: bool = True, block_injections: bool = True):
        self.enabled = enabled
        self.block_injections = block_injections

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Strip zero-width characters and normalize unicode for consistent scanning."""
        if not text:
            return ""
        # Remove zero-width chars and soft hyphens
        zero_widths = ['\u200b', '\u200c', '\u200d', '\ufeff', '\u00ad']
        clean = text
        for zw in zero_widths:
            clean = clean.replace(zw, '')
        return unicodedata.normalize('NFKD', clean)

    def inspect_prompt_safety(self, text: str) -> Dict[str, Any]:
        """Check for adversarial prompt injection signatures with normalization and payload decoding."""
        if not self.enabled or not self.block_injections or not text:
            return {"safe": True, "blocked": False, "flags": [], "risk_score": 0.0}

        normalized = self._normalize_text(text)
        flags = []

        # 1. Direct regex pattern scan
        for pattern in self.INJECTION_PATTERNS:
            match = pattern.search(normalized)
            if match:
                flags.append(f"Prompt injection pattern detected: '{match.group(0)}'")

        # 2. Check for hidden base64 encoded injection attempts
        for b64_match in self.BASE64_CANDIDATE_PATTERN.finditer(normalized):
            cand = b64_match.group(0)
            try:
                decoded = base64.b64decode(cand, validate=True).decode('utf-8', errors='ignore')
                for pattern in self.INJECTION_PATTERNS:
                    if pattern.search(decoded):
                        flags.append(f"Encoded prompt injection detected in payload: '{cand[:20]}...'")
                        break
            except Exception:
                pass

        risk_score = min(1.0, len(flags) * 0.5) if flags else 0.0

        return {
            "safe": len(flags) == 0,
            "blocked": len(flags) > 0,
            "flags": flags,
            "risk_score": risk_score
        }

    def sanitize_tool_output(self, text: str, source: str = "tool") -> str:
        """
        Sanitize untrusted external data (e.g. web search results, scraped pages, external files)
        by neutralizing prompt injection delimiters and wrapping with clear provenance boundaries.
        """
        if not self.enabled or not text:
            return text

        sanitized = text
        # Neutralize markdown instruction triggers and system tags in external tool text
        sanitized = re.sub(r"<\s*\|\s*im_start\s*\|\s*>", "[NEUTRALIZED_TAG]", sanitized, flags=re.I)
        sanitized = re.sub(r"\[\s*INST\s*\]", "[NEUTRALIZED_INST]", sanitized, flags=re.I)
        sanitized = re.sub(r"<\s*system\s*>", "[NEUTRALIZED_SYSTEM]", sanitized, flags=re.I)

        return f"<<<UNTRUSTED_EXTERNAL_DATA source=\"{source}\">>>\n{sanitized}\n<<</UNTRUSTED_EXTERNAL_DATA>>>"

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
