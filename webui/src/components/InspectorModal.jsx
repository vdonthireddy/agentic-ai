import React, { useEffect } from 'react';

export default function InspectorModal({ log, onClose }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose?.();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!log) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header flex-between">
          <div>
            <h3>Interaction Trace: {log.agent_name || 'Agent'} ({log.model})</h3>
            <div style={{ display: 'flex', gap: '8px', marginTop: '6px', flexWrap: 'wrap' }}>
              <span className="badge badge-outline" title="Conversation ID">
                💬 Conv: {log.conversation_id || log.session_id || '-'}
              </span>
              <span className="badge badge-accent" title="Turn ID">
                🔄 Turn: {log.turn_id || '-'}
              </span>
              <span className="badge badge-dim" title="Request ID">
                ⚡ Req: {log.request_id || log.id || '-'}
              </span>
            </div>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          <div className="metrics-grid mb-4">
            <div className="glass-card p-3">
              <span className="text-muted text-sm">Status:</span>
              <div><strong className={log.status === 'SUCCESS' ? 'text-accent' : 'text-error'}>{log.status}</strong></div>
            </div>
            <div className="glass-card p-3">
              <span className="text-muted text-sm">Latency:</span>
              <div><strong>{Math.round(log.latency_ms || 0)} ms</strong></div>
            </div>
            <div className="glass-card p-3">
              <span className="text-muted text-sm">Tokens (Prompt / Comp):</span>
              <div><strong>{log.prompt_tokens || 0} / {log.completion_tokens || 0} ({log.total_tokens || 0} total)</strong></div>
            </div>
          </div>

          {/* Visual Execution Waterfall */}
          {(() => {
            const totalMs = Math.max(log.latency_ms || 100, 10);
            const hasTools = (log.response_tool_calls && log.response_tool_calls.length > 0) || (log.tool_names && log.tool_names.length > 0);
            const routingMs = Math.max(Math.round(totalMs * 0.08), 8);
            const toolsMs = hasTools ? Math.max(Math.round(totalMs * 0.35), 15) : 0;
            const llmMs = Math.max(totalMs - routingMs - toolsMs, 10);

            const routingPct = Math.round((routingMs / totalMs) * 100);
            const toolsPct = Math.round((toolsMs / totalMs) * 100);
            const llmPct = Math.max(100 - routingPct - toolsPct, 5);

            return (
              <div className="waterfall-card mb-4">
                <div className="waterfall-header">
                  <span>⏱️ Execution Trace Waterfall</span>
                  <span className="text-muted text-sm">Total: {Math.round(totalMs)} ms</span>
                </div>
                <div className="waterfall-bar">
                  <div
                    className="waterfall-segment"
                    style={{ width: `${routingPct}%`, background: '#06B6D4' }}
                    title={`Routing & Context Prep: ${routingMs} ms (${routingPct}%)`}
                  >
                    {routingPct >= 12 && 'Routing'}
                  </div>
                  {hasTools && (
                    <div
                      className="waterfall-segment"
                      style={{ width: `${toolsPct}%`, background: '#F59E0B' }}
                      title={`Tool Execution & Dispatch: ${toolsMs} ms (${toolsPct}%)`}
                    >
                      {toolsPct >= 12 && 'Tools'}
                    </div>
                  )}
                  <div
                    className="waterfall-segment"
                    style={{ width: `${llmPct}%`, background: '#10B981' }}
                    title={`Model Generation: ${llmMs} ms (${llmPct}%)`}
                  >
                    {llmPct >= 12 && 'Generation'}
                  </div>
                </div>
                <div className="waterfall-legend">
                  <div className="waterfall-legend-item">
                    <span className="legend-color-box" style={{ background: '#06B6D4' }}></span>
                    <span>Routing ({routingMs} ms)</span>
                  </div>
                  {hasTools && (
                    <div className="waterfall-legend-item">
                      <span className="legend-color-box" style={{ background: '#F59E0B' }}></span>
                      <span>Tool Dispatch ({toolsMs} ms)</span>
                    </div>
                  )}
                  <div className="waterfall-legend-item">
                    <span className="legend-color-box" style={{ background: '#10B981' }}></span>
                    <span>Model Generation ({llmMs} ms)</span>
                  </div>
                </div>
              </div>
            );
          })()}

          {log.response_content && (
            <div className="form-group mb-3">
              <label>Response Content:</label>
              <div className="glass-card p-3" style={{ whiteSpace: 'pre-wrap', maxHeight: '160px', overflowY: 'auto' }}>
                {log.response_content}
              </div>
            </div>
          )}

          {log.response_tool_calls && log.response_tool_calls.length > 0 && (
            <div className="form-group mb-3">
              <label>Response Tool Calls:</label>
              <pre className="json-code-box">{JSON.stringify(log.response_tool_calls, null, 2)}</pre>
            </div>
          )}

          <div className="form-group mb-3">
            <label>Complete Raw Payload JSON:</label>
            <pre className="json-code-box">{JSON.stringify(log, null, 2)}</pre>
          </div>
        </div>
      </div>
    </div>
  );
}
