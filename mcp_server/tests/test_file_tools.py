"""Unit tests for workspace file operations."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.file_tools import workspace_file_ops

def test_file_write_and_read():
    filename = "test_unit_doc.txt"
    content = "Hello from unit test suite."
    
    write_res = workspace_file_ops(action="write", filepath=filename, content=content)
    assert write_res["success"] is True
    assert write_res["bytes_written"] == len(content)

    read_res = workspace_file_ops(action="read", filepath=filename)
    assert read_res["success"] is True
    assert read_res["content"] == content

    # Cleanup
    del_res = workspace_file_ops(action="delete", filepath=filename)
    assert del_res["success"] is True

def test_file_aliases():
    # Test file_name alias
    res = workspace_file_ops(action="write", file_name="alias_test.txt", text="sample text")
    assert res["success"] is True
    
    read_res = workspace_file_ops(action="read", path="alias_test.txt")
    assert read_res["success"] is True
    assert read_res["content"] == "sample text"
    
    workspace_file_ops(action="delete", filepath="alias_test.txt")

def test_path_traversal_protection():
    res = workspace_file_ops(action="read", filepath="../../../etc/passwd")
    assert res["success"] is False
    assert "Access denied" in res["error"] or "outside" in res["error"]

def test_workspace_file_ops_aliases_and_operations():
    # Test operation='save' alias
    save_res = workspace_file_ops(operation="save", filename="itinerary_alias.txt", content="Day 1: Paris")
    assert save_res["success"] is True
    assert save_res["action"] == "write"

    # Test operation='load' alias
    load_res = workspace_file_ops(operation="load", file_path="itinerary_alias.txt")
    assert load_res["success"] is True
    assert "Day 1: Paris" in load_res["content"]

    # Test list operation
    list_res = workspace_file_ops(operation="list")
    assert list_res["success"] is True
    assert list_res["action"] == "list"
    assert any("itinerary_alias.txt" in item["name"] for item in list_res["items"])

    # Test delete with 'rm' alias
    del_res = workspace_file_ops(op="rm", filepath="itinerary_alias.txt")
    assert del_res["success"] is True

def test_workspace_file_ops_inferred_write():
    # Calling with content but no explicit action should infer write
    res = workspace_file_ops(filename="inferred.txt", data="Auto inferred write")
    assert res["success"] is True
    assert res["action"] == "write"

    # Cleanup
    workspace_file_ops(action="delete", filename="inferred.txt")

def test_workspace_file_ops_unknown_action():
    res = workspace_file_ops(action="unsupported_action", filepath="test.txt")
    assert res["success"] is False
    assert "Unknown action" in res["error"]
