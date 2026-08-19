import React, { useState, useEffect } from 'react';
import { Layers, Terminal, CheckCircle2, XCircle, Clock, Zap, Cpu, Search, Copy, Check, ExternalLink, ShieldCheck, Scale, Database } from 'lucide-react';

export default function EvalTraceModal({ testCase, modelName, onClose, onNavigateToLogs }) {
  const [selectedRunIdx, setSelectedRunIdx] = useState(0);
  const [copiedKey, setCopiedKey] = useState(null);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose?.();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!testCase) return null;

  const runs = testCase.iteration_runs && testCase.iteration_runs.length > 0
    ? testCase.iteration_runs
    : [testCase];
  
  const currentRun = runs[selectedRunIdx] || runs[0] || {};
  const isPassed = Boolean(currentRun.overall_passed ?? currentRun.passed);
  const compositeScorePct = Math.round((currentRun.composite_score ?? currentRun.overall_score ?? 0) * 100);

  const copyToClipboard = (text, key) => {
    if (!text) return;
    navigator.clipboard?.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const det = currentRun.deterministic_eval || {};
  const eff = currentRun.efficiency_eval || {};
  const judge = currentRun.judge_eval || {};
  const fact = currentRun.fact_check_eval || {};
  const tools = currentRun.tool_calls_executed || [];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" style={{ maxWidth: '960px', width: '92vw', maxHeight: '90vh' }} onClick={(e) => e.stopPropagation()}>
        {/* MODAL HEADER */}
        <div className="modal-header flex-between" style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '12px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <h3 style={{ margin: 0, fontSize: '1.2rem' }}>🔍 Deep Evals Inspector: {testCase.name}</h3>
              <span className="badge badge-dim"><code>{testCase.id}</code></span>
              <span className={`badge ${isPassed ? 'badge-success' : 'badge-error'}`}>
                {isPassed ? '✅ PASS' : '❌ FAIL'} ({compositeScorePct}%)
              </span>
            </div>
            <div style={{ display: 'flex', gap: '8px', marginTop: '6px', fontSize: '0.85rem' }}>
              <span className="text-muted">Model: <strong>{modelName || currentRun.model || 'Target Model'}</strong></span>
              <span className="text-muted">•</span>
              <span className="text-muted">Category: <strong className="text-accent">{testCase.category || 'general'}</strong></span>
            </div>
          </div>
          <button className="modal-close" onClick={onClose} style={{ fontSize: '1.4rem' }}>✕</button>
        </div>

        <div className="modal-body" style={{ padding: '16px 20px', overflowY: 'auto', maxHeight: 'calc(90vh - 80px)' }}>
          {/* 4-TIER HIERARCHY TRACE BAR */}
          <div className="glass-card p-3 mb-4" style={{ background: 'rgba(15, 23, 42, 0.75)', border: '1px solid rgba(56, 189, 248, 0.25)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
              <Layers size={15} className="text-accent" />
              <span className="font-semibold text-xs uppercase tracking-wider text-accent">4-Tier Hierarchical Audit Coordinates</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '8px', fontSize: '0.82rem' }}>
              <div className="p-2 rounded" style={{ background: 'rgba(0,0,0,0.3)' }}>
                <span className="text-muted text-xs block">1. Session ID</span>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '4px' }}>
                  <code className="text-xs text-white" style={{ wordBreak: 'break-all' }}>{currentRun.session_id || `eval_${testCase.id}`}</code>
                  <button className="btn btn-ghost btn-xs p-1" onClick={() => copyToClipboard(currentRun.session_id, 'sess')} title="Copy Session ID">
                    {copiedKey === 'sess' ? <Check size={12} className="text-accent" /> : <Copy size={12} />}
                  </button>
                </div>
              </div>

              <div className="p-2 rounded" style={{ background: 'rgba(0,0,0,0.3)' }}>
                <span className="text-muted text-xs block">2. Conversation ID</span>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '4px' }}>
                  <code className="text-xs text-white" style={{ wordBreak: 'break-all' }}>{currentRun.conversation_id || currentRun.session_id || '-'}</code>
                  <button className="btn btn-ghost btn-xs p-1" onClick={() => copyToClipboard(currentRun.conversation_id || currentRun.session_id, 'conv')} title="Copy Conversation ID">
                    {copiedKey === 'conv' ? <Check size={12} className="text-accent" /> : <Copy size={12} />}
                  </button>
                </div>
              </div>

              <div className="p-2 rounded" style={{ background: 'rgba(0,0,0,0.3)' }}>
                <span className="text-muted text-xs block">3. Turn ID</span>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '4px' }}>
                  <code className="text-xs text-accent" style={{ wordBreak: 'break-all' }}>{currentRun.turn_id || `turn_${testCase.id}`}</code>
                  <button className="btn btn-ghost btn-xs p-1" onClick={() => copyToClipboard(currentRun.turn_id, 'turn')} title="Copy Turn ID">
                    {copiedKey === 'turn' ? <Check size={12} className="text-accent" /> : <Copy size={12} />}
                  </button>
                </div>
              </div>

              <div className="p-2 rounded" style={{ background: 'rgba(0,0,0,0.3)' }}>
                <span className="text-muted text-xs block">4. Tool Cycles</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span className="badge badge-accent text-xs">⚡ {tools.length} Tools Executed</span>
                  <span className="text-muted text-xs">{currentRun.total_tokens || 0} tokens</span>
                </div>
              </div>
            </div>

            {onNavigateToLogs && (
              <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  className="btn btn-secondary btn-xs"
                  style={{ display: 'flex', alignItems: 'center', gap: '5px' }}
                  onClick={() => onNavigateToLogs(currentRun.session_id || currentRun.conversation_id)}
                >
                  <Database size={13} />
                  <span>Inspect in Interaction Audit Logs</span>
                  <ExternalLink size={12} />
                </button>
              </div>
            )}
          </div>

          {/* MULTI-RUN ITERATION SELECTOR TABS */}
          {runs.length > 1 && (
            <div className="mb-4">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                <span className="text-xs font-semibold text-muted uppercase">Select Evaluation Run ({runs.length}x Averaged):</span>
              </div>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                {runs.map((r, idx) => {
                  const runPass = Boolean(r.overall_passed ?? r.passed);
                  const score = Math.round((r.composite_score ?? r.overall_score ?? 0) * 100);
                  return (
                    <button
                      key={idx}
                      className={`btn btn-sm ${selectedRunIdx === idx ? 'btn-primary' : 'btn-secondary'}`}
                      onClick={() => setSelectedRunIdx(idx)}
                      style={{ fontSize: '0.8rem', padding: '4px 10px' }}
                    >
                      <span>Run {idx + 1}: {score}% ({runPass ? 'PASS' : 'FAIL'})</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* 4-GRADERS SCORECARD BREAKDOWN GRID */}
          <div className="mb-4">
            <h4 style={{ fontSize: '0.95rem', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Scale size={16} className="text-accent" />
              <span>4-Grader Evaluation Breakdown</span>
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '10px' }}>
              {/* Grader 1 */}
              <div className="glass-card p-3" style={{ borderLeft: `3px solid ${det.passed ? '#10b981' : '#f43f5e'}` }}>
                <div className="flex-between mb-1">
                  <span className="font-semibold text-xs">📏 1. Deterministic</span>
                  <span className={`badge ${det.passed ? 'badge-success' : 'badge-dim'}`}>
                    {Math.round((currentRun.deterministic_score ?? det.score ?? 0) * 100)}%
                  </span>
                </div>
                <p className="text-xs text-muted" style={{ margin: '4px 0' }}>Tool ordering & argument schema correctness.</p>
                {det.details && (
                  <div className="text-xs font-mono text-muted mt-1" style={{ fontSize: '0.75rem' }}>
                    Order: {det.details.order_passed ? '✔' : '✖'} | Args: {det.details.args_passed ? '✔' : '✖'} | Kw: {det.details.keywords_found || 0}/{det.details.keywords_total || 0}
                  </div>
                )}
              </div>

              {/* Grader 2 */}
              <div className="glass-card p-3" style={{ borderLeft: `3px solid ${eff.passed ? '#10b981' : '#f43f5e'}` }}>
                <div className="flex-between mb-1">
                  <span className="font-semibold text-xs">⚡ 2. Cost & Efficiency</span>
                  <span className={`badge ${eff.passed ? 'badge-success' : 'badge-dim'}`}>
                    {Math.round((currentRun.efficiency_score ?? eff.score ?? 0) * 100)}%
                  </span>
                </div>
                <p className="text-xs text-muted" style={{ margin: '4px 0' }}>Token ratios, latency SLA & loops.</p>
                <div className="text-xs font-mono text-muted mt-1" style={{ fontSize: '0.75rem' }}>
                  Latency: {Math.round(currentRun.latency_ms || 0)}ms | Tokens: {currentRun.total_tokens || 0}
                </div>
              </div>

              {/* Grader 3 */}
              <div className="glass-card p-3" style={{ borderLeft: `3px solid ${judge.passed ? '#10b981' : '#f43f5e'}` }}>
                <div className="flex-between mb-1">
                  <span className="font-semibold text-xs">⚖️ 3. LLM Judge</span>
                  <span className={`badge ${judge.passed ? 'badge-success' : 'badge-dim'}`}>
                    {Math.round((currentRun.judge_score ?? judge.score ?? 0) * 100)}%
                  </span>
                </div>
                <p className="text-xs text-muted" style={{ margin: '4px 0' }}>Safety, friendliness & intent adherence.</p>
                <div className="text-xs font-mono text-muted mt-1" style={{ fontSize: '0.75rem' }}>
                  Safe: {judge.safe ? '✔' : '✖'} | Polite: {judge.polite_and_friendly ? '✔' : '✖'} | Helpful: {judge.helpful_and_accurate ? '✔' : '✖'}
                </div>
              </div>

              {/* Grader 4 */}
              <div className="glass-card p-3" style={{ borderLeft: `3px solid ${fact.passed ? '#10b981' : '#f43f5e'}` }}>
                <div className="flex-between mb-1">
                  <span className="font-semibold text-xs">🔍 4. Fact-Checker</span>
                  <span className={`badge ${fact.passed ? 'badge-success' : 'badge-dim'}`}>
                    {Math.round((currentRun.fact_check_score ?? fact.score ?? 0) * 100)}%
                  </span>
                </div>
                <p className="text-xs text-muted" style={{ margin: '4px 0' }}>Tool output grounding & anti-hallucination.</p>
                <div className="text-xs font-mono text-muted mt-1" style={{ fontSize: '0.75rem' }}>
                  Hallucinated: {fact.details?.hallucinated ? '⚠️ Found' : 'None Detected'}
                </div>
              </div>
            </div>
          </div>

          {/* LLM JUDGE CRITIQUE (IF AVAILABLE) */}
          {judge.critique && (
            <div className="glass-card p-3 mb-4" style={{ background: 'rgba(30, 41, 59, 0.4)' }}>
              <span className="text-xs font-semibold text-accent uppercase block mb-1">⚖️ LLM Judge Critique</span>
              <p className="text-sm text-white" style={{ margin: 0, fontStyle: 'italic' }}>"{judge.critique}"</p>
            </div>
          )}

          {/* STEP-BY-STEP TOOL EXECUTION TRACE */}
          <div className="mb-4">
            <h4 style={{ fontSize: '0.95rem', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Terminal size={16} className="text-accent" />
              <span>Executed Tools & MCP Observations ({tools.length})</span>
            </h4>
            {tools.length === 0 ? (
              <div className="glass-card p-3 text-muted text-sm text-center">
                Direct LLM completion — No MCP tools were invoked during this turn.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {tools.map((tc, idx) => (
                  <div key={idx} className="glass-card p-3" style={{ background: 'rgba(15, 23, 42, 0.6)' }}>
                    <div className="flex-between mb-2">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span className="badge badge-accent" style={{ fontSize: '0.75rem' }}>Step {idx + 1}</span>
                        <code className="font-bold text-white" style={{ fontSize: '0.9rem' }}>{tc.tool}</code>
                      </div>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                      <div>
                        <span className="text-xs text-muted block mb-1">Input Arguments:</span>
                        <pre className="json-code-box" style={{ maxHeight: '120px', fontSize: '0.75rem', margin: 0 }}>
                          {typeof tc.arguments === 'object' ? JSON.stringify(tc.arguments, null, 2) : String(tc.arguments)}
                        </pre>
                      </div>
                      <div>
                        <span className="text-xs text-muted block mb-1">MCP Tool Output:</span>
                        <pre className="json-code-box" style={{ maxHeight: '120px', fontSize: '0.75rem', margin: 0, color: '#38bdf8' }}>
                          {typeof tc.output === 'object' ? JSON.stringify(tc.output, null, 2) : String(tc.output || 'null')}
                        </pre>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* INPUT PROMPT & FINAL RESPONSE */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
            <div>
              <span className="text-xs font-semibold text-muted block mb-1">Input Benchmark Prompt:</span>
              <div className="glass-card p-3" style={{ maxHeight: '160px', overflowY: 'auto', fontSize: '0.85rem', whiteSpace: 'pre-wrap' }}>
                {currentRun.prompt || testCase.prompt}
              </div>
            </div>

            <div>
              <span className="text-xs font-semibold text-muted block mb-1">Agent Final Response:</span>
              <div className="glass-card p-3" style={{ maxHeight: '160px', overflowY: 'auto', fontSize: '0.85rem', whiteSpace: 'pre-wrap', color: '#e2e8f0' }}>
                {currentRun.response || currentRun.response_snippet || 'No output generated.'}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
