"""Tests for the token-bucket rate limiter."""

import pytest
import asyncio
import time

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rate_limiter import TokenBucket, RateLimiter


class TestTokenBucket:
    def test_initial_capacity(self):
        bucket = TokenBucket(capacity=10.0, refill_rate=1.0)
        assert bucket.tokens == 10.0

    def test_consume_success(self):
        bucket = TokenBucket(capacity=10.0, refill_rate=1.0)
        allowed, retry = bucket.try_consume(1.0)
        assert allowed is True
        assert retry == 0.0

    def test_consume_exhaustion(self):
        bucket = TokenBucket(capacity=2.0, refill_rate=0.1)
        bucket.try_consume(2.0)
        allowed, retry = bucket.try_consume(1.0)
        assert allowed is False
        assert retry > 0.0

    def test_refill(self):
        bucket = TokenBucket(capacity=5.0, refill_rate=100.0)
        bucket.try_consume(5.0)
        time.sleep(0.05)
        allowed, _ = bucket.try_consume(1.0)
        assert allowed is True

    def test_no_exceed_capacity(self):
        bucket = TokenBucket(capacity=5.0, refill_rate=100.0)
        time.sleep(0.1)
        bucket.try_consume(0)  # Trigger refill
        assert bucket.tokens <= 5.0


class TestRateLimiter:
    @pytest.fixture
    def limiter(self):
        return RateLimiter(rpm_per_caller=5, tpm_per_caller=1000, global_rpm=20, enabled=True)

    @pytest.mark.asyncio
    async def test_basic_allow(self, limiter):
        allowed, retry, reason = await limiter.check_request("user1")
        assert allowed is True
        assert reason == ""

    @pytest.mark.asyncio
    async def test_per_caller_limit(self, limiter):
        # Exhaust per-caller limit
        for _ in range(5):
            await limiter.check_request("user1")
        
        allowed, retry, reason = await limiter.check_request("user1")
        assert allowed is False
        assert "Per-caller" in reason

    @pytest.mark.asyncio
    async def test_different_callers_independent(self, limiter):
        for _ in range(5):
            await limiter.check_request("user1")
        
        # Different caller should still be allowed
        allowed, _, _ = await limiter.check_request("user2")
        assert allowed is True

    @pytest.mark.asyncio
    async def test_disabled_limiter(self):
        limiter = RateLimiter(enabled=False)
        for _ in range(100):
            allowed, _, _ = await limiter.check_request("user1")
            assert allowed is True

    @pytest.mark.asyncio
    async def test_token_tracking(self, limiter):
        allowed, _, _ = await limiter.record_tokens("user1", 500)
        assert allowed is True
        
        allowed, _, reason = await limiter.record_tokens("user1", 600)
        assert allowed is False
        assert "token" in reason.lower()

    def test_get_status(self, limiter):
        status = limiter.get_status()
        assert status["enabled"] is True
        assert status["global_rpm_limit"] == 20
        assert status["per_caller_rpm_limit"] == 5

    def test_reset(self, limiter):
        limiter.reset()
        status = limiter.get_status("user1")
        assert "caller_request_remaining" not in status

    @pytest.mark.asyncio
    async def test_global_limit(self):
        limiter = RateLimiter(rpm_per_caller=100, global_rpm=3, enabled=True)
        for _ in range(3):
            await limiter.check_request("user1")
        
        allowed, _, reason = await limiter.check_request("user2")
        assert allowed is False
        assert "Global" in reason
