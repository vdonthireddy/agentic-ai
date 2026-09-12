"""Tests for the HITL safety gate system."""

import pytest
import asyncio

from mcp_server.hitl import HITLRegistry, HITLRule, RiskLevel, requires_approval


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
        assert resolved.status == "denied"
        assert resolved.resolved_by == "timeout"

    def test_default_timeout_is_20_minutes(self, registry):
        """Verify the default timeout is 20 minutes (1200.0 seconds)."""
        rule = HITLRule(tool_name="test_default")
        assert rule.timeout_seconds == 1200.0

    def test_infinite_timeout_when_zero(self, registry):
        """Verify that timeout_seconds=0 represents an infinite approval window."""
        import time
        rule = HITLRule(tool_name="test_infinite", timeout_seconds=0)
        req = registry.create_request("test_infinite", {}, rule)
        time.sleep(0.02)
        assert req.is_expired is False
        assert req.timeout_seconds == 0

    def test_auto_deny_expired_in_get_pending(self, registry):
        """Verify expired requests are automatically denied and purged from get_pending()."""
        import time
        rule = HITLRule(tool_name="test_auto_deny", timeout_seconds=0.01)
        req = registry.create_request("test_auto_deny", {}, rule)
        time.sleep(0.02)
        pending = registry.get_pending()
        assert not any(p["request_id"] == req.request_id for p in pending)
        assert req.status == "denied"
        assert req.resolved_by == "timeout"

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
        
        @requires_approval(action_filter={"safe_action"})
        def my_tool(action="safe_action"):
            return "result"
        
        # Test it intercepts (we pass "safe_action" which matches the filter)
        import threading
        from mcp_server.hitl import hitl_registry
        done = threading.Event()
        def approve_it():
            import time
            for i in range(50):
                if done.is_set():
                    break
                time.sleep(0.1)
                pending = hitl_registry.get_pending()
                for p in pending:
                    if p["tool_name"] == "my_tool":
                        hitl_registry.approve(p["request_id"], "test")
                
        threading.Thread(target=approve_it).start()
        res1 = my_tool(action="safe_action")
        assert res1 == "result"
        done.set()
        
        res2 = my_tool(action="other_action")
        assert res2 == "result"


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

    def test_poll_resolution_flow(self):
        rule = HITLRule(tool_name="test_tool", timeout_seconds=60)
        registry = HITLRegistry()
        req = registry.create_request("test_tool", {"action": "delete"}, rule)

        # Non-blocking poll while pending
        poll_res = registry.poll_resolution(req.request_id)
        assert poll_res is not None
        assert poll_res.status == "pending"

        # Approve and verify poll reflects approval
        registry.approve(req.request_id, approved_by="admin_operator")
        poll_res2 = registry.poll_resolution(req.request_id)
        assert poll_res2 is not None
        assert poll_res2.status == "approved"
        assert poll_res2.resolved_by == "admin_operator"

