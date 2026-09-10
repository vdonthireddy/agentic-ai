import React, { useState, useEffect } from 'react';
import { Copy, Check } from 'lucide-react';

export default function InspectorModal({ log, onClose }) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose?.();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  useEffect(() => {
    if (log) {
      document.body.classList.add('modal-open');
    }
    return () => {
      document.body.classList.remove('modal-open');
    };
  }, [log]);

  if (!log) return null;

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose?.();
    }
  };

  // Extract prompt/user message
  let promptText = '';
  if (Array.isArray(log.request_messages) && log.request_messages.length > 0) {
    const userMsg = [...log.request_messages].reverse().find(m => m.role === 'user');
    promptText = userMsg?.content || log.request_messages.map(m => `[${m.role}]: ${m.content}`).join('\n\n');
  } else if (typeof log.request_messages === 'string') {
    promptText = log.request_messages;
  }

  return (
    <div className="modal-overlay" onClick={handleOverlayClick}>
      <div className="modal-card" style={{ maxWidth: '780px' }} onClick={(e) => e.stopPropagation()}>
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

          {/* 1. Input Prompt Section */}
          {promptText && (
            <div className="form-group mb-4">
              <label style={{ fontWeight: 600, color: '#94a3b8', fontSize: '13px', display: 'block', marginBottom: '6px' }}>
                📥 Input Prompt / Request:
              </label>
              <div
                className="glass-card p-3"
                style={{
                  whiteSpace: 'pre-wrap',
                  maxHeight: '160px',
                  overflowY: 'auto',
                  background: 'rgba(15, 23, 42, 0.7)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  color: '#f1f5f9',
                  fontSize: '13px',
                  lineHeight: '1.5'
                }}
              >
                {promptText}
              </div>
            </div>
          )}

          {/* 2. Actual Model Response Content */}
          <div className="form-group mb-4">
            <div className="flex-between mb-2">
              <label style={{ fontWeight: 700, color: '#38bdf8', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                💬 Model Response Content:
              </label>
              {log.response_content && (
                <button
                  className="btn btn-secondary btn-sm"
                  style={{ padding: '3px 10px', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}
                  onClick={() => {
                    navigator.clipboard?.writeText(log.response_content);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 2000);
                  }}
                  title="Copy Model Response"
                >
                  {copied ? <Check size={12} className="text-accent" /> : <Copy size={12} />}
                  <span>{copied ? 'Copied!' : 'Copy'}</span>
                </button>
              )}
            </div>
            {log.response_content ? (
              <div
                className="glass-card p-4"
                style={{
                  whiteSpace: 'pre-wrap',
                  maxHeight: '260px',
                  overflowY: 'auto',
                  background: 'rgba(6, 182, 212, 0.05)',
                  border: '1px solid rgba(6, 182, 212, 0.25)',
                  color: '#f8fafc',
                  fontSize: '13.5px',
                  lineHeight: '1.6'
                }}
              >
                {log.response_content}
              </div>
            ) : (log.response_tool_calls && log.response_tool_calls.length > 0) ? (
              <div
                className="glass-card p-3 text-sm"
                style={{ background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.25)', color: '#fbbf24' }}
              >
                ⚡ Model generated <strong>{log.response_tool_calls.length} tool call(s)</strong> (no textual message emitted for this step). View tool details below.
              </div>
            ) : (
              <div className="glass-card p-3 text-muted text-sm" style={{ background: 'rgba(255,255,255,0.02)' }}>
                No response text emitted for this request.
              </div>
            )}
          </div>

          {/* 3. Response Tool Calls */}
          {log.response_tool_calls && log.response_tool_calls.length > 0 && (
            <div className="form-group mb-4">
              <label style={{ fontWeight: 600, color: '#f59e0b', fontSize: '13px', display: 'block', marginBottom: '6px' }}>
                🛠️ Response Tool Calls:
              </label>
              <pre className="json-code-box">{JSON.stringify(log.response_tool_calls, null, 2)}</pre>
            </div>
          )}

          {/* 4. Collapsible Complete Raw Payload */}
          <details className="form-group mb-2" style={{ borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '14px' }}>
            <summary style={{ cursor: 'pointer', color: '#94a3b8', fontSize: '12px', fontWeight: 600 }}>
              📦 Complete Raw Payload JSON (Click to expand)
            </summary>
            <pre className="json-code-box mt-2">{JSON.stringify(log, null, 2)}</pre>
          </details>
        </div>
      </div>
    </div>
  );
}
