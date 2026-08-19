import React, { useState, useEffect } from 'react';
import { Search, Eye, RefreshCw, ChevronDown, ChevronRight, Layers, List, MessageSquare, CornerDownRight, Zap } from 'lucide-react';
import InspectorModal from '../components/InspectorModal';
import { api } from '../api/client';

export default function AuditLogsView({ logs: initialLogs = [], models = [], initialSearch = '' }) {
  const [viewMode, setViewMode] = useState('tree'); // 'tree' (hierarchical) | 'flat'
  const [logs, setLogs] = useState(initialLogs);
  const [conversations, setConversations] = useState([]);
  const [expandedConvs, setExpandedConvs] = useState({});
  const [expandedTurns, setExpandedTurns] = useState({});
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState(initialSearch || '');
  const [modelFilter, setModelFilter] = useState('');
  const [selectedLog, setSelectedLog] = useState(null);

  useEffect(() => {
    if (initialSearch) {
      setSearch(initialSearch);
    }
  }, [initialSearch]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const [flatData, hierData] = await Promise.all([
        api.getLogs({ limit: 200 }),
        api.getLogs({ limit: 50, hierarchical: true })
      ]);
      if (flatData && flatData.logs) {
        setLogs(flatData.logs);
      }
      if (hierData && hierData.conversations) {
        setConversations(hierData.conversations);
        // Expand the latest conversation by default
        if (hierData.conversations.length > 0) {
          const firstId = hierData.conversations[0].conv_id;
          setExpandedConvs((prev) => ({ ...prev, [firstId]: true }));
          if (hierData.conversations[0].turns?.length > 0) {
            const firstTurnId = hierData.conversations[0].turns[0].t_id;
            setExpandedTurns((prev) => ({ ...prev, [firstTurnId]: true }));
          }
        }
      }
    } catch (err) {
      console.error('Failed to fetch logs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const toggleConv = (convId) => {
    setExpandedConvs((prev) => ({ ...prev, [convId]: !prev[convId] }));
  };

  const toggleTurn = (turnId) => {
    setExpandedTurns((prev) => ({ ...prev, [turnId]: !prev[turnId] }));
  };

  // Filter flat logs
  const filteredFlatLogs = logs.filter((log) => {
    const text = `${log.agent_name || ''} ${log.conversation_id || log.session_id || ''} ${log.turn_id || ''} ${log.request_id || log.id || ''} ${log.model || ''}`.toLowerCase();
    const matchesSearch = !search || text.includes(search.toLowerCase());
    const matchesModel = !modelFilter || log.model === modelFilter;
    return matchesSearch && matchesModel;
  });

  // Filter conversations
  const filteredConversations = conversations.filter((conv) => {
    const text = `${conv.agent_name || ''} ${conv.conv_id || ''} ${conv.model || ''}`.toLowerCase();
    const matchesSearch = !search || text.includes(search.toLowerCase());
    const matchesModel = !modelFilter || conv.model === modelFilter;
    return matchesSearch && matchesModel;
  });

  return (
    <div>
      <div className="glass-card mb-6">
        <div className="card-header flex-between" style={{ flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h3>📜 Interaction Audit Logs</h3>
            <p>Categorized 3-tier telemetry: <strong>Conversation</strong> &rarr; <strong>Turn</strong> &rarr; <strong>Request (LLM Calls)</strong></p>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
            <div className="btn-group">
              <button
                className={`btn btn-sm ${viewMode === 'tree' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setViewMode('tree')}
              >
                <Layers size={14} />
                <span>Hierarchical Tree</span>
              </button>
              <button
                className={`btn btn-sm ${viewMode === 'flat' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setViewMode('flat')}
              >
                <List size={14} />
                <span>Flat Stream</span>
              </button>
            </div>

            <button
              className={`btn btn-xs ${search === 'eval_' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setSearch(search === 'eval_' ? '' : 'eval_')}
              title="Filter to Benchmark Evaluation interaction traces"
            >
              <span>🧪 Evals Only</span>
            </button>
            <input
              type="text"
              className="form-control-sm"
              placeholder="Search Conv / Turn / Req ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ minWidth: '200px' }}
            />
            <select
              className="form-control-sm"
              value={modelFilter}
              onChange={(e) => setModelFilter(e.target.value)}
            >
              <option value="">All Models</option>
              {models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.id}
                </option>
              ))}
            </select>
            <button className="btn btn-secondary btn-sm" onClick={fetchLogs} disabled={loading} title="Refresh Logs">
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        {/* VIEW MODE 1: 3-TIER HIERARCHICAL TREE */}
        {viewMode === 'tree' ? (
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {filteredConversations.length === 0 ? (
              <div className="text-center py-8 text-muted">
                No matching conversations found. Start chatting or execute agent workflows to record logs.
              </div>
            ) : (
              filteredConversations.map((conv) => {
                const isConvExpanded = !!expandedConvs[conv.conv_id];
                return (
                  <div
                    key={conv.conv_id}
                    className="glass-card"
                    style={{
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      background: 'rgba(20, 26, 38, 0.65)',
                      borderRadius: '10px',
                      overflow: 'hidden'
                    }}
                  >
                    {/* Level 1: Conversation Header */}
                    <div
                      className="p-3 flex-between"
                      style={{
                        cursor: 'pointer',
                        background: isConvExpanded ? 'rgba(255, 255, 255, 0.04)' : 'transparent',
                        borderBottom: isConvExpanded ? '1px solid rgba(255, 255, 255, 0.08)' : 'none',
                        transition: 'background 0.2s'
                      }}
                      onClick={() => toggleConv(conv.conv_id)}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        {isConvExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <MessageSquare size={16} className="text-accent" />
                            <strong>Conversation:</strong>
                            <code className="text-accent" style={{ fontSize: '13px' }}>{conv.conv_id}</code>
                            <span className="badge badge-outline">{conv.agent_name || 'Agent'}</span>
                          </div>
                          <div className="text-muted text-xs" style={{ marginTop: '2px' }}>
                            Started: {new Date(conv.started_at).toLocaleString()} &bull; Last Activity: {new Date(conv.last_activity).toLocaleTimeString()}
                          </div>
                        </div>
                      </div>

                      <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                        <span className="badge badge-dim">
                          {conv.turns?.length || 0} Turns
                        </span>
                        <span className="badge badge-dim">
                          {conv.total_requests} LLM Requests
                        </span>
                        <span className="badge badge-primary font-mono text-xs">
                          {conv.total_tokens || 0} Tokens
                        </span>
                      </div>
                    </div>

                    {/* Level 2: Turns Container */}
                    {isConvExpanded && (
                      <div className="p-3" style={{ display: 'flex', flexDirection: 'column', gap: '12px', background: 'rgba(0,0,0,0.15)' }}>
                        {(conv.turns || []).map((turn, tIdx) => {
                          const isTurnExpanded = !!expandedTurns[turn.t_id];
                          return (
                            <div
                              key={turn.t_id}
                              style={{
                                border: '1px solid rgba(255, 255, 255, 0.07)',
                                borderRadius: '8px',
                                background: 'rgba(255, 255, 255, 0.02)',
                                overflow: 'hidden'
                              }}
                            >
                              {/* Turn Header */}
                              <div
                                className="p-2.5 flex-between"
                                style={{
                                  cursor: 'pointer',
                                  background: isTurnExpanded ? 'rgba(255, 255, 255, 0.03)' : 'transparent',
                                  borderBottom: isTurnExpanded ? '1px solid rgba(255, 255, 255, 0.05)' : 'none'
                                }}
                                onClick={() => toggleTurn(turn.t_id)}
                              >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                  {isTurnExpanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
                                  <CornerDownRight size={14} className="text-muted" />
                                  <span className="badge badge-accent" style={{ fontWeight: 600 }}>
                                    Turn #{tIdx + 1}
                                  </span>
                                  <code>{turn.t_id}</code>
                                  <span className="text-muted text-xs">
                                    ({new Date(turn.turn_started_at).toLocaleTimeString()})
                                  </span>
                                </div>

                                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                  <span className="badge badge-dim text-xs">
                                    {turn.request_count} Calls
                                  </span>
                                  <span className="font-mono text-xs text-muted">
                                    {turn.turn_total_tokens || 0} tok
                                  </span>
                                  <span className="font-mono text-xs text-muted">
                                    {Math.round(turn.turn_total_latency_ms || 0)}ms
                                  </span>
                                </div>
                              </div>

                              {/* Level 3: Individual LLM Requests inside Turn */}
                              {isTurnExpanded && (
                                <div className="p-2" style={{ background: 'rgba(0, 0, 0, 0.25)' }}>
                                  <div className="table-responsive">
                                    <table className="data-table" style={{ fontSize: '12px' }}>
                                      <thead>
                                        <tr>
                                          <th>Step / Req ID</th>
                                          <th>Status</th>
                                          <th>Model</th>
                                          <th>Tools Executed</th>
                                          <th>Tokens (P / C)</th>
                                          <th>Latency</th>
                                          <th>Action</th>
                                        </tr>
                                      </thead>
                                      <tbody>
                                        {(turn.requests || []).map((req, rIdx) => (
                                          <tr key={req.request_id || req.id || rIdx}>
                                            <td>
                                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                                <Zap size={12} className="text-accent" />
                                                <span style={{ fontWeight: 600 }}>Step {rIdx + 1}:</span>
                                                <code className="text-xs">{req.request_id || req.id}</code>
                                              </div>
                                            </td>
                                            <td>
                                              <span
                                                className={`badge ${
                                                  req.status === 'SUCCESS' ? 'badge-success' : 'badge-error'
                                                }`}
                                                style={{ fontSize: '10px', padding: '2px 6px' }}
                                              >
                                                {req.status}
                                              </span>
                                            </td>
                                            <td>
                                              <code>{req.model}</code>
                                            </td>
                                            <td>
                                              {(req.tool_names || []).length > 0 ? (
                                                req.tool_names.map((t, idx) => (
                                                  <span key={idx} className="badge badge-accent" style={{ marginRight: '4px', fontSize: '10px' }}>
                                                    {t}
                                                  </span>
                                                ))
                                              ) : (
                                                <span className="text-muted">-</span>
                                              )}
                                            </td>
                                            <td className="font-mono">
                                              {req.prompt_tokens} / {req.completion_tokens} ({req.total_tokens})
                                            </td>
                                            <td className="font-mono">{Math.round(req.latency_ms || 0)}ms</td>
                                            <td>
                                              <button
                                                className="btn btn-secondary btn-sm"
                                                style={{ padding: '3px 8px', fontSize: '11px' }}
                                                onClick={(e) => {
                                                  e.stopPropagation();
                                                  setSelectedLog(req);
                                                }}
                                              >
                                                <Eye size={12} />
                                                <span>Inspect Trace</span>
                                              </button>
                                            </td>
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        ) : (
          /* VIEW MODE 2: FLAT STREAM TABLE */
          <div className="card-body p-0">
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Status</th>
                    <th>Request ID</th>
                    <th>Turn ID</th>
                    <th>Conversation ID</th>
                    <th>Model</th>
                    <th>Tools</th>
                    <th>Tokens</th>
                    <th>Latency</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredFlatLogs.length === 0 ? (
                    <tr>
                      <td colSpan={10} className="text-center py-6 text-muted">
                        No matching interaction logs found.
                      </td>
                    </tr>
                  ) : (
                    filteredFlatLogs.map((log) => (
                      <tr key={log.id}>
                        <td>
                          <span className="text-muted text-sm">
                            {new Date(log.timestamp).toLocaleTimeString()}
                          </span>
                        </td>
                        <td>
                          <span
                            className={`badge ${
                              log.status === 'SUCCESS' ? 'badge-success' : 'badge-error'
                            }`}
                          >
                            {log.status}
                          </span>
                        </td>
                        <td>
                          <code>{log.request_id || log.id}</code>
                        </td>
                        <td>
                          <span className="badge badge-accent">{log.turn_id || '-'}</span>
                        </td>
                        <td>
                          <small className="text-muted">{log.conversation_id || log.session_id}</small>
                        </td>
                        <td>
                          <code>{log.model}</code>
                        </td>
                        <td>
                          {(log.tool_names || []).length > 0 ? (
                            log.tool_names.map((t, idx) => (
                              <span key={idx} className="badge badge-accent" style={{ marginRight: '4px' }}>
                                {t}
                              </span>
                            ))
                          ) : (
                            <span className="text-muted">-</span>
                          )}
                        </td>
                        <td className="font-mono text-sm">{log.total_tokens || 0}</td>
                        <td className="font-mono text-sm">{Math.round(log.latency_ms || 0)}ms</td>
                        <td>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => setSelectedLog(log)}
                          >
                            <Eye size={14} />
                            <span>Inspect</span>
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      <InspectorModal log={selectedLog} onClose={() => setSelectedLog(null)} />
    </div>
  );
}
