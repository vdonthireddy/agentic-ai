import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Save, RefreshCw, Cpu, HardDrive, Server } from 'lucide-react';

export default function SettingsView({ onRefreshAll }) {
  const [config, setConfig] = useState({
    transport: 'http',
    ollama_api_base: '',
    default_model: '',
    provider_keys_status: {},
    hyperparameters: {
      compaction_token_threshold: 1500,
      compaction_keep_recent_turns: 2,
      hitl_timeout_seconds: 60.0,
      rate_limit_rpm: 60,
      rate_limit_tpm: 100000,
      react_max_iterations: 10,
      python_sandbox_timeout_seconds: 5.0,
      debate_max_rounds: 3,
      graph_max_depth: 4
    }
  });

  const [hyperparams, setHyperparams] = useState({
    compaction_token_threshold: 1500,
    compaction_keep_recent_turns: 2,
    hitl_timeout_seconds: 60.0,
    rate_limit_rpm: 60,
    rate_limit_tpm: 100000,
    react_max_iterations: 10,
    python_sandbox_timeout_seconds: 5.0,
    debate_max_rounds: 3,
    graph_max_depth: 4
  });

  const [keys, setKeys] = useState({
    openai: '',
    anthropic: '',
    gemini: '',
    groq: ''
  });

  const [telemetry, setTelemetry] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadConfig();
    loadMetrics();
  }, []);

  const loadConfig = async () => {
    try {
      const data = await api.getConfig();
      setConfig(data);
      if (data.hyperparameters) {
        setHyperparams(data.hyperparameters);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const loadMetrics = async () => {
    try {
      const data = await api.getSystemMetrics();
      setTelemetry(data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        transport: config.transport,
        ollama_api_base: config.ollama_api_base || undefined,
        default_model: config.default_model || undefined,
        ...hyperparams
      };
      if (keys.openai.trim()) payload.openai_api_key = keys.openai.trim();
      if (keys.anthropic.trim()) payload.anthropic_api_key = keys.anthropic.trim();
      if (keys.gemini.trim()) payload.gemini_api_key = keys.gemini.trim();
      if (keys.groq.trim()) payload.groq_api_key = keys.groq.trim();

      await api.updateConfig(payload);
      alert('Gateway configuration & hyperparameters updated successfully!');
      setKeys({ openai: '', anthropic: '', gemini: '', groq: '' });
      await loadConfig();
      if (onRefreshAll) onRefreshAll();
    } catch (err) {
      alert('Failed to save config: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const cpuPct = telemetry?.cpu?.usage_percent || telemetry?.cpu_percent || 0;
  const ramPct = telemetry?.memory?.percent_used || 0;
  const diskPct = telemetry?.disk?.percent_used || 0;

  return (
    <div>
      <div className="charts-grid mb-6">
        {/* Gateway Config Form */}
        <div className="glass-card">
          <div className="card-header">
            <h3>🔑 Multi-Provider API Keys & Endpoints</h3>
            <p>Configure credentials for OpenAI, Anthropic, Gemini, Groq, and local Ollama</p>
          </div>
          <form onSubmit={handleSave} className="card-body">
            <div className="form-group mb-3">
              <label>Transport Mode</label>
              <select
                className="form-control"
                value={config.transport || 'http'}
                onChange={(e) => setConfig({ ...config, transport: e.target.value })}
              >
                <option value="http">HTTP Server (:8000)</option>
                <option value="stdio">Stdio Subprocess</option>
              </select>
            </div>

            <div className="form-group mb-3">
              <label>Ollama API Base URL</label>
              <input
                type="text"
                className="form-control"
                placeholder="http://localhost:11434"
                value={config.ollama_api_base || ''}
                onChange={(e) => setConfig({ ...config, ollama_api_base: e.target.value })}
              />
            </div>

            <div className="form-group mb-3">
              <label>Default Model</label>
              <input
                type="text"
                className="form-control"
                placeholder="ollama/gemma2:2b"
                value={config.default_model || ''}
                onChange={(e) => setConfig({ ...config, default_model: e.target.value })}
              />
            </div>

            <hr style={{ border: 0, borderTop: '1px solid var(--border-color)', margin: '16px 0' }} />

            <div className="form-group mb-3">
              <label>OpenAI API Key (sk-...)</label>
              <input
                type="password"
                className="form-control"
                placeholder="Enter new key to update or leave empty"
                value={keys.openai}
                onChange={(e) => setKeys({ ...keys, openai: e.target.value })}
              />
              <small className="text-muted">
                Current: {config.provider_keys_status?.openai || 'Not Configured'}
              </small>
            </div>

            <div className="form-group mb-3">
              <label>Anthropic API Key (sk-ant-...)</label>
              <input
                type="password"
                className="form-control"
                placeholder="Enter new key to update or leave empty"
                value={keys.anthropic}
                onChange={(e) => setKeys({ ...keys, anthropic: e.target.value })}
              />
              <small className="text-muted">
                Current: {config.provider_keys_status?.anthropic || 'Not Configured'}
              </small>
            </div>

            <div className="form-group mb-3">
              <label>Google Gemini API Key</label>
              <input
                type="password"
                className="form-control"
                placeholder="Enter new key to update or leave empty"
                value={keys.gemini}
                onChange={(e) => setKeys({ ...keys, gemini: e.target.value })}
              />
              <small className="text-muted">
                Current: {config.provider_keys_status?.gemini || 'Not Configured'}
              </small>
            </div>

            <div className="form-group mb-3">
              <label>Groq API Key (gsk_...)</label>
              <input
                type="password"
                className="form-control"
                placeholder="Enter new key to update or leave empty"
                value={keys.groq}
                onChange={(e) => setKeys({ ...keys, groq: e.target.value })}
              />
              <small className="text-muted">
                Current: {config.provider_keys_status?.groq || 'Not Configured'}
              </small>
            </div>

            <hr style={{ border: 0, borderTop: '1px solid var(--border-color)', margin: '16px 0' }} />
            <h4 style={{ fontSize: '13px', color: '#818cf8', marginBottom: '10px' }}>⚙️ System Hyperparameters & Policy Limits</h4>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div className="form-group">
                <label style={{ fontSize: '11px' }}>Compaction Token Threshold</label>
                <input
                  type="number"
                  className="form-control"
                  value={hyperparams.compaction_token_threshold}
                  onChange={(e) => setHyperparams({ ...hyperparams, compaction_token_threshold: parseInt(e.target.value, 10) || 1500 })}
                />
              </div>
              <div className="form-group">
                <label style={{ fontSize: '11px' }}>Compaction Keep Turns</label>
                <input
                  type="number"
                  className="form-control"
                  value={hyperparams.compaction_keep_recent_turns}
                  onChange={(e) => setHyperparams({ ...hyperparams, compaction_keep_recent_turns: parseInt(e.target.value, 10) || 2 })}
                />
              </div>
              <div className="form-group">
                <label style={{ fontSize: '11px' }}>HITL Safety Timeout (sec)</label>
                <input
                  type="number"
                  step="0.5"
                  className="form-control"
                  value={hyperparams.hitl_timeout_seconds}
                  onChange={(e) => setHyperparams({ ...hyperparams, hitl_timeout_seconds: parseFloat(e.target.value) || 60.0 })}
                />
              </div>
              <div className="form-group">
                <label style={{ fontSize: '11px' }}>ReAct Max Iterations</label>
                <input
                  type="number"
                  className="form-control"
                  value={hyperparams.react_max_iterations}
                  onChange={(e) => setHyperparams({ ...hyperparams, react_max_iterations: parseInt(e.target.value, 10) || 10 })}
                />
              </div>
              <div className="form-group">
                <label style={{ fontSize: '11px' }}>Python Sandbox Timeout (sec)</label>
                <input
                  type="number"
                  step="0.5"
                  className="form-control"
                  value={hyperparams.python_sandbox_timeout_seconds}
                  onChange={(e) => setHyperparams({ ...hyperparams, python_sandbox_timeout_seconds: parseFloat(e.target.value) || 5.0 })}
                />
              </div>
              <div className="form-group">
                <label style={{ fontSize: '11px' }}>Rate Limit (RPM)</label>
                <input
                  type="number"
                  className="form-control"
                  value={hyperparams.rate_limit_rpm}
                  onChange={(e) => setHyperparams({ ...hyperparams, rate_limit_rpm: parseInt(e.target.value, 10) || 60 })}
                />
              </div>
            </div>

            <button type="submit" className="btn btn-primary w-full mt-4" disabled={saving}>
              <Save size={16} />
              <span>{saving ? 'Saving...' : '💾 Save Gateway Configuration & Hyperparameters'}</span>
            </button>
          </form>
        </div>

        {/* System Diagnostics */}
        <div className="glass-card">
          <div className="card-header flex-between">
            <div>
              <h3>💻 Host System Diagnostics</h3>
              <p>Live hardware resource utilization and platform telemetry</p>
            </div>
            <button className="btn btn-secondary btn-sm" onClick={loadMetrics}>
              <RefreshCw size={14} />
            </button>
          </div>
          <div className="card-body">
            <div className="system-metric-block mb-4">
              <div className="flex-between mb-1">
                <span>CPU Utilization:</span>
                <strong>{cpuPct}%</strong>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${cpuPct}%` }}></div>
              </div>
            </div>

            <div className="system-metric-block mb-4">
              <div className="flex-between mb-1">
                <span>RAM Memory:</span>
                <strong>
                  {ramPct}% ({telemetry?.memory?.used_gb || 0} / {telemetry?.memory?.total_gb || 0} GB)
                </strong>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${ramPct}%` }}></div>
              </div>
            </div>

            <div className="system-metric-block mb-4">
              <div className="flex-between mb-1">
                <span>Disk Storage:</span>
                <strong>
                  {diskPct}% ({telemetry?.disk?.free_gb || 0} GB free / {telemetry?.disk?.total_gb || 0} GB)
                </strong>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${diskPct}%` }}></div>
              </div>
            </div>

            <div className="glass-card p-4 mt-4" style={{ background: 'rgba(0,0,0,0.2)' }}>
              <div className="meta-row mb-2">
                <span>Platform:</span>
                <strong>{telemetry?.os ? `${telemetry.os.system} ${telemetry.os.machine || ''}` : '-'}</strong>
              </div>
              <div className="meta-row mb-2">
                <span>Python Environment:</span>
                <strong>{telemetry?.os?.python_version ? `Python ${telemetry.os.python_version}` : '-'}</strong>
              </div>
              <div className="meta-row">
                <span>Active Transport:</span>
                <strong>{config.transport?.toUpperCase() || 'HTTP'}</strong>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
