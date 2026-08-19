import React, { useState, useEffect } from 'react';
import { api } from '../api/client';

export default function MemoryView() {
  const [memories, setMemories] = useState([]);
  const [namespaces, setNamespaces] = useState([]);
  const [activeNamespace, setActiveNamespace] = useState('default');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [newMemoryContent, setNewMemoryContent] = useState('');
  const [newMemoryNamespace, setNewMemoryNamespace] = useState('default');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const loadMemories = async (ns) => {
    setIsLoading(true);
    setError('');
    try {
      const res = await fetch(`/api/memory/list?namespace=${ns || activeNamespace}&limit=50`);
      const data = await res.json();
      setMemories(data.memories || []);
      setNamespaces(data.available_namespaces || [ns || activeNamespace]);
    } catch (err) {
      setError('Failed to load memories');
    } finally {
      setIsLoading(false);
    }
  };

  const loadNamespaces = async () => {
    try {
      const res = await fetch('/api/memory/namespaces');
      const data = await res.json();
      setNamespaces(data.namespaces || []);
    } catch (err) { /* ignore */ }
  };

  useEffect(() => {
    loadMemories();
    loadNamespaces();
  }, [activeNamespace]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setIsLoading(true);
    setError('');
    try {
      const res = await fetch('/api/memory/recall', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery, namespace: activeNamespace, top_k: 10 })
      });
      const data = await res.json();
      setSearchResults(data.memories || []);
    } catch (err) {
      setError('Search failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStore = async () => {
    if (!newMemoryContent.trim()) return;
    setIsLoading(true);
    setError('');
    try {
      const res = await fetch('/api/memory/store', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: newMemoryContent, namespace: newMemoryNamespace })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setSuccessMsg(`Memory stored: ${data.memory_id}`);
        setNewMemoryContent('');
        setTimeout(() => setSuccessMsg(''), 3000);
        loadMemories();
      } else {
        setError(data.message || 'Store failed');
      }
    } catch (err) {
      setError('Failed to store memory');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (memoryId) => {
    if (!window.confirm(`Delete memory ${memoryId}? This cannot be undone.`)) return;
    try {
      const res = await fetch(`/api/memory/${memoryId}`, { method: 'DELETE' });
      const data = await res.json();
      if (data.status === 'success') {
        setSuccessMsg('Memory deleted');
        setTimeout(() => setSuccessMsg(''), 3000);
        loadMemories();
      }
    } catch (err) {
      setError('Delete failed');
    }
  };

  const displayMemories = searchResults !== null ? searchResults : memories;

  return (
    <div style={{ padding: '24px', maxWidth: '1100px' }}>
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ color: '#f0f0f0', margin: 0, fontSize: '22px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          🧠 Memory Explorer
          <span style={{ fontSize: '12px', background: 'rgba(59,130,246,0.2)', color: '#60a5fa', padding: '3px 10px', borderRadius: '12px' }}>Phase 2</span>
        </h2>
        <p style={{ color: '#888', fontSize: '13px', marginTop: '6px' }}>
          Browse, search, and manage the agent's long-term semantic memory across sessions.
        </p>
      </div>

      {/* Namespace Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
        {['default', ...namespaces.filter(n => n !== 'default')].map(ns => (
          <button
            key={ns}
            onClick={() => { setActiveNamespace(ns); setSearchResults(null); }}
            style={{
              padding: '6px 14px',
              borderRadius: '16px',
              border: activeNamespace === ns ? '1px solid rgba(59,130,246,0.5)' : '1px solid rgba(255,255,255,0.08)',
              background: activeNamespace === ns ? 'rgba(59,130,246,0.15)' : 'rgba(255,255,255,0.03)',
              color: activeNamespace === ns ? '#60a5fa' : '#888',
              fontSize: '12px',
              cursor: 'pointer'
            }}
          >
            {ns}
          </button>
        ))}
      </div>

      {/* Search Section */}
      <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', padding: '16px', marginBottom: '16px' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search memories semantically..."
            style={{ flex: 1, background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '10px 14px', color: '#e0e0e0', fontSize: '13px' }}
          />
          <button onClick={handleSearch} disabled={isLoading} style={{ background: 'linear-gradient(135deg, #3b82f6, #2563eb)', color: '#fff', border: 'none', borderRadius: '8px', padding: '10px 20px', cursor: 'pointer', fontSize: '13px', fontWeight: '600' }}>
            🔍 Search
          </button>
          {searchResults !== null && (
            <button onClick={() => { setSearchResults(null); setSearchQuery(''); }} style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '10px 16px', color: '#aaa', cursor: 'pointer', fontSize: '12px' }}>
              ✕ Clear
            </button>
          )}
        </div>
      </div>

      {/* Store New Memory */}
      <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', padding: '16px', marginBottom: '16px' }}>
        <h3 style={{ color: '#ccc', margin: '0 0 10px 0', fontSize: '14px' }}>📝 Store New Memory</h3>
        <textarea
          value={newMemoryContent}
          onChange={(e) => setNewMemoryContent(e.target.value)}
          placeholder="Type content to remember..."
          style={{ width: '100%', minHeight: '60px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '10px', color: '#e0e0e0', fontSize: '13px', resize: 'vertical', fontFamily: 'inherit' }}
        />
        <div style={{ display: 'flex', gap: '8px', marginTop: '10px', alignItems: 'center' }}>
          <input
            type="text"
            value={newMemoryNamespace}
            onChange={(e) => setNewMemoryNamespace(e.target.value)}
            placeholder="Namespace"
            style={{ width: '120px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '8px', color: '#ccc', fontSize: '12px' }}
          />
          <button onClick={handleStore} disabled={isLoading || !newMemoryContent.trim()} style={{ background: 'linear-gradient(135deg, #22c55e, #16a34a)', color: '#fff', border: 'none', borderRadius: '8px', padding: '8px 18px', cursor: 'pointer', fontSize: '12px', fontWeight: '600' }}>
            💾 Store
          </button>
        </div>
      </div>

      {/* Alerts */}
      {successMsg && (
        <div style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.3)', borderRadius: '8px', padding: '10px 14px', marginBottom: '12px', color: '#22c55e', fontSize: '13px' }}>
          ✅ {successMsg}
        </div>
      )}
      {error && (
        <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '8px', padding: '10px 14px', marginBottom: '12px', color: '#ef4444', fontSize: '13px' }}>
          ❌ {error}
        </div>
      )}

      {/* Memory List */}
      <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', padding: '20px' }}>
        <h3 style={{ color: '#ccc', margin: '0 0 16px 0', fontSize: '14px' }}>
          {searchResults !== null ? `🔍 Search Results (${displayMemories.length})` : `📚 Stored Memories (${displayMemories.length})`}
        </h3>
        
        {displayMemories.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: '#555' }}>
            <div style={{ fontSize: '40px', marginBottom: '12px' }}>🧠</div>
            <p>{searchResults !== null ? 'No matching memories found.' : 'No memories stored yet. Start by storing some information above.'}</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {displayMemories.map((mem, i) => (
              <div key={mem.memory_id || i} style={{
                padding: '12px 16px',
                background: 'rgba(0,0,0,0.2)',
                borderRadius: '8px',
                border: '1px solid rgba(255,255,255,0.05)',
                position: 'relative'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                  <span style={{ fontFamily: 'monospace', fontSize: '10px', color: '#666' }}>{mem.memory_id}</span>
                  <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                    {mem.similarity_score !== undefined && (
                      <span style={{ fontSize: '10px', color: mem.similarity_score > 0.7 ? '#22c55e' : mem.similarity_score > 0.4 ? '#f59e0b' : '#888', background: 'rgba(0,0,0,0.3)', padding: '2px 6px', borderRadius: '4px' }}>
                        {(mem.similarity_score * 100).toFixed(0)}% match
                      </span>
                    )}
                    <button
                      onClick={() => handleDelete(mem.memory_id)}
                      style={{ background: 'none', border: 'none', color: '#666', cursor: 'pointer', fontSize: '14px', padding: '2px 4px' }}
                      title="Delete memory"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
                <p style={{ color: '#ccc', fontSize: '13px', margin: 0, lineHeight: '1.5', whiteSpace: 'pre-wrap' }}>
                  {mem.content}
                </p>
                {mem.metadata && Object.keys(mem.metadata).length > 0 && (
                  <div style={{ marginTop: '6px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {Object.entries(mem.metadata).filter(([k]) => !['namespace', 'timestamp'].includes(k)).map(([k, v]) => (
                      <span key={k} style={{ fontSize: '10px', color: '#888', background: 'rgba(255,255,255,0.04)', padding: '2px 6px', borderRadius: '4px' }}>
                        {k}: {typeof v === 'string' ? v : JSON.stringify(v)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
