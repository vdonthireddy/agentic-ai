"""Vector memory backend abstraction for semantic long-term recall.

Supports ChromaDB (primary) and a SQLite-based fallback for environments
where ChromaDB is unavailable. Uses sentence-transformers for local
embeddings or falls back to basic TF-IDF cosine similarity.
"""

import json
import os
import time
import uuid
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class MemoryRecord:
    """A single stored memory with metadata."""
    memory_id: str
    content: str
    namespace: str
    metadata: Dict[str, Any]
    timestamp: float
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "namespace": self.namespace,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class MemoryBackend:
    """Abstract memory backend interface."""
    
    def store(self, content: str, metadata: Dict[str, Any], namespace: str = "default") -> str:
        raise NotImplementedError

    def recall(self, query: str, namespace: str = "default", top_k: int = 5) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def list_memories(self, namespace: str = "default", limit: int = 50) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def delete(self, memory_id: str) -> bool:
        raise NotImplementedError

    def list_namespaces(self) -> List[str]:
        raise NotImplementedError


class ChromaMemoryBackend(MemoryBackend):
    """ChromaDB-backed vector memory with local embeddings."""

    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir or str(
            Path(os.environ.get("MEMORY_PERSIST_DIR", "./memory_store")).resolve()
        )
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)

        try:
            import chromadb
            self.client = chromadb.PersistentClient(path=self.persist_dir)
            self._available = True
        except ImportError:
            self.client = None
            self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    def _get_collection(self, namespace: str):
        """Get or create a ChromaDB collection for the namespace."""
        safe_name = namespace.replace(" ", "_").replace("/", "_")[:63]
        if not safe_name:
            safe_name = "default"
        return self.client.get_or_create_collection(
            name=safe_name,
            metadata={"hnsw:space": "cosine"}
        )

    def store(self, content: str, metadata: Dict[str, Any], namespace: str = "default") -> str:
        if not self._available:
            raise RuntimeError("ChromaDB not available")
        
        memory_id = f"mem_{uuid.uuid4().hex[:12]}"
        collection = self._get_collection(namespace)
        
        meta = dict(metadata)
        meta["namespace"] = namespace
        meta["timestamp"] = time.time()
        # ChromaDB metadata values must be str, int, float, or bool
        sanitized_meta = {}
        for k, v in meta.items():
            if isinstance(v, (str, int, float, bool)):
                sanitized_meta[k] = v
            else:
                sanitized_meta[k] = json.dumps(v)
        
        collection.add(
            ids=[memory_id],
            documents=[content],
            metadatas=[sanitized_meta]
        )
        return memory_id

    def recall(self, query: str, namespace: str = "default", top_k: int = 5) -> List[Dict[str, Any]]:
        if not self._available:
            return []
        
        collection = self._get_collection(namespace)
        count = collection.count()
        if count == 0:
            return []
        
        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, count)
        )
        
        memories = []
        if results and results.get("ids"):
            for i, mid in enumerate(results["ids"][0]):
                doc = results["documents"][0][i] if results.get("documents") else ""
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                dist = results["distances"][0][i] if results.get("distances") else 0.0
                memories.append({
                    "memory_id": mid,
                    "content": doc,
                    "metadata": meta,
                    "namespace": namespace,
                    "similarity_score": round(1.0 - dist, 4) if dist else 1.0
                })
        return memories

    def list_memories(self, namespace: str = "default", limit: int = 50) -> List[Dict[str, Any]]:
        if not self._available:
            return []
        
        collection = self._get_collection(namespace)
        count = collection.count()
        if count == 0:
            return []
        
        results = collection.get(limit=min(limit, count))
        memories = []
        if results and results.get("ids"):
            for i, mid in enumerate(results["ids"]):
                doc = results["documents"][i] if results.get("documents") else ""
                meta = results["metadatas"][i] if results.get("metadatas") else {}
                memories.append({
                    "memory_id": mid,
                    "content": doc,
                    "metadata": meta,
                    "namespace": namespace
                })
        return memories

    def delete(self, memory_id: str) -> bool:
        if not self._available:
            return False
        
        # Search across all collections
        for col_name in [c.name for c in self.client.list_collections()]:
            try:
                col = self.client.get_collection(col_name)
                result = col.get(ids=[memory_id])
                if result and result.get("ids") and memory_id in result["ids"]:
                    col.delete(ids=[memory_id])
                    return True
            except Exception:
                continue
        return False

    def list_namespaces(self) -> List[str]:
        if not self._available:
            return []
        return [c.name for c in self.client.list_collections()]


