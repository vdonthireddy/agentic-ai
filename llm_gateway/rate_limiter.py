"""Token-bucket rate limiter for the LLM Gateway.

Provides per-caller and per-model rate limiting with configurable
requests-per-minute (RPM) and tokens-per-minute (TPM) limits.
"""

import os
import time
import asyncio
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class TokenBucket:
    """A simple token-bucket implementation for rate limiting."""
    capacity: float
    refill_rate: float  # tokens per second
    tokens: float = 0.0
    last_refill: float = field(default_factory=time.monotonic)

    def __post_init__(self):
        self.tokens = self.capacity

    def try_consume(self, amount: float = 1.0) -> Tuple[bool, float]:
        """Try to consume tokens. Returns (allowed, retry_after_seconds)."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= amount:
            self.tokens -= amount
            return True, 0.0
        else:
            deficit = amount - self.tokens
            retry_after = deficit / self.refill_rate if self.refill_rate > 0 else 60.0
            return False, retry_after


class RateLimiter:
    """Multi-dimensional rate limiter supporting per-caller and per-model limits.
    
    Configuration via environment variables:
    - RATE_LIMIT_RPM: Requests per minute per caller (default: 60)
    - RATE_LIMIT_TPM: Tokens per minute per caller (default: 100000)
    - RATE_LIMIT_GLOBAL_RPM: Global requests per minute (default: 300)
    - RATE_LIMIT_ENABLED: Set to "false" to disable (default: "true")
    """

    def __init__(
        self,
        rpm_per_caller: Optional[int] = None,
        tpm_per_caller: Optional[int] = None,
        global_rpm: Optional[int] = None,
        enabled: Optional[bool] = None
    ):
        self.enabled = enabled if enabled is not None else (
            os.environ.get("RATE_LIMIT_ENABLED", "true").lower() != "false"
        )
        self.rpm_per_caller = rpm_per_caller or int(os.environ.get("RATE_LIMIT_RPM", "60"))
        self.tpm_per_caller = tpm_per_caller or int(os.environ.get("RATE_LIMIT_TPM", "100000"))
        self.global_rpm = global_rpm or int(os.environ.get("RATE_LIMIT_GLOBAL_RPM", "300"))

        # Buckets: keyed by (dimension, identifier)
        self._request_buckets: Dict[str, TokenBucket] = {}
        self._token_buckets: Dict[str, TokenBucket] = {}
        self._global_bucket = TokenBucket(
            capacity=float(self.global_rpm),
            refill_rate=float(self.global_rpm) / 60.0
        )
        self._lock = asyncio.Lock()

    def _get_request_bucket(self, caller_id: str) -> TokenBucket:
        """Get or create the request-rate bucket for a caller."""
        if caller_id not in self._request_buckets:
            self._request_buckets[caller_id] = TokenBucket(
                capacity=float(self.rpm_per_caller),
                refill_rate=float(self.rpm_per_caller) / 60.0
            )
        return self._request_buckets[caller_id]

    def _get_token_bucket(self, caller_id: str) -> TokenBucket:
        """Get or create the token-rate bucket for a caller."""
        if caller_id not in self._token_buckets:
            self._token_buckets[caller_id] = TokenBucket(
                capacity=float(self.tpm_per_caller),
                refill_rate=float(self.tpm_per_caller) / 60.0
            )
        return self._token_buckets[caller_id]

    async def check_request(self, caller_id: str) -> Tuple[bool, float, str]:
        """Check if a request from the given caller is allowed.
        
        Returns:
            (allowed, retry_after_seconds, reason)
        """
        if not self.enabled:
            return True, 0.0, ""

        async with self._lock:
            # Check global rate limit
            allowed, retry_after = self._global_bucket.try_consume(1.0)
            if not allowed:
                return False, retry_after, "Global rate limit exceeded"

            # Check per-caller request rate limit
            caller_bucket = self._get_request_bucket(caller_id)
            allowed, retry_after = caller_bucket.try_consume(1.0)
            if not allowed:
                return False, retry_after, f"Per-caller request rate limit exceeded ({self.rpm_per_caller} RPM)"

        return True, 0.0, ""

    async def record_tokens(self, caller_id: str, token_count: int) -> Tuple[bool, float, str]:
        """Record token consumption and check if the caller exceeds token limits.
        
        This is called AFTER a successful completion to track token usage.
        Returns (within_limit, retry_after_seconds, reason).
        """
        if not self.enabled:
            return True, 0.0, ""

        async with self._lock:
            token_bucket = self._get_token_bucket(caller_id)
            allowed, retry_after = token_bucket.try_consume(float(token_count))
            if not allowed:
                return False, retry_after, f"Per-caller token rate limit exceeded ({self.tpm_per_caller} TPM)"

        return True, 0.0, ""

    def get_status(self, caller_id: Optional[str] = None) -> Dict:
        """Get current rate limiter status."""
        status = {
            "enabled": self.enabled,
            "global_rpm_limit": self.global_rpm,
            "per_caller_rpm_limit": self.rpm_per_caller,
            "per_caller_tpm_limit": self.tpm_per_caller,
            "global_remaining": round(self._global_bucket.tokens, 1),
        }
        if caller_id and caller_id in self._request_buckets:
            status["caller_request_remaining"] = round(self._request_buckets[caller_id].tokens, 1)
        if caller_id and caller_id in self._token_buckets:
            status["caller_token_remaining"] = round(self._token_buckets[caller_id].tokens, 1)
        return status

    def reset(self, caller_id: Optional[str] = None):
        """Reset rate limit buckets. If caller_id given, reset only that caller."""
        if caller_id:
            self._request_buckets.pop(caller_id, None)
            self._token_buckets.pop(caller_id, None)
        else:
            self._request_buckets.clear()
            self._token_buckets.clear()
            self._global_bucket = TokenBucket(
                capacity=float(self.global_rpm),
                refill_rate=float(self.global_rpm) / 60.0
            )


# Global singleton instance
rate_limiter = RateLimiter()
