"""
GraphRAG: Entity & Relationship Knowledge Graph Memory Engine for MCP Server.
Provides structured multi-hop graph traversal and associative entity linking using SQLite and NetworkX.
"""

import sqlite3
import json
import os
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

try:
    import networkx as nx
except ImportError:
    nx = None

class EntityGraphMemory:
    """Manages directed knowledge graphs with multi-hop querying and path discovery."""

    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            base_dir = Path(__file__).parent.parent
            db_path = str(base_dir / "memory_store" / "knowledge_graph.db")
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                entity_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                attributes_json TEXT DEFAULT '{}',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                relation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_entity TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                target_entity TEXT NOT NULL,
                metadata_json TEXT DEFAULT '{}',
                weight REAL DEFAULT 1.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_entity) REFERENCES entities(entity_id),
                FOREIGN KEY (target_entity) REFERENCES entities(entity_id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_source ON relations(source_entity)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_target ON relations(target_entity)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rel_type ON relations(relation_type)")
        conn.commit()
        conn.close()

    def add_entity(self, entity_id: str, name: str, entity_type: str, attributes: Optional[Dict[str, Any]] = None) -> bool:
        """Add or update an entity node in the graph."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO entities (entity_id, name, entity_type, attributes_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(entity_id) DO UPDATE SET
                name=excluded.name,
                entity_type=excluded.entity_type,
                attributes_json=excluded.attributes_json
        """, (
            entity_id.strip(),
            name.strip(),
            entity_type.strip(),
            json.dumps(attributes or {})
        ))
        conn.commit()
        conn.close()
        return True

    def add_relation(
        self,
        source_entity: str,
        relation_type: str,
        target_entity: str,
        metadata: Optional[Dict[str, Any]] = None,
        weight: float = 1.0
    ) -> Dict[str, Any]:
        """Store directed edge: (source_entity)-[relation_type]->(target_entity)."""
        src = source_entity.strip()
        tgt = target_entity.strip()
        rel = relation_type.strip().upper().replace(" ", "_")

        # Auto-create entities if they do not exist
        self.add_entity(src, src, "CONCEPT")
        self.add_entity(tgt, tgt, "CONCEPT")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO relations (source_entity, relation_type, target_entity, metadata_json, weight)
            VALUES (?, ?, ?, ?, ?)
        """, (src, rel, tgt, json.dumps(metadata or {}), weight))
        rel_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {
            "status": "success",
            "relation_id": rel_id,
            "triple": f"({src})-[{rel}]->({tgt})",
            "weight": weight
        }

    def query_relations(self, entity_name: str, direction: str = "both", depth: int = 2) -> List[Dict[str, Any]]:
        """Query direct and multi-hop outgoing, incoming, or bidirectional edges for an entity."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        ent = entity_name.strip()
        pronouns = {"he", "him", "she", "her", "they", "them", "it", "user", "person", "me", "i", "someone"}

        # If a pronoun or empty entity was passed, return recent graph relations so the agent receives context
        if not ent or ent.lower() in pronouns:
            cursor.execute(
                "SELECT source_entity, relation_type, target_entity, weight, metadata_json "
                "FROM relations ORDER BY relation_id DESC LIMIT 25"
            )
            rows = cursor.fetchall()
            conn.close()
            return [
                {
                    "direction": "outgoing",
                    "source": r["source_entity"],
                    "relation": r["relation_type"],
                    "target": r["target_entity"],
                    "weight": r["weight"],
                    "hop": 1,
                    "metadata": json.loads(r["metadata_json"] or "{}")
                }
                for r in rows
            ]

        visited_entities = {ent.lower()}
        frontier = [ent]
        results = []
        seen_edges = set()

        current_depth = 1
        while frontier and current_depth <= max(1, depth):
            next_frontier = []
            for current_ent in frontier:
                if direction in ("out", "outgoing", "both"):
                    cursor.execute("SELECT * FROM relations WHERE source_entity = ? COLLATE NOCASE", (current_ent,))
                    for r in cursor.fetchall():
                        edge_key = (r["source_entity"], r["relation_type"], r["target_entity"])
                        if edge_key not in seen_edges:
                            seen_edges.add(edge_key)
                            target = r["target_entity"]
                            results.append({
                                "direction": "outgoing",
                                "source": r["source_entity"],
                                "relation": r["relation_type"],
                                "target": target,
                                "weight": r["weight"],
                                "hop": current_depth,
                                "metadata": json.loads(r["metadata_json"] or "{}")
                            })
                            if target.lower() not in visited_entities:
                                visited_entities.add(target.lower())
                                next_frontier.append(target)

                if direction in ("in", "incoming", "both"):
                    cursor.execute("SELECT * FROM relations WHERE target_entity = ? COLLATE NOCASE", (current_ent,))
                    for r in cursor.fetchall():
                        edge_key = (r["source_entity"], r["relation_type"], r["target_entity"])
                        if edge_key not in seen_edges:
                            seen_edges.add(edge_key)
                            source = r["source_entity"]
                            results.append({
                                "direction": "incoming",
                                "source": source,
                                "relation": r["relation_type"],
                                "target": r["target_entity"],
                                "weight": r["weight"],
                                "hop": current_depth,
                                "metadata": json.loads(r["metadata_json"] or "{}")
                            })
                            if source.lower() not in visited_entities:
                                visited_entities.add(source.lower())
                                next_frontier.append(source)

            frontier = next_frontier
            current_depth += 1

        conn.close()
        return results

    def find_multi_hop_path(self, start_entity: str, end_entity: str, max_depth: int = 4) -> Dict[str, Any]:
        """Find the shortest or all relational paths between two entities across the knowledge graph."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT source_entity, relation_type, target_entity, weight FROM relations")
        rows = cursor.fetchall()
        conn.close()

        if nx is not None:
            # Use NetworkX graph traversal
            G = nx.DiGraph()
            for r in rows:
                G.add_edge(r["source_entity"], r["target_entity"], relation=r["relation_type"], weight=r["weight"])

            src = start_entity.strip()
            dst = end_entity.strip()

            if not G.has_node(src) or not G.has_node(dst):
                return {
                    "status": "not_found",
                    "message": f"One or both entities ('{src}', '{dst}') do not exist in the graph.",
                    "path": []
                }

            try:
                path_nodes = nx.shortest_path(G, source=src, target=dst)
                path_steps = []
                for i in range(len(path_nodes) - 1):
                    u, v = path_nodes[i], path_nodes[i+1]
                    edge_data = G.get_edge_data(u, v)
                    path_steps.append({
                        "from": u,
                        "relation": edge_data.get("relation", "CONNECTED_TO"),
                        "to": v
                    })
                return {
                    "status": "success",
                    "hop_count": len(path_steps),
                    "path_nodes": path_nodes,
                    "path_steps": path_steps,
                    "readable_chain": " -> ".join([f"({s['from']})-[{s['relation']}]->({s['to']})" for s in path_steps])
                }
            except nx.NetworkXNoPath:
                return {
                    "status": "no_path",
                    "message": f"No relational path exists between '{src}' and '{dst}'.",
                    "path": []
                }
        else:
            # Pure Python BFS traversal fallback
            adj = {}
            for r in rows:
                adj.setdefault(r["source_entity"], []).append((r["target_entity"], r["relation_type"]))

            queue = [[(start_entity.strip(), "START")]]
            visited = {start_entity.strip()}

            while queue:
                current_path = queue.pop(0)
                curr_node, _ = current_path[-1]

                if curr_node.lower() == end_entity.strip().lower():
                    steps = []
                    for i in range(len(current_path) - 1):
                        u = current_path[i][0]
                        v, rel = current_path[i+1]
                        steps.append({"from": u, "relation": rel, "to": v})
                    return {
                        "status": "success",
                        "hop_count": len(steps),
                        "path_nodes": [p[0] for p in current_path],
                        "path_steps": steps,
                        "readable_chain": " -> ".join([f"({s['from']})-[{s['relation']}]->({s['to']})" for s in steps])
                    }

                if len(current_path) <= max_depth:
                    for neighbor, rel in adj.get(curr_node, []):
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(current_path + [(neighbor, rel)])

            return {"status": "no_path", "message": f"No path found between '{start_entity}' and '{end_entity}' within {max_depth} hops."}

    def get_all_graph_data(self, limit: int = 100) -> Dict[str, Any]:
        """Fetch all relations and entities from the SQLite knowledge graph."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT relation_id, source_entity, relation_type, target_entity, weight, created_at, metadata_json "
            "FROM relations ORDER BY relation_id DESC LIMIT ?",
            (limit,)
        )
        relations = []
        for r in cursor.fetchall():
            relations.append({
                "relation_id": r["relation_id"],
                "source": r["source_entity"],
                "relation": r["relation_type"],
                "target": r["target_entity"],
                "weight": r["weight"],
                "created_at": r["created_at"],
                "metadata": json.loads(r["metadata_json"] or "{}")
            })
        cursor.execute(
            "SELECT entity_id, name, entity_type, created_at FROM entities ORDER BY name ASC LIMIT ?",
            (limit,)
        )
        entities = [dict(e) for e in cursor.fetchall()]
        conn.close()
        return {"status": "success", "relations": relations, "entities": entities}

# Singleton instance
_graph_memory_instance: Optional[EntityGraphMemory] = None

def get_graph_memory() -> EntityGraphMemory:
    global _graph_memory_instance
    if _graph_memory_instance is None:
        _graph_memory_instance = EntityGraphMemory()
    return _graph_memory_instance