class SQLiteMemoryBackend(MemoryBackend):
    """Lightweight SQLite-based memory backend with basic keyword matching.
    
    Fallback for environments where ChromaDB is not installed.
    Uses simple TF-IDF-like scoring based on keyword overlap.
    """

    def __init__(self, db_path: Optional[str] = None):
        import sqlite3
        self.db_path = db_path or str(
            Path(os.environ.get("MEMORY_DB_PATH", "./memory_store/memories.db")).resolve()
        )
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                memory_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                namespace TEXT DEFAULT 'default',
                metadata TEXT DEFAULT '{}',
                timestamp REAL,
                keywords TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_ns ON memories(namespace)")
        conn.commit()
        conn.close()

    @staticmethod
    def _extract_keywords(text: str) -> str:
        """Extract simple keywords for matching."""
        import re
        words = re.findall(r'\b\w{3,}\b', text.lower())
        # Remove common stop words
        stops = {"the", "and", "for", "are", "but", "not", "you", "all", "can", "had",
                 "her", "was", "one", "our", "out", "has", "have", "with", "this", "that",
                 "from", "they", "been", "will", "would", "could", "should", "into"}
        return " ".join(w for w in words if w not in stops)

    def store(self, content: str, metadata: Dict[str, Any], namespace: str = "default") -> str:
        import sqlite3
        memory_id = f"mem_{uuid.uuid4().hex[:12]}"
        keywords = self._extract_keywords(content)
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO memories (memory_id, content, namespace, metadata, timestamp, keywords) VALUES (?, ?, ?, ?, ?, ?)",
            (memory_id, content, namespace, json.dumps(metadata), time.time(), keywords)
        )
        conn.commit()
        conn.close()
        return memory_id

    def recall(self, query: str, namespace: str = "default", top_k: int = 5) -> List[Dict[str, Any]]:
        import sqlite3
        query_keywords = set(self._extract_keywords(query).split())
        if not query_keywords:
            return []

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM memories WHERE namespace = ? ORDER BY timestamp DESC LIMIT 200",
            (namespace,)
        )
        rows = cursor.fetchall()
        conn.close()

        scored = []
        for row in rows:
            row_keywords = set((row["keywords"] or "").split())
            if not row_keywords:
                continue
            overlap = len(query_keywords & row_keywords)
            score = overlap / max(len(query_keywords | row_keywords), 1)
            if score > 0:
                scored.append((score, dict(row)))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, row_dict in scored[:top_k]:
            meta = {}
            try:
                meta = json.loads(row_dict.get("metadata", "{}"))
            except Exception:
                pass
            results.append({
                "memory_id": row_dict["memory_id"],
                "content": row_dict["content"],
                "metadata": meta,
                "namespace": row_dict["namespace"],
                "similarity_score": round(score, 4)
            })
        return results

    def list_memories(self, namespace: str = "default", limit: int = 50) -> List[Dict[str, Any]]:
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM memories WHERE namespace = ? ORDER BY timestamp DESC LIMIT ?",
            (namespace, limit)
        )
        results = []
        for row in cursor.fetchall():
            meta = {}
            try:
                meta = json.loads(row["metadata"])
            except Exception:
                pass
            results.append({
                "memory_id": row["memory_id"],
                "content": row["content"],
                "metadata": meta,
                "namespace": row["namespace"],
                "timestamp": row["timestamp"]
            })
        conn.close()
        return results

    def delete(self, memory_id: str) -> bool:
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("DELETE FROM memories WHERE memory_id = ?", (memory_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def list_namespaces(self) -> List[str]:
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT DISTINCT namespace FROM memories")
        namespaces = [row[0] for row in cursor.fetchall()]
        conn.close()
        return namespaces


def create_memory_backend() -> MemoryBackend:
    """Factory that creates the best available memory backend.
    
    Tries ChromaDB first, falls back to SQLite.
    """
    chroma = ChromaMemoryBackend()
    if chroma.is_available:
        return chroma
    return SQLiteMemoryBackend()


# Global singleton
memory_backend = create_memory_backend()
