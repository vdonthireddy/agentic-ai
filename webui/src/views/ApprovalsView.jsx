import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { 
  ShieldAlert, ShieldCheck, CheckCircle2, XCircle, Clock, 
  RefreshCw, AlertTriangle, ChevronRight, Copy, Check, 
  FileText, Info, Lock, Shield, ArrowUpRight
} from 'lucide-react';

// Helper to format ISO or epoch timestamp into readable localized date/time
const formatTimestamp = (ts) => {
  if (!ts) return '';
  try {
    const d = typeof ts === 'number'
      ? new Date(ts < 1e11 ? ts * 1000 : ts)
      : new Date(ts);
    if (isNaN(d.getTime())) return String(ts);
    return d.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  } catch (e) {
    return String(ts);
  }
};

// Helper for relative time (e.g. just now, 5m ago)
const formatRelativeTime = (ts) => {
  if (!ts) return '';
  try {
    const d = typeof ts === 'number'
      ? new Date(ts < 1e11 ? ts * 1000 : ts)
      : new Date(ts);
    if (isNaN(d.getTime())) return '';
    const now = Date.now();
    const diffSec = Math.floor((now - d.getTime()) / 1000);
    if (diffSec < 0) return '';
    if (diffSec < 45) return 'just now';
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
    return `${Math.floor(diffSec / 86400)}d ago`;
  } catch (e) {
    return '';
  }
};

