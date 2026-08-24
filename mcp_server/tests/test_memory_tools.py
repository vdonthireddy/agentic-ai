"""Tests for memory tools (store, recall, list, delete)."""

import pytest
import sys
import os
from pathlib import Path

# Set test DB path BEFORE importing memory modules
_test_db_path = str((Path(__file__).parent.parent / "test_memories.db").resolve())
os.environ["MEMORY_DB_PATH"] = _test_db_path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import memory_backend and reinitialize with test path
import memory_backend as mb
mb.memory_backend = mb.SQLiteMemoryBackend(db_path=_test_db_path)

import tools.memory_tools as tmt
tmt.memory_backend = mb.memory_backend

from tools.memory_tools import memory_store, memory_recall, memory_list, memory_delete
import sqlite3


@pytest.fixture(autouse=True)
def cleanup_db():
    """Clean up test database table before each test."""
    conn = sqlite3.connect(_test_db_path)
    conn.execute("DELETE FROM memories")
    conn.commit()
    conn.close()
    yield
    if Path(_test_db_path).exists():
        conn = sqlite3.connect(_test_db_path)
        conn.execute("DELETE FROM memories")
        conn.commit()
        conn.close()


class TestMemoryStore:
    def test_store_basic(self):
        result = memory_store(content="The capital of France is Paris.")
        assert result["status"] == "success"
        assert result["memory_id"].startswith("mem_")
        assert result["namespace"] == "default"

    def test_store_with_namespace(self):
        result = memory_store(content="Test content", namespace="work")
        assert result["status"] == "success"
        assert result["namespace"] == "work"

    def test_store_with_tags(self):
        result = memory_store(content="Tagged content", tags="geography, europe")
        assert result["status"] == "success"

    def test_store_empty_content(self):
        result = memory_store(content="")
        assert result["status"] == "error"

    def test_store_text_alias(self):
        result = memory_store(text="Using text alias")
        assert result["status"] == "success"

    def test_store_data_alias(self):
        result = memory_store(data="Using data alias")
        assert result["status"] == "success"


class TestMemoryRecall:
    def test_recall_after_store(self):
        memory_store(content="Paris is famous for the Eiffel Tower and croissants.")
        memory_store(content="Tokyo is known for sushi and cherry blossoms.")
        
        result = memory_recall(query="Eiffel Tower croissants")
        assert result["status"] == "success"
        assert result["count"] >= 1

    def test_recall_empty_query(self):
        result = memory_recall(query="")
        assert result["status"] == "error"

    def test_recall_no_results(self):
        result = memory_recall(query="quantum computing algorithms")
        assert result["status"] == "success"
        assert result["count"] == 0

    def test_recall_with_namespace(self):
        memory_store(content="Work memory content", namespace="work")
        result = memory_recall(query="work content", namespace="work")
        assert result["status"] == "success"

    def test_recall_stemmed_and_morphological(self):
        memory_store(content="I am allergic to peanuts")
        # Querying with 'allergies' should match 'allergic' via morphological stemmer
        result = memory_recall(query="allergies")
        assert result["status"] == "success"
        assert result["count"] >= 1
        assert "peanuts" in result["memories"][0]["content"]

        # Querying with 'peanut' should match 'peanuts'
        result_peanut = memory_recall(query="peanut")
        assert result_peanut["status"] == "success"
        assert result_peanut["count"] >= 1


class TestMemoryList:
    def test_list_empty(self):
        result = memory_list()
        assert result["status"] == "success"
        assert result["count"] == 0

    def test_list_after_store(self):
        memory_store(content="First memory")
        memory_store(content="Second memory")
        
        result = memory_list()
        assert result["status"] == "success"
        assert result["count"] == 2

    def test_list_with_limit(self):
        for i in range(5):
            memory_store(content=f"Memory {i}")
        
        result = memory_list(limit=3)
        assert result["status"] == "success"
        assert result["count"] <= 3


class TestMemoryDelete:
    def test_delete_existing(self):
        store_result = memory_store(content="To be deleted")
        memory_id = store_result["memory_id"]
        
        result = memory_delete(memory_id=memory_id)
        assert result["status"] == "success"
        
        # Verify it's gone
        list_result = memory_list()
        assert list_result["count"] == 0

    def test_delete_nonexistent(self):
        result = memory_delete(memory_id="mem_nonexistent")
        assert result["status"] == "error"

    def test_delete_empty_id(self):
        result = memory_delete(memory_id="")
        assert result["status"] == "error"
