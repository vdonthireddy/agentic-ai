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
