import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Database, Share2, Plus, Search, ArrowRight, GitFork, RefreshCw, Trash2, CheckCircle2, AlertCircle } from 'lucide-react';

export default function MemoryView() {
  const [activeSubTab, setActiveSubTab] = useState('vector'); // 'vector' | 'graph'

  // Vector Memory State
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

  // Graph Memory State
  const [graphData, setGraphData] = useState({ relations: [], entities: [] });
  const [graphLoading, setGraphLoading] = useState(false);
  const [newSource, setNewSource] = useState('');
  const [newRelation, setNewRelation] = useState('ASSOCIATED_WITH');
  const [newTarget, setNewTarget] = useState('');
  const [newWeight, setNewWeight] = useState(1.0);
  
  // Path Finding State
  const [pathStart, setPathStart] = useState('');
  const [pathEnd, setPathEnd] = useState('');
  const [maxDepth, setMaxDepth] = useState(4);
  const [pathResult, setPathResult] = useState(null);
  const [pathFinding, setPathFinding] = useState(false);

  // Entity Query State
  const [entityQuery, setEntityQuery] = useState('');
  const [queryDirection, setQueryDirection] = useState('both');
  const [entityRelations, setEntityRelations] = useState(null);
  const [queryLoading, setQueryLoading] = useState(false);

  // Load Vector Memories
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

  // Load Graph Data
  const loadGraphData = async () => {
    setGraphLoading(true);
    try {
      const data = await api.getGraphAll(50).catch(() => ({ relations: [], entities: [] }));
      setGraphData(data || { relations: [], entities: [] });
    } catch (e) {
      console.warn('Failed to fetch graph data', e);
    } finally {
      setGraphLoading(false);
    }
  };

  useEffect(() => {
    loadMemories();
    loadNamespaces();
  }, [activeNamespace]);

  useEffect(() => {
    if (activeSubTab === 'graph') {
      loadGraphData();
    }
  }, [activeSubTab]);

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
      } else {
        setError(data.message || 'Delete failed');
      }
    } catch (err) {
      setError('Delete failed');
    }
  };

  // Add Graph Relation
  const handleAddRelation = async (e) => {
    e.preventDefault();
    if (!newSource.trim() || !newRelation.trim() || !newTarget.trim()) return;
    setError('');
    try {
      const res = await api.addGraphRelation({
        source: newSource.trim(),
        relation: newRelation.trim(),
        target: newTarget.trim(),
        weight: parseFloat(newWeight) || 1.0
      });
      if (res.status === 'success') {
        setSuccessMsg(`Added relation: ${res.triple}`);
        setNewSource('');
        setNewTarget('');
        setTimeout(() => setSuccessMsg(''), 3500);
        loadGraphData();
      }
    } catch (err) {
      setError('Failed to add graph relation: ' + err.message);
    }
  };

  // Find Multi-Hop Path
  const handleFindPath = async (e) => {
    e.preventDefault();
    if (!pathStart.trim() || !pathEnd.trim()) return;
    setPathFinding(true);
    setPathResult(null);
    try {
      const res = await api.findGraphPath(pathStart.trim(), pathEnd.trim(), maxDepth);
      setPathResult(res);
    } catch (err) {
      setPathResult({ status: 'error', message: err.message });
    } finally {
      setPathFinding(false);
    }
  };

  // Query Entity Relations
  const handleQueryEntity = async (e) => {
    e.preventDefault();
    if (!entityQuery.trim()) return;
    setQueryLoading(true);
    try {
      const res = await api.queryGraphRelations(entityQuery.trim(), queryDirection);
      setEntityRelations(res.relations || []);
    } catch (err) {
      setEntityRelations([]);
    } finally {
      setQueryLoading(false);
    }
  };

  const displayMemories = searchResults !== null ? searchResults : memories;

  return (
    <div style={{ padding: '24px', maxWidth: '1140px' }}>
      {/* View Header */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <h2 style={{ color: '#f0f0f0', margin: 0, fontSize: '22px' }}>
            🧠 Memory Explorer
          </h2>
          <span style={{ fontSize: '11px', background: 'rgba(59,130,246,0.18)', color: '#60a5fa', padding: '3px 9px', borderRadius: '12px', border: '1px solid rgba(59,130,246,0.3)', fontWeight: '600' }}>
            Vector & GraphRAG
          </span>
        </div>
        <p style={{ color: '#888', fontSize: '13px', marginTop: '6px' }}>
          Browse, recall, and manage long-term semantic embeddings and associative multi-hop knowledge graph relationships.
        </p>
      </div>

      {/* Primary Sub-Tabs */}
      <div className="memory-hub-nav">
        <button
          className={`memory-tab-btn ${activeSubTab === 'vector' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('vector')}
        >
          <Database size={16} />
          <span>Semantic Vector Memory</span>
        </button>
        <button
          className={`memory-tab-btn ${activeSubTab === 'graph' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('graph')}
        >
          <Share2 size={16} />
          <span>Knowledge Graph (GraphRAG)</span>
        </button>
      </div>

      {/* Global Alerts */}
      {successMsg && (
        <div style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.3)', borderRadius: '8px', padding: '10px 14px', marginBottom: '14px', color: '#22c55e', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <CheckCircle2 size={16} />
          <span>{successMsg}</span>
        </div>
      )}
      {error && (
        <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '8px', padding: '10px 14px', marginBottom: '14px', color: '#ef4444', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* TAB 1: Semantic Vector Memory */}
      {activeSubTab === 'vector' && (
        <div>
          {/* Namespace Tabs */}
          <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{ fontSize: '12px', color: '#888', marginRight: '4px' }}>Namespace:</span>
            {['default', ...namespaces.filter(n => n !== 'default')].map(ns => (
              <button
                key={ns}
                onClick={() => { setActiveNamespace(ns); setSearchResults(null); }}
                style={{
                  padding: '5px 12px',
                  borderRadius: '16px',
                  border: activeNamespace === ns ? '1px solid rgba(59,130,246,0.6)' : '1px solid rgba(255,255,255,0.08)',
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
      )}

      {/* TAB 2: Knowledge Graph (GraphRAG) */}
      {activeSubTab === 'graph' && (
        <div>
          {/* Graph Overview Stats */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px', marginBottom: '20px' }}>
            <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', padding: '16px' }}>
              <span style={{ fontSize: '11px', color: '#888', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Entities (Nodes)</span>
              <div style={{ fontSize: '24px', fontWeight: '700', color: '#38bdf8', marginTop: '4px' }}>
                {graphData.entities?.length || 0}
              </div>
            </div>
            <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', padding: '16px' }}>
              <span style={{ fontSize: '11px', color: '#888', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Relations (Edges)</span>
              <div style={{ fontSize: '24px', fontWeight: '700', color: '#a78bfa', marginTop: '4px' }}>
                {graphData.relations?.length || 0}
              </div>
            </div>
            <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', padding: '16px' }}>
              <span style={{ fontSize: '11px', color: '#888', textTransform: 'uppercase', letterSpacing: '0.05em' }}>GraphRAG Engine</span>
              <div style={{ fontSize: '14px', fontWeight: '600', color: '#22c55e', marginTop: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span>⚡ SQLite + NetworkX</span>
              </div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '16px', marginBottom: '20px' }}>
            {/* Edge Inserter */}
            <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', padding: '18px' }}>
              <h3 style={{ color: '#f0f0f0', margin: '0 0 12px 0', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Plus size={16} className="text-cyan-400" />
                <span>Add Directed Relation (Triple)</span>
              </h3>
              <form onSubmit={handleAddRelation} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div>
                  <label style={{ fontSize: '11px', color: '#888', display: 'block', marginBottom: '4px' }}>Source Entity</label>
                  <input
                    type="text"
                    value={newSource}
                    onChange={(e) => setNewSource(e.target.value)}
                    placeholder="e.g. Paris"
                    required
                    style={{ width: '100%', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '8px 10px', color: '#fff', fontSize: '12px' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '11px', color: '#888', display: 'block', marginBottom: '4px' }}>Relation Type</label>
                  <input
                    type="text"
                    value={newRelation}
                    onChange={(e) => setNewRelation(e.target.value)}
                    placeholder="e.g. CAPITAL_OF"
                    required
                    style={{ width: '100%', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '8px 10px', color: '#fff', fontSize: '12px' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '11px', color: '#888', display: 'block', marginBottom: '4px' }}>Target Entity</label>
                  <input
                    type="text"
                    value={newTarget}
                    onChange={(e) => setNewTarget(e.target.value)}
                    placeholder="e.g. France"
                    required
                    style={{ width: '100%', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '8px 10px', color: '#fff', fontSize: '12px' }}
                  />
                </div>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <div style={{ flex: 1 }}>
                    <label style={{ fontSize: '11px', color: '#888', display: 'block', marginBottom: '4px' }}>Weight (Strength)</label>
                    <input
                      type="number"
                      step="0.1"
                      min="0.1"
                      max="10.0"
                      value={newWeight}
                      onChange={(e) => setNewWeight(e.target.value)}
                      style={{ width: '100%', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '8px 10px', color: '#fff', fontSize: '12px' }}
                    />
                  </div>
                  <button
                    type="submit"
                    style={{ marginTop: '18px', background: 'linear-gradient(135deg, #06b6d4, #3b82f6)', color: '#fff', border: 'none', borderRadius: '6px', padding: '9px 18px', cursor: 'pointer', fontSize: '12px', fontWeight: '600' }}
                  >
                    Add Edge
                  </button>
                </div>
              </form>
            </div>

            {/* Multi-Hop Path Finder */}
            <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', padding: '18px' }}>
              <h3 style={{ color: '#f0f0f0', margin: '0 0 12px 0', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <GitFork size={16} className="text-indigo-400" />
                <span>Multi-Hop Path Finder (Graph Traversal)</span>
              </h3>
              <form onSubmit={handleFindPath} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <div style={{ flex: 1 }}>
                    <label style={{ fontSize: '11px', color: '#888', display: 'block', marginBottom: '4px' }}>Start Entity</label>
                    <input
                      type="text"
                      value={pathStart}
                      onChange={(e) => setPathStart(e.target.value)}
                      placeholder="e.g. Alice"
                      required
                      style={{ width: '100%', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '8px 10px', color: '#fff', fontSize: '12px' }}
                    />
                  </div>
                  <div style={{ flex: 1 }}>
                    <label style={{ fontSize: '11px', color: '#888', display: 'block', marginBottom: '4px' }}>End Entity</label>
                    <input
                      type="text"
                      value={pathEnd}
                      onChange={(e) => setPathEnd(e.target.value)}
                      placeholder="e.g. Mountain View"
                      required
                      style={{ width: '100%', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '8px 10px', color: '#fff', fontSize: '12px' }}
                    />
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <div style={{ flex: 1 }}>
                    <label style={{ fontSize: '11px', color: '#888', display: 'block', marginBottom: '4px' }}>Max Depth ({maxDepth} hops)</label>
                    <input
                      type="range"
                      min="1"
                      max="6"
                      value={maxDepth}
                      onChange={(e) => setMaxDepth(parseInt(e.target.value))}
                      style={{ width: '100%' }}
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={pathFinding}
                    style={{ marginTop: '16px', background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: '#fff', border: 'none', borderRadius: '6px', padding: '9px 18px', cursor: 'pointer', fontSize: '12px', fontWeight: '600' }}
                  >
                    {pathFinding ? 'Traversing...' : 'Find Path'}
                  </button>
                </div>
              </form>

              {/* Path Result Display */}
              {pathResult && (
                <div style={{ marginTop: '14px', padding: '12px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.06)' }}>
                  {pathResult.status === 'success' ? (
                    <div>
                      <div style={{ fontSize: '11px', color: '#22c55e', fontWeight: '600', marginBottom: '8px' }}>
                        ✅ Path Found ({pathResult.hop_count} {pathResult.hop_count === 1 ? 'hop' : 'hops'}):
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', fontSize: '12px' }}>
                        {pathResult.path_steps?.map((step, idx) => (
                          <React.Fragment key={idx}>
                            <span style={{ background: 'rgba(59,130,246,0.2)', color: '#93c5fd', padding: '3px 8px', borderRadius: '4px', border: '1px solid rgba(59,130,246,0.3)' }}>
                              {step.from}
                            </span>
                            <span style={{ color: '#a78bfa', fontSize: '11px', fontWeight: '600' }}>
                              —[{step.relation}]→
                            </span>
                            {idx === pathResult.path_steps.length - 1 && (
                              <span style={{ background: 'rgba(59,130,246,0.2)', color: '#93c5fd', padding: '3px 8px', borderRadius: '4px', border: '1px solid rgba(59,130,246,0.3)' }}>
                                {step.to}
                              </span>
                            )}
                          </React.Fragment>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div style={{ fontSize: '12px', color: '#f59e0b' }}>
                      ⚠️ {pathResult.message || 'No connecting path found.'}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Connected Relations Query Section */}
          <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', padding: '18px', marginBottom: '20px' }}>
            <h3 style={{ color: '#f0f0f0', margin: '0 0 12px 0', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Search size={16} className="text-emerald-400" />
              <span>Query Entity Relations</span>
            </h3>
            <form onSubmit={handleQueryEntity} style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
              <input
                type="text"
                value={entityQuery}
                onChange={(e) => setEntityQuery(e.target.value)}
                placeholder="Enter entity name (e.g. Paris, Alice, Google)..."
                style={{ flex: 1, background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '8px 12px', color: '#fff', fontSize: '13px' }}
              />
              <select
                value={queryDirection}
                onChange={(e) => setQueryDirection(e.target.value)}
                style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '8px 10px', color: '#ccc', fontSize: '12px' }}
              >
                <option value="both">Both Directions</option>
                <option value="outgoing">Outgoing Edges</option>
                <option value="incoming">Incoming Edges</option>
              </select>
              <button
                type="submit"
                disabled={queryLoading}
                style={{ background: 'linear-gradient(135deg, #10b981, #059669)', color: '#fff', border: 'none', borderRadius: '8px', padding: '8px 18px', cursor: 'pointer', fontSize: '12px', fontWeight: '600' }}
              >
                {queryLoading ? 'Searching...' : 'Inspect'}
              </button>
            </form>

            {entityRelations !== null && (
              <div style={{ marginTop: '10px' }}>
                <span style={{ fontSize: '11px', color: '#888', display: 'block', marginBottom: '8px' }}>
                  Found {entityRelations.length} connection(s) for &quot;{entityQuery}&quot;:
                </span>
                {entityRelations.length === 0 ? (
                  <p style={{ color: '#666', fontSize: '12px' }}>No relations found for this entity.</p>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {entityRelations.map((rel, idx) => (
                      <div key={idx} style={{ background: 'rgba(0,0,0,0.25)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '6px', padding: '8px 12px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px' }}>
                        <span style={{ color: '#38bdf8', fontWeight: '600' }}>{rel.source}</span>
                        <span style={{ color: '#a78bfa', fontSize: '11px', background: 'rgba(167,139,250,0.15)', padding: '2px 6px', borderRadius: '4px' }}>
                          [{rel.relation}]
                        </span>
                        <ArrowRight size={12} className="text-gray-500" />
                        <span style={{ color: '#38bdf8', fontWeight: '600' }}>{rel.target}</span>
                        <span style={{ marginLeft: 'auto', fontSize: '10px', color: '#888' }}>weight: {rel.weight}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Graph Triples Explorer Table */}
          <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <h3 style={{ color: '#ccc', margin: 0, fontSize: '14px' }}>
                🕸️ Graph Relationship Registry ({graphData.relations?.length || 0})
              </h3>
              <button
                onClick={loadGraphData}
                disabled={graphLoading}
                style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '6px 12px', color: '#ccc', cursor: 'pointer', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                <RefreshCw size={12} className={graphLoading ? 'spin' : ''} />
                <span>Refresh</span>
              </button>
            </div>

            {(!graphData.relations || graphData.relations.length === 0) ? (
              <div style={{ textAlign: 'center', padding: '36px', color: '#555' }}>
                <div style={{ fontSize: '32px', marginBottom: '8px' }}>🕸️</div>
                <p>No graph relations stored yet. Add directed triples above to populate the knowledge graph.</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {graphData.relations.map((rel) => (
                  <div key={rel.relation_id} style={{
                    padding: '10px 14px',
                    background: 'rgba(0,0,0,0.2)',
                    borderRadius: '8px',
                    border: '1px solid rgba(255,255,255,0.05)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '12px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
                      <span style={{ color: '#38bdf8', fontWeight: '600' }}>{rel.source}</span>
                      <span style={{ color: '#c084fc', background: 'rgba(192,132,252,0.12)', border: '1px solid rgba(192,132,252,0.25)', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: '600' }}>
                        [{rel.relation}]
                      </span>
                      <ArrowRight size={14} style={{ color: '#64748b' }} />
                      <span style={{ color: '#38bdf8', fontWeight: '600' }}>{rel.target}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '11px', color: '#666' }}>
                      <span>weight: {rel.weight}</span>
                      {rel.created_at && <span>{new Date(rel.created_at).toLocaleDateString()}</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
