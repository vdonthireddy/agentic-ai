"""Tests for new MCP server tools: db_tools, python_tool, graph_memory, and legal auditor skill."""

import pytest
import os
import json
from pathlib import Path

from mcp_server.tools.db_tools import execute_readonly_sql
from mcp_server.tools.python_tool import execute_python_sandbox
from mcp_server.graph_memory import EntityGraphMemory
from mcp_server.skills import ALL_SKILLS, render_skill

def test_readonly_sql_execution(tmp_path):
    db_file = tmp_path / "test.db"
    res = execute_readonly_sql(query="SELECT 1 as num, 'hello' as greeting", db_path=str(db_file))
    assert res["status"] == "success"
    assert res["row_count"] == 1
    assert res["rows"][0]["num"] == 1

def test_sql_blocks_destructive_commands(tmp_path):
    db_file = tmp_path / "test.db"
    res = execute_readonly_sql(query="DROP TABLE employees", db_path=str(db_file))
    assert res["status"] == "error"
    assert "read-only" in res["message"].lower() or "destructive" in res["message"].lower()

def test_python_sandbox_basic_math():
    res = execute_python_sandbox(code="""
a = 10
b = 25
total = a + b
print(f"Total: {total}")
""")
    assert res["status"] == "success"
    assert "Total: 35" in res["output"]
    assert res["result_variables"].get("total") == "35"

def test_python_sandbox_blocks_os_system():
    res = execute_python_sandbox(code="import os; os.system('ls')")
    assert res["status"] == "error"
    assert "Security restriction" in res["message"]

def test_python_sandbox_plotly_capture():
    code = """
import plotly.graph_objects as go
fig = go.Figure(data=[go.Bar(x=['A', 'B'], y=[1, 2])])
"""
    res = execute_python_sandbox(code=code)
    assert res["status"] == "success"
    assert res["figures_count"] >= 1
    assert len(res["plotly_figures"]) >= 1

def test_graph_memory_triples_and_pathfinding(tmp_path):
    db_file = tmp_path / "graph.db"
    gm = EntityGraphMemory(db_path=str(db_file))

    # Add entity triples: Sarah -> Project Apollo -> AWS Cluster
    gm.add_relation("Sarah", "LEAD_ON", "Project Apollo")
    gm.add_relation("Project Apollo", "DEPLOYED_TO", "AWS Cluster")
    gm.add_relation("Alex", "CONTRIBUTOR_TO", "Project Apollo")

    # Query direct relations
    sarah_rels = gm.query_relations("Sarah")
    assert len(sarah_rels) >= 1
    assert sarah_rels[0]["relation"] == "LEAD_ON"

    # Multi-hop path finding
    path_res = gm.find_multi_hop_path("Sarah", "AWS Cluster")
    assert path_res["status"] == "success"
    assert path_res["hop_count"] == 2
    assert path_res["path_nodes"] == ["Sarah", "Project Apollo", "AWS Cluster"]

def test_legal_auditor_skill_registration():
    assert "legal_auditor_skill" in ALL_SKILLS
    rendered = render_skill("legal_auditor_skill", {"contract_type": "NDA"})
    assert "Enterprise Legal" in rendered
    assert "NDA" in rendered
