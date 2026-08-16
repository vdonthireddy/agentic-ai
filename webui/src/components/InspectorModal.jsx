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
