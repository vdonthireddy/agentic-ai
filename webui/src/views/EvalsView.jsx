import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Play, Award, CheckCircle, Plus, Trash2, Scale } from 'lucide-react';

export default function EvalsView({ models, activeModel }) {
  const [subTab, setSubTab] = useState('runner');

  // Registries
  const [agents, setAgents] = useState([]);
  const [evalModels, setEvalModels] = useState([]);
  const [judges, setJudges] = useState([]);
  const [runs, setRuns] = useState([]);
  const [selectedRunIds, setSelectedRunIds] = useState(new Set());
  const [comparisonResult, setComparisonResult] = useState(null);

  // Runner state
  const [selectedAgent, setSelectedAgent] = useState('mcp_default');
  const [candidateModel, setCandidateModel] = useState(activeModel || 'ollama/gemma2:2b');
  const [selectedJudge, setSelectedJudge] = useState('ollama/gemma2:2b');
  const [categories, setCategories] = useState({ tool_calling: true, skill_adherence: true, reasoning: true });
  const [running, setRunning] = useState(false);
  const [scorecard, setScorecard] = useState(null);

  // Inline forms
  const [newModel, setNewModel] = useState({ id: '', name: '', provider: 'openai' });
  const [newJudge, setNewJudge] = useState({ id: '', name: '', model: 'openai/gpt-4o-mini' });
  const [newAgent, setNewAgent] = useState({ id: '', name: '', type: 'mcp', endpoint_url: '' });

  useEffect(() => {
    loadRegistries();
  }, []);

  const loadRegistries = async () => {
    try {
      const [agRes, modRes, jdgRes, runRes] = await Promise.all([
        api.getEvalAgents(),
        api.getEvalModels(),
        api.getEvalJudges(),
        api.getEvalRuns()
      ]);
      setAgents(agRes.agents || []);
      setEvalModels(modRes.models || []);
      setJudges(jdgRes.judges || []);
      setRuns(runRes.runs || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleRunEvals = async () => {
    const selectedCats = Object.keys(categories).filter((k) => categories[k]);
    if (selectedCats.length === 0) {
      alert('Select at least one category to test.');
      return;
    }

    setRunning(true);
    setScorecard(null);

    try {
      const data = await api.runEvals({
        agent_id: selectedAgent,
        model: candidateModel,
        judge_model: selectedJudge,
        categories: selectedCats
      });
      setScorecard(data);
      loadRegistries();
    } catch (err) {
      alert('Benchmark execution failed: ' + err.message);
    } finally {
      setRunning(false);
    }
  };

  const handleToggleRunSelect = (runId) => {
    const next = new Set(selectedRunIds);
    if (next.has(runId)) next.delete(runId);
    else next.add(runId);
    setSelectedRunIds(next);
  };

  const handleCompareRuns = async () => {
    if (selectedRunIds.size < 2) return;
    try {
      const data = await api.compareRuns(Array.from(selectedRunIds));
      setComparisonResult(data);
    } catch (err) {
      alert('Compare failed: ' + err.message);
    }
  };

  // Registries handlers
  const handleAddModel = async (e) => {
    e.preventDefault();
    if (!newModel.id || !newModel.name) return;
    await api.registerEvalModel({ model_id: newModel.id, name: newModel.name, provider: newModel.provider });
    setNewModel({ id: '', name: '', provider: 'openai' });
    loadRegistries();
  };

  const handleDeleteModel = async (id) => {
    if (!confirm(`Delete model ${id}?`)) return;
    await api.deleteEvalModel(id);
    loadRegistries();
  };

  const handleAddJudge = async (e) => {
    e.preventDefault();
    if (!newJudge.id || !newJudge.name || !newJudge.model) return;
    await api.registerEvalJudge({ judge_id: newJudge.id, name: newJudge.name, model: newJudge.model });
    setNewJudge({ id: '', name: '', model: 'openai/gpt-4o-mini' });
    loadRegistries();
  };

  const handleDeleteJudge = async (id) => {
    if (!confirm(`Delete judge ${id}?`)) return;
    await api.deleteEvalJudge(id);
    loadRegistries();
  };

  const handleAddAgent = async (e) => {
    e.preventDefault();
    if (!newAgent.id || !newAgent.name) return;
    await api.registerEvalAgent({
      adapter_id: newAgent.id,
      name: newAgent.name,
      type: newAgent.type,
      endpoint_url: newAgent.endpoint_url || undefined
    });
    setNewAgent({ id: '', name: '', type: 'mcp', endpoint_url: '' });
    loadRegistries();
  };

  const handleDeleteAgent = async (id) => {
    if (!confirm(`Delete agent ${id}?`)) return;
    await api.deleteEvalAgent(id);
    loadRegistries();
  };

  return (
    <div>
      {/* Sub navigation */}
      <div className="evals-hub-nav">
        <button
          className={`evals-tab-btn ${subTab === 'runner' ? 'active' : ''}`}
          onClick={() => setSubTab('runner')}
        >
          🚀 1. Run Benchmark Suite
        </button>
        <button
          className={`evals-tab-btn ${subTab === 'models' ? 'active' : ''}`}
          onClick={() => setSubTab('models')}
        >
          🤖 2. Models & Judges Registry
        </button>
        <button
          className={`evals-tab-btn ${subTab === 'agents' ? 'active' : ''}`}
          onClick={() => setSubTab('agents')}
        >
          🔌 3. Agent Adapters Registry
        </button>
        <button
          className={`evals-tab-btn ${subTab === 'history' ? 'active' : ''}`}
          onClick={() => setSubTab('history')}
        >
          📊 4. Historical Runs & Side-by-Side Compare
        </button>
      </div>

      {/* PANE 1: RUNNER */}
      {subTab === 'runner' && (
        <div className="charts-grid">
          {/* Config card */}
          <div className="glass-card">
            <div className="card-header">
              <h3>🚀 Execute Benchmark</h3>
              <p>Run 4-Grader evaluation on candidate agents and models</p>
            </div>
            <div className="card-body">
              <div className="form-group mb-3">
                <label>Agent Adapter Under Test</label>
                <select
                  className="form-control"
                  value={selectedAgent}
                  onChange={(e) => setSelectedAgent(e.target.value)}
                >
                  {agents.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name} ({a.type.toUpperCase()})
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group mb-3">
                <label>Candidate Model Under Test</label>
                <select
                  className="form-control"
                  value={candidateModel}
                  onChange={(e) => setCandidateModel(e.target.value)}
                >
                  {models.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name || m.id}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group mb-3">
                <label>LLM-as-a-Judge Evaluator</label>
                <select
                  className="form-control"
                  value={selectedJudge}
                  onChange={(e) => setSelectedJudge(e.target.value)}
                >
                  {judges.map((j) => (
                    <option key={j.judge_id} value={j.model}>
                      {j.name} [{j.model}]
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group mb-4">
                <label>Benchmark Test Categories</label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label>
                    <input
                      type="checkbox"
                      checked={categories.tool_calling}
                      onChange={(e) => setCategories({ ...categories, tool_calling: e.target.checked })}
                    />{' '}
                    Everyday Tools Accuracy (Tool Calling)
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={categories.skill_adherence}
                      onChange={(e) => setCategories({ ...categories, skill_adherence: e.target.checked })}
                    />{' '}
                    Domain Skills Adherence
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={categories.reasoning}
                      onChange={(e) => setCategories({ ...categories, reasoning: e.target.checked })}
                    />{' '}
                    Multi-Step Reasoning
                  </label>
                </div>
              </div>

              <button
                className="btn btn-primary w-full"
                onClick={handleRunEvals}
                disabled={running}
              >
                <Play size={16} />
                <span>{running ? 'Executing 4-Grader Suite...' : '🚀 Execute Benchmark Suite'}</span>
              </button>
            </div>
          </div>

          {/* Results Scorecard */}
          <div className="glass-card">
            <div className="card-header flex-between">
              <h3>🏆 Benchmark Scorecard</h3>
              <span className={`badge ${scorecard ? 'badge-success' : 'badge-dim'}`}>
                {scorecard ? 'Completed' : 'Ready'}
              </span>
            </div>
            <div className="card-body">
              {scorecard ? (
                <div>
                  <div className="metrics-grid mb-4">
                    <div className="glass-card p-3">
                      <span className="text-muted text-sm">Overall Score:</span>
                      <div><strong className="text-accent text-lg">{Math.round(scorecard.summary?.overall_score || 0)}%</strong></div>
                    </div>
                    <div className="glass-card p-3">
                      <span className="text-muted text-sm">Pass Rate:</span>
                      <div><strong className="text-lg">{Math.round(scorecard.summary?.pass_rate || 0)}%</strong></div>
                    </div>
                    <div className="glass-card p-3">
                      <span className="text-muted text-sm">Tests Executed:</span>
                      <div><strong>{scorecard.summary?.total_tests || 0}</strong></div>
                    </div>
                    <div className="glass-card p-3">
                      <span className="text-muted text-sm">Avg Latency:</span>
                      <div><strong>{Math.round(scorecard.summary?.avg_latency_ms || 0)} ms</strong></div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-6 text-muted">
                  Select an <strong>Agent Adapter</strong>, <strong>Candidate Model</strong>, and <strong>LLM Judge</strong> on the left, then click <strong>Execute Benchmark Suite</strong> to run evaluation.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* PANE 2: MODELS & JUDGES */}
      {subTab === 'models' && (
        <div>
          <div className="charts-grid mb-6">
            <div className="glass-card">
              <div className="card-header">
                <h3>🤖 Registered Candidate Models</h3>
              </div>
              <div className="card-body p-0">
                <div className="table-responsive">
                  <table className="data-table">
                    <thead>
                      <tr><th>Model ID</th><th>Name</th><th>Provider</th><th>Action</th></tr>
                    </thead>
                    <tbody>
                      {evalModels.map((m) => (
                        <tr key={m.model_id}>
                          <td><code>{m.model_id}</code></td>
                          <td><strong>{m.name}</strong></td>
                          <td><span className="badge badge-dim">{m.provider}</span></td>
                          <td>
                            <button className="btn btn-secondary btn-sm" onClick={() => handleDeleteModel(m.model_id)}>
                              <Trash2 size={14} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <div className="glass-card">
              <div className="card-header">
                <h3>➕ Register Candidate Model</h3>
              </div>
              <form onSubmit={handleAddModel} className="card-body">
                <div className="form-group mb-2">
                  <label>Model ID</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="openai/gpt-4o"
                    value={newModel.id}
                    onChange={(e) => setNewModel({ ...newModel, id: e.target.value })}
                  />
                </div>
                <div className="form-group mb-2">
                  <label>Display Name</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="OpenAI GPT-4o"
                    value={newModel.name}
                    onChange={(e) => setNewModel({ ...newModel, name: e.target.value })}
                  />
                </div>
                <div className="form-group mb-3">
                  <label>Provider</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="openai, anthropic, ollama"
                    value={newModel.provider}
                    onChange={(e) => setNewModel({ ...newModel, provider: e.target.value })}
                  />
                </div>
                <button type="submit" className="btn btn-primary w-full">
                  <Plus size={16} />
                  <span>Add Model to Registry</span>
                </button>
              </form>
            </div>
          </div>

          <div className="charts-grid">
            <div className="glass-card">
              <div className="card-header">
                <h3>⚖️ Registered LLM Judges</h3>
              </div>
              <div className="card-body p-0">
                <div className="table-responsive">
                  <table className="data-table">
                    <thead>
                      <tr><th>Judge ID</th><th>Judge Name</th><th>Model</th><th>Action</th></tr>
                    </thead>
                    <tbody>
                      {judges.map((j) => (
                        <tr key={j.judge_id}>
                          <td><code>{j.judge_id}</code></td>
                          <td><strong>{j.name}</strong></td>
                          <td><code>{j.model}</code></td>
                          <td>
                            <button className="btn btn-secondary btn-sm" onClick={() => handleDeleteJudge(j.judge_id)}>
                              <Trash2 size={14} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <div className="glass-card">
              <div className="card-header">
                <h3>➕ Register New LLM Judge</h3>
              </div>
              <form onSubmit={handleAddJudge} className="card-body">
                <div className="form-group mb-2">
                  <label>Judge ID</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="judge_gpt4o_strict"
                    value={newJudge.id}
                    onChange={(e) => setNewJudge({ ...newJudge, id: e.target.value })}
                  />
                </div>
                <div className="form-group mb-2">
                  <label>Judge Display Name</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="GPT-4o Strict Judge"
                    value={newJudge.name}
                    onChange={(e) => setNewJudge({ ...newJudge, name: e.target.value })}
                  />
                </div>
                <div className="form-group mb-3">
                  <label>Underlying Model</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="openai/gpt-4o-mini"
                    value={newJudge.model}
                    onChange={(e) => setNewJudge({ ...newJudge, model: e.target.value })}
                  />
                </div>
                <button type="submit" className="btn btn-primary w-full">
                  <Plus size={16} />
                  <span>Add Judge to Registry</span>
                </button>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* PANE 3: AGENTS */}
      {subTab === 'agents' && (
        <div className="charts-grid">
          <div className="glass-card">
            <div className="card-header">
              <h3>🔌 Registered Agent Adapters</h3>
            </div>
            <div className="card-body p-0">
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr><th>Adapter ID</th><th>Name</th><th>Type</th><th>Action</th></tr>
                  </thead>
                  <tbody>
                    {agents.map((a) => (
                      <tr key={a.id}>
                        <td><code>{a.id}</code></td>
                        <td><strong>{a.name}</strong></td>
                        <td><span className="badge badge-accent">{a.type.toUpperCase()}</span></td>
                        <td>
                          <button className="btn btn-secondary btn-sm" onClick={() => handleDeleteAgent(a.id)}>
                            <Trash2 size={14} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div className="glass-card">
            <div className="card-header">
              <h3>➕ Register Agent Adapter</h3>
            </div>
            <form onSubmit={handleAddAgent} className="card-body">
              <div className="form-group mb-2">
                <label>Adapter ID</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="travel_http_agent"
                  value={newAgent.id}
                  onChange={(e) => setNewAgent({ ...newAgent, id: e.target.value })}
                />
              </div>
              <div className="form-group mb-2">
                <label>Agent Name</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="External Travel HTTP Agent"
                  value={newAgent.name}
                  onChange={(e) => setNewAgent({ ...newAgent, name: e.target.value })}
                />
              </div>
              <div className="form-group mb-2">
                <label>Adapter Type</label>
                <select
                  className="form-control"
                  value={newAgent.type}
                  onChange={(e) => setNewAgent({ ...newAgent, type: e.target.value })}
                >
                  <option value="mcp">Native FastMCP Tool Agent</option>
                  <option value="http">External HTTP REST Endpoint</option>
                </select>
              </div>
              {newAgent.type === 'http' && (
                <div className="form-group mb-2">
                  <label>Endpoint URL</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="http://localhost:9000/agent"
                    value={newAgent.endpoint_url}
                    onChange={(e) => setNewAgent({ ...newAgent, endpoint_url: e.target.value })}
                  />
                </div>
              )}
              <button type="submit" className="btn btn-primary w-full mt-3">
                <Plus size={16} />
                <span>Add Adapter to Registry</span>
              </button>
            </form>
          </div>
        </div>
      )}

      {/* PANE 4: HISTORY & COMPARE */}
      {subTab === 'history' && (
        <div>
          <div className="glass-card mb-6">
            <div className="card-header flex-between">
              <h3>📊 Historical Benchmark Runs</h3>
              <button
                className="btn btn-primary btn-sm"
                onClick={handleCompareRuns}
                disabled={selectedRunIds.size < 2}
              >
                <Scale size={14} />
                <span>Compare Selected ({selectedRunIds.size})</span>
              </button>
            </div>
            <div className="card-body p-0">
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th style={{ width: '40px' }}>Select</th>
                      <th>Run ID / Date</th>
                      <th>Agent</th>
                      <th>Model</th>
                      <th>Overall Score</th>
                      <th>Pass Rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runs.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="text-center py-6 text-muted">
                          No benchmark runs recorded yet.
                        </td>
                      </tr>
                    ) : (
                      runs.map((r) => (
                        <tr key={r.run_id}>
                          <td>
                            <input
                              type="checkbox"
                              checked={selectedRunIds.has(r.run_id)}
                              onChange={() => handleToggleRunSelect(r.run_id)}
                            />
                          </td>
                          <td>
                            <strong><code>{r.run_id.substring(0, 16)}...</code></strong>
                            <br />
                            <small className="text-muted">{new Date(r.timestamp).toLocaleString()}</small>
                          </td>
                          <td>{r.agent_id}</td>
                          <td><code>{r.model}</code></td>
                          <td><span className="font-bold text-accent">{Math.round(r.overall_score || 0)}%</span></td>
                          <td>
                            <span className={`badge ${r.pass_rate >= 80 ? 'badge-success' : 'badge-dim'}`}>
                              {Math.round(r.pass_rate || 0)}%
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Comparison Matrix */}
          {comparisonResult && (
            <div className="glass-card mb-6">
              <div className="card-header flex-between">
                <h3>⚖️ Side-by-Side Model Comparison Matrix</h3>
                <button className="btn btn-secondary btn-sm" onClick={() => setComparisonResult(null)}>
                  ✕ Close
                </button>
              </div>
              <div className="card-body">
                <div className="comparison-grid">
                  {(comparisonResult.runs || []).map((r) => {
                    const isWinner = comparisonResult.winner?.run_id === r.run_id;
                    return (
                      <div key={r.run_id} className={`compare-card ${isWinner ? 'winner' : ''}`}>
                        <div className="flex-between mb-3">
                          <h4>{r.model}</h4>
                          {isWinner && <span className="badge badge-success">🏆 Highest Score</span>}
                        </div>
                        <div className="compare-stat-row">
                          <span className="compare-stat-label">Agent:</span>
                          <span className="compare-stat-val">{r.agent_id}</span>
                        </div>
                        <div className="compare-stat-row">
                          <span className="compare-stat-label">Overall Score:</span>
                          <span className="compare-stat-val text-accent">{Math.round(r.overall_score)}%</span>
                        </div>
                        <div className="compare-stat-row">
                          <span className="compare-stat-label">Pass Rate:</span>
                          <span className="compare-stat-val">{Math.round(r.pass_rate)}%</span>
                        </div>
                        <div className="compare-stat-row">
                          <span className="compare-stat-label">Avg Latency:</span>
                          <span className="compare-stat-val">{Math.round(r.avg_latency_ms || 0)}ms</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
