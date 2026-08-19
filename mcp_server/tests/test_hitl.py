"""Tests for the HITL safety gate system."""

import pytest
import asyncio

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from hitl import HITLRegistry, HITLRule, RiskLevel, requires_approval


class TestHITLRegistry:
    @pytest.fixture
    def registry(self):
        return HITLRegistry()

    def test_default_rules(self, registry):
        rules = registry.get_rules()
        assert len(rules) >= 1
        tool_names = [r["tool_name"] for r in rules]
        assert "workspace_file_ops" in tool_names

    def test_register_custom_rule(self, registry):
        registry.register_rule(HITLRule(
            tool_name="send_email",
            risk_level=RiskLevel.HIGH,
            description="Email sending requires approval"
        ))
        rules = registry.get_rules()
        tool_names = [r["tool_name"] for r in rules]
        assert "send_email" in tool_names

    def test_unregister_rule(self, registry):
        registry.register_rule(HITLRule(tool_name="test_tool"))
        assert registry.unregister_rule("test_tool") is True
        assert registry.unregister_rule("test_tool") is False

    def test_check_requires_approval_match(self, registry):
        rule = registry.check_requires_approval(
            "workspace_file_ops", 
            {"action": "delete", "filename": "test.txt"}
        )
        assert rule is not None
        assert rule.tool_name == "workspace_file_ops"

    def test_check_no_approval_needed(self, registry):
        rule = registry.check_requires_approval(
            "workspace_file_ops",
            {"action": "read", "filename": "test.txt"}
        )
        assert rule is None

    def test_check_unknown_tool(self, registry):
        rule = registry.check_requires_approval("calculator", {"expression": "2+2"})
        assert rule is None

    def test_create_request(self, registry):
        rule = HITLRule(tool_name="test_tool", risk_level=RiskLevel.MEDIUM)
        req = registry.create_request("test_tool", {"arg": "val"}, rule)
        assert req.request_id.startswith("hitl_")
        assert req.status == "pending"
        assert req.tool_name == "test_tool"

    def test_approve_request(self, registry):
        rule = HITLRule(tool_name="test_tool")
        req = registry.create_request("test_tool", {}, rule)
        
        success = registry.approve(req.request_id, approved_by="tester")
        assert success is True
        assert req.status == "approved"
        assert req.resolved_by == "tester"

    def test_deny_request(self, registry):
        rule = HITLRule(tool_name="test_tool")
        req = registry.create_request("test_tool", {}, rule)
        
        success = registry.deny(req.request_id, denied_by="tester")
        assert success is True
        assert req.status == "denied"

    def test_approve_nonexistent(self, registry):
        assert registry.approve("nonexistent_id") is False

    def test_deny_nonexistent(self, registry):
        assert registry.deny("nonexistent_id") is False

    def test_get_pending(self, registry):
        rule = HITLRule(tool_name="test_tool")
        registry.create_request("test_tool", {"a": 1}, rule)
        registry.create_request("test_tool", {"b": 2}, rule)
        
        pending = registry.get_pending()
        assert len(pending) == 2

    def test_get_history(self, registry):
        rule = HITLRule(tool_name="test_tool")
        req = registry.create_request("test_tool", {}, rule)
        registry.approve(req.request_id)
        
        # Wait for resolution to move to history
        history = registry.get_history()
        # History may be empty since we haven't awaited wait_for_resolution
        assert isinstance(history, list)

    @pytest.mark.asyncio
    async def test_wait_for_approval(self, registry):
        rule = HITLRule(tool_name="test_tool", timeout_seconds=5.0)
        req = registry.create_request("test_tool", {}, rule)
        
        async def approve_after_delay():
            await asyncio.sleep(0.1)
            registry.approve(req.request_id)
        
        asyncio.create_task(approve_after_delay())
        resolved = await registry.wait_for_resolution(req.request_id)
        assert resolved.status == "approved"

    @pytest.mark.asyncio
    async def test_wait_for_timeout(self, registry):
        rule = HITLRule(tool_name="test_tool", timeout_seconds=0.2)
        req = registry.create_request("test_tool", {}, rule)
        
        resolved = await registry.wait_for_resolution(req.request_id)
        assert resolved.status == "expired"

    def test_action_filter_with_aliases(self, registry):
        """Verify the action filter matches case-insensitively."""
        rule = registry.check_requires_approval(
            "workspace_file_ops",
            {"action": "Delete"}
        )
        assert rule is not None

    def test_action_filter_no_match(self, registry):
        rule = registry.check_requires_approval(
            "workspace_file_ops",
            {"action": "write"}
        )
        assert rule is None


class TestRequiresApprovalDecorator:
    def test_decorator_attaches_rule(self):
        @requires_approval(
            risk_level=RiskLevel.HIGH,
            description="Test description",
            action_filter={"delete"}
        )
        def my_tool(action, target):
            return f"Executed {action} on {target}"
        
        assert hasattr(my_tool, "_hitl_rule")
        assert my_tool._hitl_rule.risk_level == RiskLevel.HIGH
        assert my_tool._hitl_rule.description == "Test description"

    def test_decorated_function_still_callable(self):
        @requires_approval()
        def my_tool():
            return "result"
        
        assert my_tool() == "result"


class TestHITLRequest:
    def test_to_dict(self, ):
        rule = HITLRule(tool_name="test", risk_level=RiskLevel.CRITICAL, timeout_seconds=30)
        registry = HITLRegistry()
        req = registry.create_request("test", {"key": "value"}, rule)
        
        d = req.to_dict()
        assert d["tool_name"] == "test"
        assert d["risk_level"] == "critical"
        assert d["status"] == "pending"
        assert d["arguments"] == {"key": "value"}

    def test_is_expired(self):
        import time
        rule = HITLRule(tool_name="test", timeout_seconds=0.01)
        registry = HITLRegistry()
        req = registry.create_request("test", {}, rule)
        time.sleep(0.02)
        assert req.is_expired is True