export default function ApprovalsView({ onRefreshAll }) {
  const [activeSubTab, setActiveSubTab] = useState('pending'); // 'pending' | 'rules' | 'history'
  const [pendingRequests, setPendingRequests] = useState([]);
  const [rules, setRules] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [actionInProgress, setActionInProgress] = useState({});
  const [copiedId, setCopiedId] = useState(null);
  const [now, setNow] = useState(Date.now());

  // Ticking timer for real-time countdown progress bars
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    try {
      const [pendingRes, rulesRes, histRes] = await Promise.all([
        api.getHITLPending().catch(() => ({ pending: [] })),
        api.getHITLRules().catch(() => ({ rules: [] })),
        api.getHITLHistory(50).catch(() => ({ history: [] }))
      ]);

      setPendingRequests(pendingRes.pending || []);
      setRules(rulesRes.rules || []);
      setHistory(histRes.history || []);
    } catch (e) {
      console.error('Failed to load HITL data', e);
    } finally {
      setLoading(false);
    }
  };

  // Periodic polling for live queue updates every 2.5s
  useEffect(() => {
    loadAllData();
    const interval = setInterval(async () => {
      try {
        const res = await api.getHITLPending();
        setPendingRequests(res.pending || []);
      } catch (e) { /* ignore */ }
    }, 2500);

    return () => clearInterval(interval);
  }, []);

  const handleApprove = async (requestId) => {
    setActionInProgress(prev => ({ ...prev, [requestId]: 'approving' }));
    try {
      await api.approveHITL(requestId);
      await loadAllData();
      onRefreshAll?.();
    } catch (e) {
      alert(`Approval error: ${e.message}`);
    } finally {
      setActionInProgress(prev => ({ ...prev, [requestId]: null }));
    }
  };

  const handleDeny = async (requestId) => {
    setActionInProgress(prev => ({ ...prev, [requestId]: 'denying' }));
    try {
      await api.denyHITL(requestId);
      await loadAllData();
      onRefreshAll?.();
    } catch (e) {
      alert(`Denial error: ${e.message}`);
    } finally {
      setActionInProgress(prev => ({ ...prev, [requestId]: null }));
    }
  };

  const handleCopy = (id) => {
    navigator.clipboard?.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const getRiskStyle = (level) => {
    const l = (level || 'medium').toLowerCase();
    if (l === 'critical') return { bg: 'rgba(239, 68, 68, 0.2)', text: '#ef4444', border: '#dc2626', label: 'CRITICAL RISK' };
    if (l === 'high') return { bg: 'rgba(244, 63, 94, 0.15)', text: '#f43f5e', border: '#e11d48', label: 'HIGH RISK' };
    if (l === 'low') return { bg: 'rgba(34, 197, 94, 0.15)', text: '#22c55e', border: '#16a34a', label: 'LOW RISK' };
    return { bg: 'rgba(245, 158, 11, 0.15)', text: '#f59e0b', border: '#d97706', label: 'MEDIUM RISK' };
  };

  return (
    <div className="view-container animate-fade-in" style={{ paddingBottom: '40px' }}>
      {/* Header */}
      <div className="view-header flex-between" style={{ marginBottom: '20px' }}>
        <div>
          <h2 className="view-title flex items-center gap-2" style={{ fontSize: '20px', fontWeight: '700' }}>
            <ShieldAlert className="text-rose-400" /> Human-in-the-Loop (HITL) Safety & Approvals
            {pendingRequests.length > 0 && (
              <span style={{
                fontSize: '11px',
                background: '#ef4444',
                color: '#fff',
                padding: '2px 8px',
                borderRadius: '10px',
                fontWeight: '700',
                animation: 'pulse 1.5s infinite'
              }}>
                {pendingRequests.length} PENDING
              </span>
            )}
          </h2>
          <p className="view-subtitle" style={{ color: '#94a3b8', fontSize: '13px', marginTop: '4px' }}>
            Real-time control tower to review, approve, or deny intercepted AI agent actions and workflow DAG safety gates.
          </p>
        </div>

        <button 
          className="btn btn-secondary" 
          onClick={loadAllData} 
          disabled={loading}
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
          <span>Refresh All</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px', marginBottom: '24px' }}>
        <div className="glass-card" style={{ padding: '16px', borderRadius: '12px', border: pendingRequests.length > 0 ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ fontSize: '11px', color: '#94a3b8', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Active Pending Queue
          </div>
          <div style={{ fontSize: '24px', fontWeight: '700', color: pendingRequests.length > 0 ? '#ef4444' : '#22c55e', marginTop: '6px' }}>
            {pendingRequests.length}
          </div>
          <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
            {pendingRequests.length > 0 ? 'Awaiting human authorization' : 'All systems clear'}
          </div>
        </div>

        <div className="glass-card" style={{ padding: '16px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ fontSize: '11px', color: '#94a3b8', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Registered Safety Rules
          </div>
          <div style={{ fontSize: '24px', fontWeight: '700', color: '#818cf8', marginTop: '6px' }}>
            {rules.length}
          </div>
          <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
            Protected tools & financial gates
          </div>
        </div>

        <div className="glass-card" style={{ padding: '16px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ fontSize: '11px', color: '#94a3b8', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Audited Resolutions
          </div>
          <div style={{ fontSize: '24px', fontWeight: '700', color: '#38bdf8', marginTop: '6px' }}>
            {history.length}
          </div>
          <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
            Approved, denied, or expired actions
          </div>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid rgba(255,255,255,0.08)', marginBottom: '20px' }}>
        <button
          onClick={() => setActiveSubTab('pending')}
          style={{
            background: activeSubTab === 'pending' ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
            border: 'none',
            borderBottom: activeSubTab === 'pending' ? '2px solid #6366f1' : '2px solid transparent',
            color: activeSubTab === 'pending' ? '#818cf8' : '#94a3b8',
            padding: '10px 18px',
            fontSize: '13px',
            fontWeight: '600',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <ShieldAlert size={16} />
          <span>Pending Approvals</span>
          {pendingRequests.length > 0 && (
            <span style={{
              background: '#ef4444',
              color: '#fff',
              borderRadius: '9999px',
              padding: '1px 6px',
              fontSize: '11px'
            }}>
              {pendingRequests.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveSubTab('rules')}
          style={{
            background: activeSubTab === 'rules' ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
            border: 'none',
            borderBottom: activeSubTab === 'rules' ? '2px solid #6366f1' : '2px solid transparent',
            color: activeSubTab === 'rules' ? '#818cf8' : '#94a3b8',
            padding: '10px 18px',
            fontSize: '13px',
            fontWeight: '600',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <Lock size={16} />
          <span>Safety Policy Rules ({rules.length})</span>
        </button>

        <button
          onClick={() => setActiveSubTab('history')}
          style={{
            background: activeSubTab === 'history' ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
            border: 'none',
            borderBottom: activeSubTab === 'history' ? '2px solid #6366f1' : '2px solid transparent',
            color: activeSubTab === 'history' ? '#818cf8' : '#94a3b8',
            padding: '10px 18px',
            fontSize: '13px',
            fontWeight: '600',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <Clock size={16} />
          <span>Audit History Ledger ({history.length})</span>
        </button>
      </div>

      {/* Sub-Tab 1: Pending Approvals Queue */}
      {activeSubTab === 'pending' && (
        <div>
          {pendingRequests.length === 0 ? (
            <div className="glass-card" style={{
              padding: '48px 24px',
              textAlign: 'center',
              borderRadius: '16px',
              border: '1px dashed rgba(34, 197, 94, 0.3)',
              background: 'rgba(15, 23, 42, 0.4)'
            }}>
              <CheckCircle2 size={48} className="text-emerald-400" style={{ margin: '0 auto 16px', opacity: 0.8 }} />
              <h3 style={{ fontSize: '18px', fontWeight: '600', color: '#f8fafc', margin: '0 0 6px' }}>
                All Clear — No Pending Approvals
              </h3>
              <p style={{ fontSize: '13px', color: '#94a3b8', maxWidth: '480px', margin: '0 auto', lineHeight: '1.5' }}>
                The autonomous AI agent and Workflow Canvas DAGs can execute without human pauses. Whenever a protected tool (e.g. file deletion, memory wipe) or a DAG approval gate is reached, it will appear here immediately for review.
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {pendingRequests.map((req) => {
                const risk = getRiskStyle(req.risk_level);
                const createdMs = (req.created_at || 0) * 1000;
                const timeoutSec = req.timeout_seconds !== undefined ? req.timeout_seconds : 1200;
                const isInfinite = timeoutSec <= 0;
                const elapsedSec = (now - createdMs) / 1000;
                const remainingSec = isInfinite ? Infinity : Math.max(0, Math.ceil(timeoutSec - elapsedSec));
                const progressPct = isInfinite ? 100 : Math.max(0, Math.min(100, (remainingSec / timeoutSec) * 100));

                const formatCountdown = (secs) => {
                  if (secs === Infinity) return 'Infinite (No Timeout)';
                  if (secs <= 0) return 'Auto-Denied (Timed Out)';
                  const m = Math.floor(secs / 60);
                  const s = secs % 60;
                  if (m > 0) return `${m}m ${s}s (${secs}s)`;
                  return `${secs}s`;
                };

                return (
                  <div
                    key={req.request_id}
                    className="glass-card"
                    style={{
                      borderRadius: '14px',
                      border: `1px solid ${risk.border}`,
                      padding: '20px 24px',
                      background: 'rgba(26, 26, 46, 0.7)',
                      boxShadow: '0 10px 30px rgba(0,0,0,0.4)',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    {/* Top Row: Tool, Risk, ID */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', marginBottom: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{
                          background: risk.bg,
                          color: risk.text,
                          border: `1px solid ${risk.border}`,
                          borderRadius: '6px',
                          padding: '3px 10px',
                          fontSize: '11px',
                          fontWeight: '700',
                          letterSpacing: '0.5px'
                        }}>
                          {risk.label}
                        </span>

                        <span style={{
                          fontFamily: 'monospace',
                          fontSize: '14px',
                          fontWeight: '700',
                          color: '#f8fafc',
                          background: 'rgba(0,0,0,0.3)',
                          padding: '3px 8px',
                          borderRadius: '6px'
                        }}>
                          {req.tool_name}
                        </span>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                        {req.created_at && (
                          <div
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '5px',
                              fontSize: '11px',
                              color: '#cbd5e1',
                              background: 'rgba(255, 255, 255, 0.05)',
                              border: '1px solid rgba(255, 255, 255, 0.08)',
                              padding: '3px 8px',
                              borderRadius: '6px'
                            }}
                            title={`Submitted: ${formatTimestamp(req.created_at)}`}
                          >
                            <Clock size={12} style={{ color: '#818cf8', flexShrink: 0 }} />
                            <span>{formatTimestamp(req.created_at)}</span>
                            {formatRelativeTime(req.created_at) && (
                              <span style={{ color: '#94a3b8', fontSize: '10px' }}>
                                ({formatRelativeTime(req.created_at)})
                              </span>
                            )}
                          </div>
                        )}

                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <span style={{ fontFamily: 'monospace', fontSize: '11px', color: '#94a3b8' }}>
                            ID: {req.request_id}
                          </span>
                          <button
                            onClick={() => handleCopy(req.request_id)}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              color: copiedId === req.request_id ? '#22c55e' : '#94a3b8',
                              cursor: 'pointer',
                              padding: '2px 4px'
                            }}
                            title="Copy Request ID"
                          >
                            {copiedId === req.request_id ? <Check size={14} /> : <Copy size={14} />}
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* Reason / Prompt */}
                    <div style={{ marginBottom: '14px' }}>
                      <p style={{ margin: 0, fontSize: '13px', color: '#e2e8f0', lineHeight: '1.5' }}>
                        {req.description || 'Action requires human approval before proceeding.'}
                      </p>
                    </div>

                    {/* Arguments Box */}
                    {req.arguments && (
                      <div style={{ marginBottom: '16px' }}>
                        <div style={{ fontSize: '11px', color: '#94a3b8', fontWeight: '600', textTransform: 'uppercase', marginBottom: '4px' }}>
                          Protected Action Arguments:
                        </div>
                        <pre style={{
                          margin: 0,
                          padding: '10px 14px',
                          borderRadius: '8px',
                          background: 'rgba(0, 0, 0, 0.4)',
                          color: '#cbd5e1',
                          fontFamily: 'monospace',
                          fontSize: '12px',
                          overflowX: 'auto',
                          maxHeight: '140px'
                        }}>
                          {JSON.stringify(req.arguments, null, 2)}
                        </pre>
                      </div>
                    )}

                    {/* Countdown Progress Bar */}
                    <div style={{ marginBottom: '18px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', fontFamily: 'monospace', marginBottom: '4px' }}>
                        <span style={{ color: isInfinite ? '#38bdf8' : remainingSec <= 30 ? '#ef4444' : remainingSec <= 120 ? '#f59e0b' : '#94a3b8' }}>
                          {isInfinite ? '♾️ Infinite approval window (No timeout)' : `⏳ Auto-denies in ${formatCountdown(remainingSec)} if unresolved`}
                        </span>
                        <span style={{ color: '#64748b' }}>
                          Timeout: {isInfinite ? 'Infinite (0s)' : `${timeoutSec}s (${Math.round(timeoutSec / 60)}m)`}
                        </span>
                      </div>
                      <div style={{ height: '4px', background: 'rgba(255,255,255,0.06)', borderRadius: '2px', overflow: 'hidden' }}>
                        <div style={{
                          width: `${progressPct}%`,
                          height: '100%',
                          background: isInfinite ? '#38bdf8' : remainingSec <= 30 ? '#ef4444' : remainingSec <= 120 ? '#f59e0b' : '#3b82f6',
                          transition: 'width 1s linear, background 0.3s'
                        }} />
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                      <button
                        onClick={() => handleDeny(req.request_id)}
                        disabled={actionInProgress[req.request_id] !== undefined && actionInProgress[req.request_id] !== null}
                        style={{
                          background: 'rgba(239, 68, 68, 0.15)',
                          border: '1px solid rgba(239, 68, 68, 0.3)',
                          color: '#ef4444',
                          padding: '8px 20px',
                          borderRadius: '8px',
                          fontSize: '13px',
                          fontWeight: '600',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}
                      >
                        <XCircle size={15} />
                        {actionInProgress[req.request_id] === 'denying' ? 'Denying...' : '✕ Deny Request'}
                      </button>

                      <button
                        onClick={() => handleApprove(req.request_id)}
                        disabled={actionInProgress[req.request_id] !== undefined && actionInProgress[req.request_id] !== null}
                        style={{
                          background: 'linear-gradient(135deg, #22c55e, #16a34a)',
                          border: 'none',
                          color: '#fff',
                          padding: '8px 24px',
                          borderRadius: '8px',
                          fontSize: '13px',
                          fontWeight: '600',
                          cursor: 'pointer',
                          boxShadow: '0 4px 14px rgba(34, 197, 94, 0.35)',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}
                      >
                        <CheckCircle2 size={15} />
                        {actionInProgress[req.request_id] === 'approving' ? 'Approving...' : '✓ Approve Action'}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Sub-Tab 2: Safety Rules Registry */}
      {activeSubTab === 'rules' && (
        <div className="glass-card" style={{ borderRadius: '14px', padding: '20px' }}>
          <div style={{ marginBottom: '16px' }}>
            <h3 style={{ fontSize: '15px', fontWeight: '600', color: '#f8fafc', margin: '0 0 4px' }}>
              Active Safety Policy Rules
            </h3>
            <p style={{ fontSize: '12px', color: '#94a3b8', margin: 0 }}>
              These rules are checked before tool execution and DAG stage dispatch to halt operations until an operator signs off.
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {rules.map((rule, idx) => {
              const risk = getRiskStyle(rule.risk_level);
              return (
                <div
                  key={idx}
                  style={{
                    padding: '14px 18px',
                    borderRadius: '10px',
                    background: 'rgba(15, 23, 42, 0.5)',
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '12px'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{
                      background: risk.bg,
                      color: risk.text,
                      border: `1px solid ${risk.border}`,
                      borderRadius: '6px',
                      padding: '2px 8px',
                      fontSize: '10px',
                      fontWeight: '700'
                    }}>
                      {risk.label}
                    </span>
                    <div>
                      <div style={{ fontFamily: 'monospace', fontWeight: '600', color: '#f1f5f9', fontSize: '13px' }}>
                        {rule.tool_name}
                      </div>
                      <div style={{ color: '#94a3b8', fontSize: '12px', marginTop: '2px' }}>
                        {rule.description || 'Protected by Human-in-the-Loop policy'}
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '12px', color: '#cbd5e1' }}>
                    {rule.action_filter && (
                      <span style={{ background: 'rgba(255,255,255,0.06)', padding: '2px 8px', borderRadius: '4px', fontFamily: 'monospace', fontSize: '11px' }}>
                        Filter: {rule.action_filter.join(', ')}
                      </span>
                    )}
                    <span style={{ fontFamily: 'monospace', color: '#818cf8' }}>
                      Timeout: {rule.timeout_seconds <= 0 ? 'Infinite (0s)' : `${rule.timeout_seconds}s (${Math.round(rule.timeout_seconds / 60)}m)`}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Sub-Tab 3: History & Audit Ledger */}
      {activeSubTab === 'history' && (
        <div className="glass-card" style={{ borderRadius: '14px', padding: '20px' }}>
          <div style={{ marginBottom: '16px' }}>
            <h3 style={{ fontSize: '15px', fontWeight: '600', color: '#f8fafc', margin: '0 0 4px' }}>
              Historical Approval Resolutions
            </h3>
            <p style={{ fontSize: '12px', color: '#94a3b8', margin: 0 }}>
              Chronological ledger of previously approved, denied, or timed-out requests with operator identities.
            </p>
          </div>

          {history.length === 0 ? (
            <div style={{ padding: '32px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
              No historical approval events recorded yet.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {history.map((h, idx) => {
                const statusStyles = {
                  approved: { bg: 'rgba(34, 197, 94, 0.15)', text: '#4ade80', label: 'APPROVED' },
                  denied: { bg: 'rgba(239, 68, 68, 0.15)', text: '#f87171', label: 'DENIED' },
                  expired: { bg: 'rgba(245, 158, 11, 0.15)', text: '#fbbf24', label: 'EXPIRED' }
                };
                const st = statusStyles[h.status] || statusStyles.expired;
                const dateStr = h.created_at ? formatTimestamp(h.created_at) : '';
                const relStr = h.created_at ? formatRelativeTime(h.created_at) : '';

                return (
                  <div
                    key={h.request_id || idx}
                    style={{
                      padding: '12px 16px',
                      borderRadius: '8px',
                      background: 'rgba(15, 23, 42, 0.45)',
                      border: '1px solid rgba(255, 255, 255, 0.05)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '10px'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{
                        background: st.bg,
                        color: st.text,
                        borderRadius: '6px',
                        padding: '2px 8px',
                        fontSize: '10px',
                        fontWeight: '700'
                      }}>
                        {st.label}
                      </span>
                      <div>
                        <div style={{ fontSize: '13px', fontWeight: '600', color: '#f1f5f9' }}>
                          {h.tool_name}
                        </div>
                        <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>
                          {h.description || 'Request ID: ' + h.request_id}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '11px', color: '#64748b' }}>
                      {h.resolved_by && (
                        <span>By: <strong style={{ color: '#cbd5e1' }}>{h.resolved_by}</strong></span>
                      )}
                      {dateStr && (
                        <span style={{ display: 'flex', alignItems: 'center', gap: '5px', color: '#94a3b8' }}>
                          <Clock size={12} style={{ color: '#818cf8', flexShrink: 0 }} />
                          {dateStr}
                          {relStr && <span style={{ color: '#64748b', fontSize: '10px' }}>({relStr})</span>}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
