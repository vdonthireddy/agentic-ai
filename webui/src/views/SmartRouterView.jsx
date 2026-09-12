import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { 
  GitBranch, 
  Cpu, 
  Zap, 
  CheckCircle2, 
  AlertTriangle, 
  Sliders, 
  History, 
  Play, 
  Copy, 
  Check, 
  Trash2, 
  RefreshCw, 
  Search, 
  ArrowRight, 
  Info,
  Clock,
  Code,
  Brain,
  MessageSquare,
  Sparkles,
  ExternalLink,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

const CATEGORY_COLORS = {
  coding: { bg: 'rgba(59, 130, 246, 0.15)', border: '#3b82f6', text: '#60a5fa', icon: Code },
  complex_work: { bg: 'rgba(168, 85, 247, 0.15)', border: '#a855f7', text: '#c084fc', icon: Brain },
  general_qa: { bg: 'rgba(34, 197, 94, 0.15)', border: '#22c55e', text: '#4ade80', icon: MessageSquare },
  fast_lightweight: { bg: 'rgba(245, 158, 11, 0.15)', border: '#f59e0b', text: '#fbbf24', icon: Zap },
  creative_writing: { bg: 'rgba(236, 72, 153, 0.15)', border: '#ec4899', text: '#f472b6', icon: Sparkles }
};

const SAMPLE_PROMPTS = [
  {
    category: 'coding',
    label: '💻 Python Async Crawler',
    prompt: 'Write an asynchronous Python function using httpx to scrape 5 URLs concurrently with exponential backoff retry.'
  },
  {
    category: 'complex_work',
    label: '🧠 Distributed Consensus',
    prompt: 'Evaluate the architectural trade-offs between Raft vs Paxos for distributed transaction coordination under network partition.'
  },
  {
    category: 'general_qa',
    label: '❓ Rayleigh Scattering',
    prompt: 'Why is the sky blue and how does Rayleigh scattering explain why sunsets appear red?'
  },
  {
    category: 'fast_lightweight',
    label: '⚡ Multilingual Translation',
    prompt: 'Translate this greeting into French, Spanish, and German: "Good morning! Have a productive and wonderful day."'
  },
  {
    category: 'creative_writing',
    label: '✍️ Cyberpunk Opening',
    prompt: 'Write an evocative opening paragraph for a noir science fiction story about an AI awakening in a rain-soaked metropolis.'
  }
];

export default function SmartRouterView({ models = [], defaultModel = 'ollama/llama3.2:latest' }) {
  const [activeSubTab, setActiveSubTab] = useState('playground'); // 'playground' | 'config' | 'logs'
  const [promptInput, setPromptInput] = useState('');
  const [reasoningModelOverride, setReasoningModelOverride] = useState('');
  const [routingResult, setRoutingResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copiedResp, setCopiedResp] = useState(false);
  const [showTargetPrompt, setShowTargetPrompt] = useState(false);

  // Configuration State
  const [config, setConfig] = useState(null);
  const [configSaving, setConfigSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Call Logs State
  const [logs, setLogs] = useState([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsSearch, setLogsSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [selectedLogForModal, setSelectedLogForModal] = useState(null);

  useEffect(() => {
    if (!selectedLogForModal) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' || e.key === 'Esc') {
        setSelectedLogForModal(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedLogForModal]);

  useEffect(() => {
    loadConfig();
    loadLogs();
  }, []);

  const loadConfig = async () => {
    try {
      const data = await api.getSmartRouterConfig();
      setConfig(data);
      if (!reasoningModelOverride && data.default_reasoning_model) {
        setReasoningModelOverride(data.default_reasoning_model);
      }
    } catch (err) {
      console.error('Failed to load Smart Router config', err);
    }
  };

  const loadLogs = async () => {
    setLogsLoading(true);
    try {
      const data = await api.getSmartRouterLogs({
        limit: 50,
        search: logsSearch || undefined,
        category: categoryFilter || undefined
      });
      setLogs(data.logs || []);
    } catch (err) {
      console.error('Failed to load Smart Router logs', err);
    } finally {
      setLogsLoading(false);
    }
  };

  const handleRouteAndExecute = async (e) => {
    if (e) e.preventDefault();
    if (!promptInput.trim() || loading) return;

    setLoading(true);
    setRoutingResult(null);

    try {
      const res = await api.routeSmartPrompt({
        prompt: promptInput.trim(),
        reasoning_model: reasoningModelOverride || undefined
      });
      setRoutingResult(res);
      loadLogs();
    } catch (err) {
      alert('Routing failed: ' + (err.message || err));
    } finally {
      setLoading(false);
    }
  };

  const handleSaveConfig = async (e) => {
    e.preventDefault();
    if (!config || configSaving) return;
    setConfigSaving(true);
    setSaveSuccess(false);

    try {
      const updated = await api.updateSmartRouterConfig(config);
      setConfig(updated);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      alert('Failed to save config: ' + (err.message || err));
    } finally {
      setConfigSaving(false);
    }
  };

  const handleToggleSmartRouting = async () => {
    if (!config) return;
    const newEnabled = !config.enabled;
    const newConfig = { ...config, enabled: newEnabled, use_smart_routing: newEnabled };
    setConfig(newConfig);
    try {
      const updated = await api.updateSmartRouterConfig(newConfig);
      setConfig(updated);
    } catch (err) {
      alert('Failed to update Smart Routing state: ' + (err.message || err));
      loadConfig();
    }
  };

  const handleClearLogs = async () => {
    if (!window.confirm('Are you sure you want to clear all Smart Router execution logs?')) return;
    try {
      await api.clearSmartRouterLogs();
      setLogs([]);
    } catch (err) {
      alert('Failed to clear logs: ' + err.message);
    }
  };

  const copyToClipboard = (text) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedResp(true);
      setTimeout(() => setCopiedResp(false), 2000);
    }
  };

  const activeReasoningModel = reasoningModelOverride || config?.default_reasoning_model || defaultModel || 'ollama/llama3.2:latest';
  const availableModelsList = config?.available_models?.length ? config.available_models : models.map(m => m.id);

  return (
    <div className="smart-router-view" style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto', color: '#f1f5f9' }}>
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
            <div style={{ padding: '8px', background: 'rgba(59, 130, 246, 0.2)', borderRadius: '10px', color: '#60a5fa' }}>
              <GitBranch size={24} />
            </div>
            <h1 style={{ fontSize: '24px', fontWeight: '700', margin: 0 }}>Smart-Router</h1>
            <span style={{ 
              fontSize: '12px', 
              padding: '3px 10px', 
              background: config?.enabled ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)', 
              color: config?.enabled ? '#34d399' : '#fbbf24', 
              borderRadius: '999px', 
              border: `1px solid ${config?.enabled ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
              fontWeight: '600'
            }}>
              {config?.enabled ? 'Active & Online' : 'Disabled (Bypass Mode)'}
            </span>
          </div>
          <p style={{ color: '#94a3b8', fontSize: '14px', margin: 0 }}>
            Dynamic 2-stage reasoning dispatcher: asks the default model to classify task domain and enforce accuracy thresholds before executing on specialized Ollama models.
          </p>
        </div>

        {/* Status Pill with Toggle */}
        <div style={{ 
          background: 'rgba(30, 41, 59, 0.7)', 
          border: '1px solid rgba(255, 255, 255, 0.08)', 
          borderRadius: '12px', 
          padding: '10px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: '16px'
        }}>
          <div>
            <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Reasoning Model</div>
            <div style={{ fontSize: '13px', fontWeight: '600', color: '#38bdf8' }}>{activeReasoningModel}</div>
          </div>
          <div style={{ height: '24px', width: '1px', background: 'rgba(255,255,255,0.1)' }}></div>
          <div>
            <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>USE_SMART_ROUTING</div>
            <button
              onClick={handleToggleSmartRouting}
              type="button"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                background: config?.enabled ? 'rgba(22, 101, 52, 0.6)' : 'rgba(120, 53, 15, 0.6)',
                color: config?.enabled ? '#86efac' : '#fde68a',
                border: `1px solid ${config?.enabled ? '#22c55e' : '#f59e0b'}`,
                borderRadius: '6px',
                padding: '3px 10px',
                fontSize: '12px',
                fontWeight: '700',
                cursor: 'pointer',
                marginTop: '2px',
                transition: 'all 0.2s ease'
              }}
              title="Click to toggle USE_SMART_ROUTING on or off"
            >
              {config?.enabled ? '🟢 ENABLED' : '🟡 DISABLED'}
            </button>
          </div>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '12px', marginBottom: '24px' }}>
        <button
          onClick={() => setActiveSubTab('playground')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 18px',
            borderRadius: '8px',
            background: activeSubTab === 'playground' ? '#2563eb' : 'rgba(30, 41, 59, 0.6)',
            color: activeSubTab === 'playground' ? '#fff' : '#94a3b8',
            border: '1px solid ' + (activeSubTab === 'playground' ? '#3b82f6' : 'rgba(255,255,255,0.05)'),
            fontWeight: '600',
            cursor: 'pointer',
            fontSize: '14px'
          }}
        >
          <Play size={16} />
          Route & Playground
        </button>

        <button
          onClick={() => setActiveSubTab('config')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 18px',
            borderRadius: '8px',
            background: activeSubTab === 'config' ? '#2563eb' : 'rgba(30, 41, 59, 0.6)',
            color: activeSubTab === 'config' ? '#fff' : '#94a3b8',
            border: '1px solid ' + (activeSubTab === 'config' ? '#3b82f6' : 'rgba(255,255,255,0.05)'),
            fontWeight: '600',
            cursor: 'pointer',
            fontSize: '14px'
          }}
        >
          <Sliders size={16} />
          Accuracy Thresholds & Config
        </button>

        <button
          onClick={() => { setActiveSubTab('logs'); loadLogs(); }}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 18px',
            borderRadius: '8px',
            background: activeSubTab === 'logs' ? '#2563eb' : 'rgba(30, 41, 59, 0.6)',
            color: activeSubTab === 'logs' ? '#fff' : '#94a3b8',
            border: '1px solid ' + (activeSubTab === 'logs' ? '#3b82f6' : 'rgba(255,255,255,0.05)'),
            fontWeight: '600',
            cursor: 'pointer',
            fontSize: '14px'
          }}
        >
          <History size={16} />
          Full Call Logs ({logs.length})
        </button>
      </div>

      {/* ====================================================================== */}
      {/* TAB 1: PLAYGROUND & ROUTE EXECUTOR */}
      {/* ====================================================================== */}
      {activeSubTab === 'playground' && (
        <div>
          {/* Disabled Bypass Notice */}
          {config && !config.enabled && (
            <div style={{
              background: 'rgba(245, 158, 11, 0.12)',
              border: '1px solid rgba(245, 158, 11, 0.35)',
              borderRadius: '12px',
              padding: '14px 18px',
              marginBottom: '20px',
              display: 'flex',
              alignItems: 'center',
              gap: '14px',
              color: '#fde68a'
            }}>
              <AlertTriangle size={22} style={{ flexShrink: 0, color: '#f59e0b' }} />
              <div style={{ fontSize: '13px', lineHeight: '1.5', flex: 1 }}>
                <strong style={{ color: '#fbbf24', fontSize: '14px' }}>Smart Routing is currently DISABLED (USE_SMART_ROUTING=False)</strong>
                <div style={{ color: '#cbd5e1' }}>
                  Stage 1 reasoning classification is bypassed. Prompts submitted here or via the Gateway will be dispatched directly to the fallback/default model (<code>{config.fallback_model || defaultModel}</code>).
                </div>
              </div>
              <button
                type="button"
                onClick={handleToggleSmartRouting}
                style={{
                  background: '#2563eb',
                  color: '#fff',
                  border: 'none',
                  padding: '7px 16px',
                  borderRadius: '8px',
                  fontSize: '12px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap'
                }}
              >
                Enable Smart Routing
              </button>
            </div>
          )}

          {/* Sample Prompt Chips */}
          <div style={{ marginBottom: '16px' }}>
            <div style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '8px', fontWeight: '500' }}>
              💡 Quick-Test Scenarios across Threshold Categories:
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {SAMPLE_PROMPTS.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => setPromptInput(item.prompt)}
                  style={{
                    background: 'rgba(30, 41, 59, 0.8)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '20px',
                    padding: '6px 14px',
                    fontSize: '12px',
                    color: '#cbd5e1',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    transition: 'all 0.2s ease'
                  }}
                  onMouseOver={(e) => e.currentTarget.style.borderColor = '#3b82f6'}
                  onMouseOut={(e) => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          {/* Prompt Form Card */}
          <div style={{ 
            background: 'rgba(30, 41, 59, 0.5)', 
            border: '1px solid rgba(255, 255, 255, 0.08)', 
            borderRadius: '16px', 
            padding: '20px',
            marginBottom: '24px'
          }}>
            <form onSubmit={handleRouteAndExecute}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <label style={{ fontSize: '14px', fontWeight: '600', color: '#e2e8f0' }}>
                  User Prompt to Route & Execute:
                </label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '12px', color: '#94a3b8' }}>Default Reasoning Model:</span>
                  <select
                    value={activeReasoningModel}
                    onChange={(e) => setReasoningModelOverride(e.target.value)}
                    style={{
                      background: '#0f172a',
                      color: '#38bdf8',
                      border: '1px solid rgba(255,255,255,0.15)',
                      borderRadius: '8px',
                      padding: '4px 10px',
                      fontSize: '12px',
                      fontWeight: '500'
                    }}
                  >
                    {availableModelsList.map(m => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </div>
              </div>

              <textarea
                value={promptInput}
                onChange={(e) => setPromptInput(e.target.value)}
                placeholder="Enter any coding, complex reasoning, general QA, translation, or creative prompt here..."
                rows={4}
                style={{
                  width: '100%',
                  background: '#0f172a',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  borderRadius: '10px',
                  padding: '12px',
                  color: '#fff',
                  fontSize: '14px',
                  fontFamily: 'inherit',
                  resize: 'vertical',
                  marginBottom: '16px',
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                <button
                  type="button"
                  onClick={() => { setPromptInput(''); setRoutingResult(null); }}
                  style={{
                    background: 'transparent',
                    border: '1px solid rgba(255,255,255,0.1)',
                    color: '#94a3b8',
                    padding: '8px 16px',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontSize: '13px'
                  }}
                >
                  Clear
                </button>
                <button
                  type="submit"
                  disabled={loading || !promptInput.trim()}
                  style={{
                    background: loading ? '#475569' : '#2563eb',
                    color: '#fff',
                    border: 'none',
                    padding: '8px 24px',
                    borderRadius: '8px',
                    fontWeight: '600',
                    cursor: loading ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontSize: '14px'
                  }}
                >
                  {loading ? (
                    <>
                      <RefreshCw size={16} className="spin" />
                      Stage 1 Reasoning & Stage 2 Execution...
                    </>
                  ) : (
                    <>
                      <Zap size={16} />
                      Route & Execute Prompt
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Real-time 2-Stage Routing Flow Card */}
          {routingResult && (
            <div style={{ marginTop: '24px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                <CheckCircle2 size={20} color="#10b981" />
                <h3 style={{ fontSize: '18px', fontWeight: '700', margin: 0 }}>
                  2-Stage Dynamic Routing Trace
                </h3>
                <span style={{ fontSize: '12px', color: '#94a3b8', marginLeft: 'auto' }}>
                  Total Latency: {routingResult.trace?.total_latency_ms} ms • Tokens: {routingResult.trace?.total_tokens}
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '20px', marginBottom: '24px' }}>
                {/* STAGE 1 CARD: Reasoning Model Decision */}
                <div style={{ 
                  background: 'rgba(30, 41, 59, 0.6)', 
                  border: '1px solid rgba(59, 130, 246, 0.3)', 
                  borderRadius: '16px', 
                  padding: '20px',
                  boxShadow: '0 4px 20px rgba(0,0,0,0.2)'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ 
                        background: '#1e3a8a', 
                        color: '#60a5fa', 
                        borderRadius: '6px', 
                        padding: '2px 8px', 
                        fontSize: '11px', 
                        fontWeight: '700' 
                      }}>
                        STAGE 1
                      </div>
                      <span style={{ fontWeight: '600', fontSize: '15px' }}>Reasoning Model Dispatch</span>
                    </div>
                    <span style={{ fontSize: '12px', color: '#94a3b8' }}>
                      {routingResult.trace?.stage1_latency_ms} ms
                    </span>
                  </div>

                  <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '14px' }}>
                    Evaluated by reasoning model: <span style={{ color: '#38bdf8', fontWeight: '600' }}>{routingResult.trace?.reasoning_model}</span>
                  </div>

                  {/* Detected Category & Confidence vs Threshold */}
                  {(() => {
                    const dec = routingResult.trace?.routing_decision || {};
                    const catKey = dec.category || 'general_qa';
                    const catStyle = CATEGORY_COLORS[catKey] || CATEGORY_COLORS.general_qa;
                    const Icon = catStyle.icon;
                    return (
                      <div style={{ 
                        background: catStyle.bg, 
                        border: `1px solid ${catStyle.border}`, 
                        borderRadius: '12px', 
                        padding: '14px',
                        marginBottom: '16px' 
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: catStyle.text, fontWeight: '700' }}>
                            <Icon size={18} />
                            <span>{dec.category_name || catKey.toUpperCase()}</span>
                          </div>
                          <span style={{ 
                            fontSize: '11px', 
                            padding: '2px 8px', 
                            borderRadius: '999px',
                            background: dec.threshold_met ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                            color: dec.threshold_met ? '#34d399' : '#fbbf24',
                            fontWeight: '600'
                          }}>
                            {dec.threshold_met ? '✅ Threshold Satisfied' : '⚠️ Fallback Model Applied'}
                          </span>
                        </div>

                        {/* Visual Progress Bar: Confidence vs Threshold */}
                        <div style={{ marginTop: '8px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px', color: '#cbd5e1' }}>
                            <span>Model Confidence: <strong>{Math.round((dec.confidence || 0) * 100)}%</strong></span>
                            <span>Required Threshold: <strong>{Math.round((dec.threshold || 0) * 100)}%</strong></span>
                          </div>
                          <div style={{ height: '8px', background: 'rgba(0,0,0,0.4)', borderRadius: '4px', overflow: 'hidden', position: 'relative' }}>
                            <div style={{ 
                              height: '100%', 
                              width: `${Math.min(100, Math.round((dec.confidence || 0) * 100))}%`, 
                              background: dec.threshold_met ? '#10b981' : '#f59e0b',
                              borderRadius: '4px',
                              transition: 'width 0.5s ease'
                            }} />
                          </div>
                        </div>

                        <div style={{ marginTop: '12px', fontSize: '13px', color: '#e2e8f0', lineHeight: '1.4' }}>
                          <strong>Reasoning:</strong> {dec.reasoning}
                        </div>
                      </div>
                    );
                  })()}

                  <div style={{ fontSize: '12px', color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span>Selected Target:</span>
                    <span style={{ 
                      background: '#0f172a', 
                      color: '#a78bfa', 
                      padding: '4px 10px', 
                      borderRadius: '6px', 
                      fontWeight: '600',
                      border: '1px solid rgba(255,255,255,0.1)'
                    }}>
                      {routingResult.trace?.target_model}
                    </span>
                  </div>
                </div>

                {/* STAGE 2 CARD: Target Model Response */}
                <div style={{ 
                  background: 'rgba(30, 41, 59, 0.6)', 
                  border: '1px solid rgba(168, 85, 247, 0.3)', 
                  borderRadius: '16px', 
                  padding: '20px',
                  boxShadow: '0 4px 20px rgba(0,0,0,0.2)',
                  display: 'flex',
                  flexDirection: 'column'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ 
                        background: '#581c87', 
                        color: '#c084fc', 
                        borderRadius: '6px', 
                        padding: '2px 8px', 
                        fontSize: '11px', 
                        fontWeight: '700' 
                      }}>
                        STAGE 2
                      </div>
                      <span style={{ fontWeight: '600', fontSize: '15px' }}>Target Model Execution</span>
                    </div>
                    <span style={{ fontSize: '12px', color: '#94a3b8' }}>
                      {routingResult.trace?.stage2_latency_ms} ms
                    </span>
                  </div>

                  <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '12px' }}>
                    Executed by: <span style={{ color: '#a78bfa', fontWeight: '600' }}>{routingResult.trace?.target_model}</span>
                  </div>

                  {/* Toggle forwarded prompt */}
                  <div style={{ marginBottom: '10px' }}>
                    <button
                      type="button"
                      onClick={() => setShowTargetPrompt(!showTargetPrompt)}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: '#94a3b8',
                        fontSize: '12px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        padding: 0
                      }}
                    >
                      {showTargetPrompt ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      {showTargetPrompt ? 'Hide Prompt Sent to Target Model' : 'View Prompt Sent to Target Model'}
                    </button>
                    {showTargetPrompt && (
                      <div style={{ 
                        marginTop: '6px', 
                        background: '#0f172a', 
                        padding: '8px 12px', 
                        borderRadius: '8px', 
                        fontSize: '12px', 
                        color: '#cbd5e1',
                        border: '1px solid rgba(255,255,255,0.08)' 
                      }}>
                        {routingResult.trace?.target_prompt}
                      </div>
                    )}
                  </div>

                  {/* Final Response Content Box */}
                  <div style={{ 
                    flex: 1, 
                    background: '#0f172a', 
                    borderRadius: '12px', 
                    border: '1px solid rgba(255,255,255,0.1)', 
                    padding: '16px',
                    position: 'relative',
                    maxHeight: '400px',
                    overflowY: 'auto'
                  }}>
                    <button
                      onClick={() => copyToClipboard(routingResult.response)}
                      style={{
                        position: 'absolute',
                        top: '12px',
                        right: '12px',
                        background: 'rgba(255,255,255,0.08)',
                        border: 'none',
                        borderRadius: '6px',
                        color: '#cbd5e1',
                        padding: '4px 8px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        fontSize: '11px'
                      }}
                    >
                      {copiedResp ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
                      {copiedResp ? 'Copied' : 'Copy'}
                    </button>

                    <pre style={{ 
                      margin: 0, 
                      whiteSpace: 'pre-wrap', 
                      wordBreak: 'break-word', 
                      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                      fontSize: '13px',
                      color: '#e2e8f0',
                      lineHeight: '1.5'
                    }}>
                      {routingResult.response}
                    </pre>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ====================================================================== */}
      {/* TAB 2: CONFIGURATION & ACCURACY THRESHOLDS */}
      {/* ====================================================================== */}
      {activeSubTab === 'config' && config && (
        <div style={{ 
          background: 'rgba(30, 41, 59, 0.5)', 
          border: '1px solid rgba(255, 255, 255, 0.08)', 
          borderRadius: '16px', 
          padding: '24px' 
        }}>
          <form onSubmit={handleSaveConfig}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: '700', margin: '0 0 4px 0' }}>
                  Smart Router Hyperparameters & Category Accuracy Thresholds
                </h3>
                <p style={{ color: '#94a3b8', fontSize: '13px', margin: 0 }}>
                  Configure which default model conducts reasoning analysis, the accuracy threshold per domain, and default target models.
                </p>
              </div>

              <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                {saveSuccess && (
                  <span style={{ color: '#34d399', fontSize: '13px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <CheckCircle2 size={16} /> Saved!
                  </span>
                )}
                <button
                  type="submit"
                  disabled={configSaving}
                  style={{
                    background: '#2563eb',
                    color: '#fff',
                    border: 'none',
                    padding: '8px 20px',
                    borderRadius: '8px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    fontSize: '14px'
                  }}
                >
                  {configSaving ? 'Saving...' : 'Save Configuration'}
                </button>
              </div>
            </div>

            {/* Feature Flag: USE_SMART_ROUTING */}
            <div style={{
              background: config.enabled ? 'rgba(37, 99, 235, 0.08)' : 'rgba(245, 158, 11, 0.08)',
              border: `1px solid ${config.enabled ? 'rgba(59, 130, 246, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
              borderRadius: '12px',
              padding: '16px 20px',
              marginBottom: '24px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '16px'
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <Zap size={18} color={config.enabled ? '#60a5fa' : '#fbbf24'} />
                  <span style={{ fontSize: '15px', fontWeight: '700', color: '#f8fafc' }}>
                    Feature Flag: USE_SMART_ROUTING
                  </span>
                  <span style={{
                    fontSize: '11px',
                    padding: '2px 8px',
                    borderRadius: '999px',
                    background: config.enabled ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                    color: config.enabled ? '#34d399' : '#fbbf24',
                    fontWeight: '600'
                  }}>
                    {config.enabled ? 'ACTIVE (Enabled)' : 'INACTIVE (Bypassed)'}
                  </span>
                </div>
                <p style={{ color: '#94a3b8', fontSize: '13px', margin: 0 }}>
                  Controls whether prompts are analyzed by the default reasoning model for optimal routing, or directly dispatched to the fallback/default model.
                </p>
              </div>

              <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={config.enabled}
                  onChange={(e) => setConfig({ ...config, enabled: e.target.checked, use_smart_routing: e.target.checked })}
                  style={{ width: '20px', height: '20px', accentColor: '#2563eb', cursor: 'pointer' }}
                />
                <span style={{ fontSize: '14px', fontWeight: '600', color: config.enabled ? '#60a5fa' : '#94a3b8' }}>
                  {config.enabled ? 'Enabled' : 'Disabled'}
                </span>
              </label>
            </div>

            {/* Default Reasoning Model & Fallback Model */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px', marginBottom: '28px' }}>
              <div style={{ background: '#0f172a', padding: '16px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#e2e8f0', marginBottom: '6px' }}>
                  Default Reasoning Model (Stage 1):
                </label>
                <select
                  value={config.default_reasoning_model}
                  onChange={(e) => setConfig({ ...config, default_reasoning_model: e.target.value })}
                  style={{
                    width: '100%',
                    background: '#1e293b',
                    color: '#38bdf8',
                    border: '1px solid rgba(255,255,255,0.15)',
                    borderRadius: '8px',
                    padding: '8px 12px',
                    fontSize: '14px',
                    fontWeight: '500'
                  }}
                >
                  {availableModelsList.map(m => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
                <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '6px' }}>
                  The default model asked to reason and decide the optimal route for incoming user queries.
                </div>
              </div>

              <div style={{ background: '#0f172a', padding: '16px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#e2e8f0', marginBottom: '6px' }}>
                  Global Fallback Model:
                </label>
                <select
                  value={config.fallback_model}
                  onChange={(e) => setConfig({ ...config, fallback_model: e.target.value })}
                  style={{
                    width: '100%',
                    background: '#1e293b',
                    color: '#cbd5e1',
                    border: '1px solid rgba(255,255,255,0.15)',
                    borderRadius: '8px',
                    padding: '8px 12px',
                    fontSize: '14px',
                    fontWeight: '500'
                  }}
                >
                  {availableModelsList.map(m => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
                <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '6px' }}>
                  Invoked if a chosen target model is offline or confidence drops below accuracy threshold.
                </div>
              </div>
            </div>

            {/* Category Threshold Cards */}
            <h4 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '16px', color: '#f1f5f9' }}>
              Category Accuracy Thresholds & Preferred Model Mappings
            </h4>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px' }}>
              {Object.entries(config.categories || {}).map(([catKey, cat]) => {
                const catStyle = CATEGORY_COLORS[catKey] || CATEGORY_COLORS.general_qa;
                const Icon = catStyle.icon;
                const thresholdPct = Math.round((cat.accuracy_threshold || 0.70) * 100);

                return (
                  <div
                    key={catKey}
                    style={{
                      background: '#0f172a',
                      border: `1px solid ${catStyle.border}44`,
                      borderRadius: '12px',
                      padding: '16px',
                      boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <div style={{ color: catStyle.text }}>
                        <Icon size={18} />
                      </div>
                      <span style={{ fontWeight: '700', fontSize: '15px', color: '#f8fafc' }}>
                        {cat.name || catKey}
                      </span>
                    </div>

                    <p style={{ fontSize: '12px', color: '#94a3b8', margin: '0 0 16px 0', minHeight: '34px', lineHeight: '1.4' }}>
                      {cat.description}
                    </p>

                    {/* Target Model Mapping */}
                    <div style={{ marginBottom: '14px' }}>
                      <label style={{ display: 'block', fontSize: '11px', color: '#cbd5e1', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                        Target Model:
                      </label>
                      <select
                        value={cat.target_model}
                        onChange={(e) => {
                          const updatedCats = { ...config.categories };
                          updatedCats[catKey].target_model = e.target.value;
                          setConfig({ ...config, categories: updatedCats });
                        }}
                        style={{
                          width: '100%',
                          background: '#1e293b',
                          color: '#fff',
                          border: '1px solid rgba(255,255,255,0.1)',
                          borderRadius: '6px',
                          padding: '6px 10px',
                          fontSize: '13px'
                        }}
                      >
                        {availableModelsList.map(m => (
                          <option key={m} value={m}>{m}</option>
                        ))}
                      </select>
                    </div>

                    {/* Accuracy Threshold Slider */}
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <label style={{ fontSize: '11px', color: '#cbd5e1', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                          Accuracy Threshold:
                        </label>
                        <span style={{ fontSize: '13px', fontWeight: '700', color: catStyle.text }}>
                          {thresholdPct}%
                        </span>
                      </div>
                      <input
                        type="range"
                        min="0.50"
                        max="0.95"
                        step="0.05"
                        value={cat.accuracy_threshold}
                        onChange={(e) => {
                          const updatedCats = { ...config.categories };
                          updatedCats[catKey].accuracy_threshold = parseFloat(e.target.value);
                          setConfig({ ...config, categories: updatedCats });
                        }}
                        style={{ width: '100%', cursor: 'pointer' }}
                      />
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: '#64748b' }}>
                        <span>Permissive (50%)</span>
                        <span>Strict (95%)</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </form>
        </div>
      )}

      {/* ====================================================================== */}
      {/* TAB 3: FULL CALL LOGS & AUDIT TRACE */}
      {/* ====================================================================== */}
      {activeSubTab === 'logs' && (
        <div style={{ 
          background: 'rgba(30, 41, 59, 0.5)', 
          border: '1px solid rgba(255, 255, 255, 0.08)', 
          borderRadius: '16px', 
          padding: '20px' 
        }}>
          {/* Logs Toolbar */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flex: 1, minWidth: '280px' }}>
              <div style={{ position: 'relative', flex: 1 }}>
                <Search size={16} style={{ position: 'absolute', left: '10px', top: '10px', color: '#64748b' }} />
                <input
                  type="text"
                  placeholder="Search prompts or responses..."
                  value={logsSearch}
                  onChange={(e) => setLogsSearch(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && loadLogs()}
                  style={{
                    width: '100%',
                    background: '#0f172a',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '8px',
                    padding: '8px 12px 8px 34px',
                    color: '#fff',
                    fontSize: '13px',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <select
                value={categoryFilter}
                onChange={(e) => { setCategoryFilter(e.target.value); }}
                style={{
                  background: '#0f172a',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                  padding: '8px 12px',
                  color: '#cbd5e1',
                  fontSize: '13px'
                }}
              >
                <option value="">All Categories</option>
                <option value="coding">Coding</option>
                <option value="complex_work">Complex Work</option>
                <option value="general_qa">General QA</option>
                <option value="fast_lightweight">Fast & Lightweight</option>
                <option value="creative_writing">Creative Writing</option>
              </select>

              <button
                onClick={loadLogs}
                style={{
                  background: 'rgba(255,255,255,0.08)',
                  border: 'none',
                  borderRadius: '8px',
                  padding: '8px 14px',
                  color: '#cbd5e1',
                  cursor: 'pointer',
                  fontSize: '13px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <RefreshCw size={14} className={logsLoading ? 'spin' : ''} />
                Refresh
              </button>
            </div>

            <button
              onClick={handleClearLogs}
              style={{
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#f87171',
                borderRadius: '8px',
                padding: '8px 14px',
                cursor: 'pointer',
                fontSize: '13px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <Trash2 size={14} />
              Clear Logs
            </button>
          </div>

          {/* Table of Call Logs */}
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', color: '#cbd5e1' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', textAlign: 'left', color: '#94a3b8' }}>
                  <th style={{ padding: '10px 12px' }}>Timestamp</th>
                  <th style={{ padding: '10px 12px' }}>User Prompt</th>
                  <th style={{ padding: '10px 12px' }}>Reasoning Model</th>
                  <th style={{ padding: '10px 12px' }}>Category & Confidence</th>
                  <th style={{ padding: '10px 12px' }}>Target Model</th>
                  <th style={{ padding: '10px 12px' }}>Total Latency</th>
                  <th style={{ padding: '10px 12px', textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan={7} style={{ textAlign: 'center', padding: '36px', color: '#64748b' }}>
                      No Smart Router calls logged yet. Submit a prompt in the Playground above!
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => {
                    const catKey = log.category || 'general_qa';
                    const catStyle = CATEGORY_COLORS[catKey] || CATEGORY_COLORS.general_qa;
                    return (
                      <tr key={log.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', transition: 'background 0.2s' }}>
                        <td style={{ padding: '12px', whiteSpace: 'nowrap', color: '#64748b', fontSize: '12px' }}>
                          {new Date(log.timestamp).toLocaleTimeString()}
                        </td>
                        <td style={{ padding: '12px', maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: '500', color: '#f1f5f9' }}>
                          {log.prompt}
                        </td>
                        <td style={{ padding: '12px', color: '#38bdf8', fontSize: '12px' }}>
                          {log.reasoning_model}
                        </td>
                        <td style={{ padding: '12px' }}>
                          <span style={{ 
                            background: catStyle.bg, 
                            color: catStyle.text, 
                            padding: '2px 8px', 
                            borderRadius: '6px', 
                            fontSize: '11px',
                            fontWeight: '600'
                          }}>
                            {catKey} ({Math.round((log.confidence || 0) * 100)}%)
                          </span>
                        </td>
                        <td style={{ padding: '12px', color: '#a78bfa', fontWeight: '600', fontSize: '12px' }}>
                          {log.target_model}
                        </td>
                        <td style={{ padding: '12px', fontSize: '12px' }}>
                          {log.total_latency_ms ? `${Math.round(log.total_latency_ms)} ms` : '-'}
                        </td>
                        <td style={{ padding: '12px', textAlign: 'right' }}>
                          <button
                            onClick={() => setSelectedLogForModal(log)}
                            style={{
                              background: '#2563eb',
                              border: 'none',
                              color: '#fff',
                              borderRadius: '6px',
                              padding: '4px 10px',
                              fontSize: '12px',
                              cursor: 'pointer',
                              fontWeight: '500'
                            }}
                          >
                            Inspect Call Log
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ====================================================================== */}
      {/* FULL CALL LOG INSPECTOR MODAL */}
      {/* ====================================================================== */}
      {selectedLogForModal && (
        <div 
          onClick={() => setSelectedLogForModal(null)}
          role="dialog"
          aria-modal="true"
          aria-label="Smart Router Full Call Log Trace"
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(6px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '20px'
          }}>
          <div 
            onClick={(e) => e.stopPropagation()}
            style={{
              background: '#0f172a',
              border: '1px solid rgba(255,255,255,0.15)',
              borderRadius: '20px',
              width: '100%',
              maxWidth: '850px',
              maxHeight: '90vh',
              display: 'flex',
              flexDirection: 'column',
              boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)',
              overflow: 'hidden'
            }}>
            {/* Modal Header */}
            <div style={{
              padding: '16px 24px',
              borderBottom: '1px solid rgba(255,255,255,0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <GitBranch size={20} color="#3b82f6" />
                <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '700', color: '#fff' }}>
                  Smart Router Full Call Log Trace
                </h3>
              </div>
              <button
                onClick={() => setSelectedLogForModal(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#94a3b8',
                  fontSize: '20px',
                  cursor: 'pointer',
                  padding: '4px'
                }}
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div style={{ padding: '24px', overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {/* 1. What was the prompt */}
              <div>
                <div style={{ fontSize: '12px', fontWeight: '700', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>
                  1. Original User Prompt:
                </div>
                <div style={{ background: '#1e293b', padding: '12px 16px', borderRadius: '10px', fontSize: '14px', color: '#f8fafc', border: '1px solid rgba(255,255,255,0.05)' }}>
                  {selectedLogForModal.prompt}
                </div>
              </div>

              {/* 2. What was the default (reasoning) model used */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div>
                  <div style={{ fontSize: '12px', fontWeight: '700', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>
                    2. Default Reasoning Model Used:
                  </div>
                  <div style={{ background: '#1e293b', padding: '10px 14px', borderRadius: '10px', fontSize: '13px', color: '#38bdf8', fontWeight: '600', border: '1px solid rgba(255,255,255,0.05)' }}>
                    {selectedLogForModal.reasoning_model}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '12px', fontWeight: '700', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>
                    Routed Target Model:
                  </div>
                  <div style={{ background: '#1e293b', padding: '10px 14px', borderRadius: '10px', fontSize: '13px', color: '#a78bfa', fontWeight: '600', border: '1px solid rgba(255,255,255,0.05)' }}>
                    {selectedLogForModal.target_model}
                  </div>
                </div>
              </div>

              {/* 3. Reasoning Model Response & Decision */}
              <div>
                <div style={{ fontSize: '12px', fontWeight: '700', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>
                  3. Reasoning Response & Model Selection Decision:
                </div>
                <div style={{ background: '#1e293b', padding: '14px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.05)' }}>
                  <div style={{ display: 'flex', gap: '12px', marginBottom: '10px', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '12px', background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', padding: '3px 8px', borderRadius: '6px', fontWeight: '600' }}>
                      Category: {selectedLogForModal.category}
                    </span>
                    <span style={{ fontSize: '12px', background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', padding: '3px 8px', borderRadius: '6px', fontWeight: '600' }}>
                      Confidence: {Math.round((selectedLogForModal.confidence || 0) * 100)}%
                    </span>
                    <span style={{ fontSize: '12px', background: 'rgba(255, 255, 255, 0.08)', color: '#cbd5e1', padding: '3px 8px', borderRadius: '6px' }}>
                      Threshold: {Math.round((selectedLogForModal.threshold || 0.70) * 100)}%
                    </span>
                  </div>
                  <div style={{ fontSize: '13px', color: '#e2e8f0', lineHeight: '1.4' }}>
                    <strong>Selection Rationale:</strong> {selectedLogForModal.routing_decision?.reasoning || selectedLogForModal.reasoning_raw_response}
                  </div>
                </div>
              </div>

              {/* 4. What was the prompt sent to this new model */}
              <div>
                <div style={{ fontSize: '12px', fontWeight: '700', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>
                  4. Prompt Sent to This New Model:
                </div>
                <div style={{ background: '#1e293b', padding: '12px 16px', borderRadius: '10px', fontSize: '13px', color: '#f8fafc', border: '1px solid rgba(255,255,255,0.05)' }}>
                  {selectedLogForModal.target_prompt || selectedLogForModal.prompt}
                </div>
              </div>

              {/* 5. Response from the target model */}
              <div>
                <div style={{ fontSize: '12px', fontWeight: '700', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>
                  5. Response from New Model ({selectedLogForModal.target_model}):
                </div>
                <div style={{ 
                  background: '#020617', 
                  padding: '16px', 
                  borderRadius: '10px', 
                  border: '1px solid rgba(255,255,255,0.08)',
                  maxHeight: '220px',
                  overflowY: 'auto'
                }}>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: '13px', color: '#e2e8f0', fontFamily: 'monospace' }}>
                    {selectedLogForModal.target_response}
                  </pre>
                </div>
              </div>

              {/* 6. Latency & Token Breakdown */}
              <div style={{ 
                background: 'rgba(255,255,255,0.03)', 
                padding: '12px 16px', 
                borderRadius: '10px', 
                display: 'flex', 
                justifyContent: 'space-between', 
                fontSize: '12px', 
                color: '#94a3b8',
                border: '1px solid rgba(255,255,255,0.05)'
              }}>
                <span>Stage 1 Latency: <strong style={{ color: '#fff' }}>{selectedLogForModal.stage1_latency_ms} ms</strong></span>
                <span>Stage 2 Latency: <strong style={{ color: '#fff' }}>{selectedLogForModal.stage2_latency_ms} ms</strong></span>
                <span>Total Latency: <strong style={{ color: '#10b981' }}>{selectedLogForModal.total_latency_ms} ms</strong></span>
                <span>Total Tokens: <strong style={{ color: '#a78bfa' }}>{selectedLogForModal.total_tokens}</strong></span>
              </div>
            </div>

            {/* Modal Footer */}
            <div style={{ padding: '16px 24px', borderTop: '1px solid rgba(255,255,255,0.1)', display: 'flex', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setSelectedLogForModal(null)}
                style={{
                  background: '#2563eb',
                  color: '#fff',
                  border: 'none',
                  padding: '8px 20px',
                  borderRadius: '8px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  fontSize: '13px'
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
