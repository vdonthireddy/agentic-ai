"""Human-in-the-Loop (HITL) Safety Gate system for the MCP Server.

Provides a registry of tools/actions that require human approval before
execution, along with models for tracking pending approvals and a
decorator for marking tools as HITL-protected.
"""

import time
import uuid
import asyncio
from typing import Dict, Any, List, Optional, Set, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class HITLRule:
    """Defines when a tool requires human approval."""
    tool_name: str
    risk_level: RiskLevel = RiskLevel.MEDIUM
    description: str = ""
    # If action_filter is set, only require approval when the action arg matches
    action_filter: Optional[Set[str]] = None
    # Timeout in seconds before auto-denying (0 = no timeout)
    timeout_seconds: float = 60.0


@dataclass
class HITLRequest:
    """A pending approval request waiting for human review."""
    request_id: str
    tool_name: str
    arguments: Dict[str, Any]
    risk_level: RiskLevel
    description: str
    created_at: float
    timeout_seconds: float
    status: str = "pending"  # pending, approved, denied, expired
    resolved_at: Optional[float] = None
    resolved_by: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        if self.timeout_seconds <= 0:
            return False
        return (time.time() - self.created_at) > self.timeout_seconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "risk_level": self.risk_level.value,
            "description": self.description,
            "created_at": self.created_at,
            "timeout_seconds": self.timeout_seconds,
            "status": self.status,
            "is_expired": self.is_expired,
            "resolved_at": self.resolved_at,
            "resolved_by": self.resolved_by
        }


class HITLRegistry:
    """Registry of HITL-protected tools and pending approval requests.
    
    Maintains a set of rules defining which tools/actions require
    human approval, and manages the lifecycle of approval requests.
    """

    def __init__(self):
        self._rules: Dict[str, HITLRule] = {}
        self._pending: Dict[str, HITLRequest] = {}
        self._history: List[HITLRequest] = []
        self._approval_events: Dict[str, asyncio.Event] = {}
        self._setup_defaults()

    def _setup_defaults(self):
        """Register default HITL rules for known dangerous operations."""
        self.register_rule(HITLRule(
            tool_name="workspace_file_ops",
            risk_level=RiskLevel.HIGH,
            description="File deletion requires human approval to prevent accidental data loss.",
            action_filter={"delete", "remove", "rm"},
            timeout_seconds=60.0
        ))
        self.register_rule(HITLRule(
            tool_name="memory_delete",
            risk_level=RiskLevel.MEDIUM,
            description="Memory deletion requires human approval.",
            timeout_seconds=60.0
        ))

    def register_rule(self, rule: HITLRule):
        """Register a HITL rule for a tool."""
        self._rules[rule.tool_name] = rule

    def unregister_rule(self, tool_name: str) -> bool:
        """Remove a HITL rule."""
        return self._rules.pop(tool_name, None) is not None

    def check_requires_approval(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[HITLRule]:
        """Check if a tool invocation requires human approval.
        
        Returns the matching rule if approval is needed, None otherwise.
        """
        rule = self._rules.get(tool_name)
        if not rule:
            return None

        # If there's an action filter, check the action argument
        if rule.action_filter:
            action_val = (
                str(arguments.get("action", "") or 
                    arguments.get("operation", "") or 
                    arguments.get("op", ""))
            ).lower().strip()
            if action_val not in rule.action_filter:
                return None

        return rule

    def create_request(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any], 
        rule: HITLRule
    ) -> HITLRequest:
        """Create a new pending approval request."""
        request_id = f"hitl_{uuid.uuid4().hex[:12]}"
        req = HITLRequest(
            request_id=request_id,
            tool_name=tool_name,
            arguments=arguments,
            risk_level=rule.risk_level,
            description=rule.description,
            created_at=time.time(),
            timeout_seconds=rule.timeout_seconds
        )
        self._pending[request_id] = req
        self._approval_events[request_id] = asyncio.Event()
        return req

    async def wait_for_resolution(self, request_id: str) -> HITLRequest:
        """Wait for a pending request to be approved, denied, or expired.
        
        Returns the resolved HITLRequest.
        """
        req = self._pending.get(request_id)
        if not req:
            raise ValueError(f"HITL request {request_id} not found")

        event = self._approval_events.get(request_id)
        if not event:
            raise ValueError(f"HITL event for {request_id} not found")

        try:
            if req.timeout_seconds > 0:
                await asyncio.wait_for(event.wait(), timeout=req.timeout_seconds)
            else:
                await event.wait()
        except asyncio.TimeoutError:
            req.status = "expired"
            req.resolved_at = time.time()

        # Move to history
        self._pending.pop(request_id, None)
        self._approval_events.pop(request_id, None)
        self._history.append(req)
        return req

    def approve(self, request_id: str, approved_by: str = "user") -> bool:
        """Approve a pending HITL request."""
        req = self._pending.get(request_id)
        if not req or req.status != "pending":
            return False

        if req.is_expired:
            req.status = "expired"
            req.resolved_at = time.time()
            event = self._approval_events.get(request_id)
            if event:
                event.set()
            return False

        req.status = "approved"
        req.resolved_at = time.time()
        req.resolved_by = approved_by
        
        event = self._approval_events.get(request_id)
        if event:
            event.set()
        return True

    def deny(self, request_id: str, denied_by: str = "user") -> bool:
        """Deny a pending HITL request."""
        req = self._pending.get(request_id)
        if not req or req.status != "pending":
            return False

        req.status = "denied"
        req.resolved_at = time.time()
        req.resolved_by = denied_by
        
        event = self._approval_events.get(request_id)
        if event:
            event.set()
        return True

    def get_pending(self) -> List[Dict[str, Any]]:
        """Get all pending HITL requests."""
        # Clean up expired requests
        expired = [
            rid for rid, req in self._pending.items()
            if req.is_expired and req.status == "pending"
        ]
        for rid in expired:
            req = self._pending[rid]
            req.status = "expired"
            req.resolved_at = time.time()
            event = self._approval_events.get(rid)
            if event:
                event.set()

        return [req.to_dict() for req in self._pending.values()]

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent HITL resolution history."""
        return [req.to_dict() for req in self._history[-limit:]]

    def get_rules(self) -> List[Dict[str, Any]]:
        """Get all registered HITL rules."""
        return [
            {
                "tool_name": r.tool_name,
                "risk_level": r.risk_level.value,
                "description": r.description,
                "action_filter": list(r.action_filter) if r.action_filter else None,
                "timeout_seconds": r.timeout_seconds
            }
            for r in self._rules.values()
        ]


def requires_approval(
    risk_level: RiskLevel = RiskLevel.MEDIUM,
    description: str = "",
    action_filter: Optional[Set[str]] = None,
    timeout_seconds: float = 60.0
):
    """Decorator to mark a tool function as requiring HITL approval.
    
    Usage:
        @requires_approval(risk_level=RiskLevel.HIGH, description="Deletes files")
        def my_dangerous_tool(action, filename):
            ...
    """
    def decorator(func):
        func._hitl_rule = HITLRule(
            tool_name=func.__name__,
            risk_level=risk_level,
            description=description,
            action_filter=action_filter,
            timeout_seconds=timeout_seconds
        )
        return func
    return decorator


# Global singleton instance
hitl_registry = HITLRegistry()
