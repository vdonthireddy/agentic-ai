"""Unit tests for MCPClientManager argument adaptation and normalization."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from ai_agent.mcp_client import MCPClientManager

@pytest.mark.asyncio
async def test_mcp_client_calculator_normalization_formula():
    client = MCPClientManager()
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_content = MagicMock()
    mock_content.text = '{"success": true, "result": 42}'
    mock_result.content = [mock_content]
    mock_session.call_tool.return_value = mock_result
    client._session = mock_session

    # Call with formula alias
    res = await client.execute_tool("calculator", {"formula": "21 * 2"})
    mock_session.call_tool.assert_called_once_with("calculator", arguments={"formula": "21 * 2", "expression": "21 * 2"})
    assert "42" in res

@pytest.mark.asyncio
async def test_mcp_client_calculator_normalization_tip_total():
    client = MCPClientManager()
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_content = MagicMock()
    mock_content.text = '{"success": true, "result": 217.71}'
    mock_result.content = [mock_content]
    mock_session.call_tool.return_value = mock_result
    client._session = mock_session

    # Call with tip and total
    await client.execute_tool("calculator", {"tip": "33.21", "total": "184.50"})
    mock_session.call_tool.assert_called_once_with(
        "calculator",
        arguments={"tip": "33.21", "total": "184.50", "expression": "(184.50) + (33.21)"}
    )

@pytest.mark.asyncio
async def test_mcp_client_workspace_file_ops_normalization():
    client = MCPClientManager()
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_content = MagicMock()
    mock_content.text = '{"success": true, "action": "write"}'
    mock_result.content = [mock_content]
    mock_session.call_tool.return_value = mock_result
    client._session = mock_session

    # Call with operation='save' and content
    await client.execute_tool("workspace_file_ops", {
        "operation": "save",
        "file_name": "itinerary.txt",
        "content": "Vacation details"
    })
    mock_session.call_tool.assert_called_once_with(
        "workspace_file_ops",
        arguments={
            "operation": "save",
            "file_name": "itinerary.txt",
            "content": "Vacation details",
            "action": "save"
        }
    )
