import React, { useState, useEffect, useRef } from 'react';

export default function HITLApprovalModal({ request, onApprove, onDeny, onClose }) {
  const [countdown, setCountdown] = useState(Math.ceil(request?.timeout_seconds || 60));
  const intervalRef = useRef(null);

  useEffect(() => {
    if (!request) return;
    const startTime = Date.now();
    const timeout = (request.timeout_seconds || 60) * 1000;

    intervalRef.current = setInterval(() => {
      const remaining = Math.ceil((timeout - (Date.now() - startTime)) / 1000);
      if (remaining <= 0) {
        clearInterval(intervalRef.current);
        setCountdown(0);
        // Auto-deny on timeout
        if (onDeny) onDeny(request.request_id);
      } else {
        setCountdown(remaining);
      }
    }, 1000);

    return () => clearInterval(intervalRef.current);
  }, [request]);

  if (!request) return null;

  const riskColors = {
    low: { bg: 'rgba(34,197,94,0.15)', border: 'rgba(34,197,94,0.3)', text: '#22c55e', label: 'LOW' },
    medium: { bg: 'rgba(245,158,11,0.15)', border: 'rgba(245,158,11,0.3)', text: '#f59e0b', label: 'MEDIUM' },
    high: { bg: 'rgba(239,68,68,0.15)', border: 'rgba(239,68,68,0.3)', text: '#ef4444', label: 'HIGH' },
    critical: { bg: 'rgba(220,38,38,0.2)', border: 'rgba(220,38,38,0.5)', text: '#dc2626', label: 'CRITICAL' }
  };
  const risk = riskColors[request.risk_level] || riskColors.medium;

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 10000, animation: 'fadeIn 0.2s ease'
    }}>
      <div style={{
        background: '#1a1a2e', border: `1px solid ${risk.border}`,
        borderRadius: '16px', padding: '28px', width: '480px', maxWidth: '90vw',
        boxShadow: `0 0 40px ${risk.bg}, 0 20px 60px rgba(0,0,0,0.5)`
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
          <div style={{ fontSize: '28px' }}>⚠️</div>
          <div>
            <h3 style={{ color: '#f0f0f0', margin: 0, fontSize: '18px' }}>Safety Approval Required</h3>
            <p style={{ color: '#888', margin: '2px 0 0', fontSize: '12px' }}>
              The AI agent is requesting to perform a protected action
            </p>
          </div>
        </div>

        {/* Risk Badge */}
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: '6px',
          background: risk.bg, border: `1px solid ${risk.border}`,
          borderRadius: '6px', padding: '4px 12px', marginBottom: '16px'
        }}>
          <span style={{ color: risk.text, fontSize: '11px', fontWeight: '700', letterSpacing: '1px' }}>
            {risk.label} RISK
          </span>
        </div>

        {/* Tool Details */}
        <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '10px', padding: '16px', marginBottom: '16px' }}>
          <div style={{ marginBottom: '10px' }}>
            <span style={{ color: '#666', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Tool</span>
            <div style={{ color: '#e0e0e0', fontFamily: 'monospace', fontSize: '14px', marginTop: '2px' }}>{request.tool_name}</div>
          </div>
          <div style={{ marginBottom: '10px' }}>
            <span style={{ color: '#666', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Arguments</span>
            <pre style={{
              color: '#aaa', fontSize: '11px', margin: '4px 0 0', padding: '8px',
              background: 'rgba(0,0,0,0.3)', borderRadius: '6px', overflowX: 'auto',
              maxHeight: '120px', overflowY: 'auto'
            }}>
              {JSON.stringify(request.arguments, null, 2)}
            </pre>
          </div>
          {request.description && (
            <div>
              <span style={{ color: '#666', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Reason</span>
              <p style={{ color: '#ccc', fontSize: '12px', margin: '4px 0 0', lineHeight: '1.4' }}>{request.description}</p>
            </div>
          )}
        </div>

        {/* Countdown */}
        <div style={{ textAlign: 'center', marginBottom: '16px' }}>
          <span style={{
            color: countdown <= 10 ? '#ef4444' : countdown <= 30 ? '#f59e0b' : '#888',
            fontSize: '12px', fontFamily: 'monospace'
          }}>
            Auto-deny in {countdown}s
          </span>
          <div style={{
            width: '100%', height: '3px', background: 'rgba(255,255,255,0.05)',
            borderRadius: '2px', marginTop: '6px', overflow: 'hidden'
          }}>
            <div style={{
              width: `${(countdown / (request.timeout_seconds || 60)) * 100}%`,
              height: '100%',
              background: countdown <= 10 ? '#ef4444' : countdown <= 30 ? '#f59e0b' : '#3b82f6',
              borderRadius: '2px',
              transition: 'width 1s linear, background 0.3s ease'
            }} />
          </div>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={() => onDeny && onDeny(request.request_id)}
            style={{
              flex: 1, padding: '12px', borderRadius: '10px',
              background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)',
              color: '#ef4444', fontSize: '14px', fontWeight: '600', cursor: 'pointer'
            }}
          >
            ✕ Deny
          </button>
          <button
            onClick={() => onApprove && onApprove(request.request_id)}
            style={{
              flex: 1, padding: '12px', borderRadius: '10px',
              background: 'linear-gradient(135deg, #22c55e, #16a34a)',
              border: 'none', color: '#fff', fontSize: '14px', fontWeight: '600', cursor: 'pointer'
            }}
          >
            ✓ Approve
          </button>
        </div>
      </div>
    </div>
  );
}
