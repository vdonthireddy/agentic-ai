"""Global pytest fixtures and test environment isolation."""

import os
import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def isolate_test_environment(tmp_path, monkeypatch):
    """
    Ensure all test executions use an isolated temporary SQLite database and clean
    HITL memory state so tests NEVER pollute the development or production llm_gateway.db.
    """
    test_db = tmp_path / "test_isolated.db"
    monkeypatch.setenv("LLM_GATEWAY_DB_PATH", str(test_db))

    from llm_gateway.config import config as gw_config
    gw_config.db_path = test_db

    try:
        from llm_gateway.db import init_db
        init_db(test_db)
    except Exception:
        pass

    try:
        from llm_gateway.logger import audit_logger
        audit_logger.db_path = test_db
    except Exception:
        pass

    try:
        from mcp_server.hitl import hitl_registry
        hitl_registry._pending.clear()
        hitl_registry._history.clear()
        hitl_registry._approval_events.clear()
    except Exception:
        pass

    yield test_db

    # Clean up after test
    try:
        from mcp_server.hitl import hitl_registry
        hitl_registry._pending.clear()
        hitl_registry._history.clear()
        hitl_registry._approval_events.clear()
    except Exception:
        pass
