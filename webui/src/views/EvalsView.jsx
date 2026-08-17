import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Play, Award, CheckCircle, Plus, Trash2, Scale, Swords, Check, RefreshCw } from 'lucide-react';

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
  const [evalMode, setEvalMode] = useState('single'); // 'single' | 'compare'
  const [selectedAgent, setSelectedAgent] = useState('mcp_default');
  const [candidateModel, setCandidateModel] = useState(activeModel || 'ollama/gemma2:2b');
  const [compareModelsList, setCompareModelsList] = useState(['ollama/gemma2:2b', 'ollama/qwen2.5-coder:7b']);
  const [selectedJudge, setSelectedJudge] = useState('ollama/gemma2:2b');
  const [categories, setCategories] = useState({ tool_calling: true, skill_adherence: true, reasoning: true });
  const [running, setRunning] = useState(false);
  const [scorecard, setScorecard] = useState(null);
  const [compareScorecard, setCompareScorecard] = useState(null);

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

  const handleRunCompareModels = async () => {
    const selectedCats = Object.keys(categories).filter((k) => categories[k]);
    if (selectedCats.length === 0) {
      alert('Select at least one category to test.');
      return;
    }
    if (compareModelsList.length < 2) {
      alert('Please select at least 2 models for Head-to-Head comparison.');
      return;
    }

    setRunning(true);
    setCompareScorecard(null);

    try {
      const data = await api.compareModels({
        models: compareModelsList,
        agent_id: selectedAgent,
        judge_model: selectedJudge,
        categories: selectedCats
      });
      setCompareScorecard(data);
      loadRegistries();
    } catch (err) {
      alert('Head-to-head comparison failed: ' + err.message);
    } finally {
      setRunning(false);
    }
  };

  const handleToggleCompareModel = (modelId) => {
    setCompareModelsList((prev) => {
      if (prev.includes(modelId)) {
        return prev.filter((m) => m !== modelId);
      } else {
        return [...prev, modelId];
      }
    });
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
        <div>
          {/* Mode Switcher */}
          <div className="flex-between mb-4 p-2 glass-card" style={{ maxWidth: '600px' }}>
            <span className="text-sm font-semibold text-muted">Evaluation Mode:</span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                className={`btn btn-sm ${evalMode === 'single' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setEvalMode('single')}
              >
                <Play size={14} />
                <span>Single Model</span>
              </button>
              <button
                className={`btn btn-sm ${evalMode === 'compare' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setEvalMode('compare')}
              >
                <Swords size={14} />
                <span>⚔️ Head-to-Head Comparison</span>
              </button>
            </div>
          </div>

          <div className="charts-grid mb-6">
            {/* Config card */}
            <div className="glass-card">
              <div className="card-header">
                <h3>{evalMode === 'single' ? '🚀 Execute Benchmark' : '⚔️ Head-to-Head Model Comparison'}</h3>
                <p>
                  {evalMode === 'single'
                    ? 'Run 4-Grader evaluation on candidate agent and model'
                    : 'Benchmark and compare multiple models side-by-side on identical test cases'}
                </p>
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

                {evalMode === 'single' ? (
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
                ) : (
                  <div className="form-group mb-3">
                    <div className="flex-between mb-1">
                      <label>Select Models to Compare (Select 2+)</label>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          type="button"
                          className="btn btn-secondary btn-xs text-xs"
                          onClick={() => setCompareModelsList(models.map((m) => m.id))}
                        >
                          Select All
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary btn-xs text-xs"
                          onClick={() => setCompareModelsList([])}
                        >
                          Clear
                        </button>
                      </div>
                    </div>
                    <div
                      style={{
                        maxHeight: '160px',
                        overflowY: 'auto',
                        padding: '8px 12px',
                        border: '1px solid var(--border-color)',
                        borderRadius: '8px',
                        background: 'rgba(0,0,0,0.2)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '6px'
                      }}
                    >
                      {models.map((m) => (
                        <label key={m.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                          <input
                            type="checkbox"
                            checked={compareModelsList.includes(m.id)}
                            onChange={() => handleToggleCompareModel(m.id)}
                          />
                          <span style={{ fontSize: '0.9rem' }}>{m.name || m.id}</span>
                          <code className="text-xs text-muted">({m.id})</code>
                        </label>
                      ))}
                    </div>
                  </div>
                )}

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

                {evalMode === 'single' ? (
                  <button
                    className="btn btn-primary w-full"
                    onClick={handleRunEvals}
                    disabled={running}
                  >
                    <Play size={16} />
                    <span>{running ? 'Executing 4-Grader Suite...' : '🚀 Execute Benchmark Suite'}</span>
                  </button>
                ) : (
                  <button
                    className="btn btn-primary w-full"
                    onClick={handleRunCompareModels}
                    disabled={running || compareModelsList.length < 2}
                  >
                    <Swords size={16} />
                    <span>{running ? 'Benchmarking Models Head-to-Head...' : `⚔️ Run Head-to-Head Comparison (${compareModelsList.length} Models)`}</span>
                  </button>
                )}
              </div>
            </div>

            {/* Results Scorecard / Comparison Matrix */}
            <div className="glass-card">
              <div className="card-header flex-between">
                <h3>{evalMode === 'single' ? '🏆 Benchmark Scorecard' : '⚖️ Head-to-Head Scorecard Matrix'}</h3>
                <span className={`badge ${scorecard || compareScorecard ? 'badge-success' : 'badge-dim'}`}>
                  {scorecard || compareScorecard ? 'Completed' : 'Ready'}
                </span>
              </div>
              <div className="card-body">
                {evalMode === 'single' && scorecard && (
                  <div>
                    <div className="metrics-grid mb-4">
                      <div className="glass-card p-3">
                        <span className="text-muted text-sm">Overall Score:</span>
                        <div><strong className="text-accent text-lg">{Math.round(scorecard.summary?.overall_score || scorecard.average_score_pct || 0)}%</strong></div>
                      </div>
                      <div className="glass-card p-3">
                        <span className="text-muted text-sm">Pass Rate:</span>
                        <div><strong className="text-lg">{Math.round(scorecard.summary?.pass_rate || scorecard.pass_rate_pct || 0)}%</strong></div>
                      </div>
                      <div className="glass-card p-3">
                        <span className="text-muted text-sm">Tests Executed:</span>
                        <div><strong>{scorecard.summary?.total_tests || scorecard.total_tests || 0}</strong></div>
                      </div>
                      <div className="glass-card p-3">
                        <span className="text-muted text-sm">Avg Latency:</span>
                        <div><strong>{Math.round(scorecard.summary?.avg_latency_ms || scorecard.avg_latency_ms || 0)} ms</strong></div>
                      </div>
                    </div>

                    {scorecard.grader_averages && (
                      <div className="mb-4">
                        <h4 className="text-sm text-muted mb-2">4-Grader Subscores</h4>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
                          <div className="glass-card p-2 text-center">
                            <small className="text-muted">Deterministic</small>
                            <div className="font-bold">{Math.round(scorecard.grader_averages.deterministic || 0)}%</div>
                          </div>
                          <div className="glass-card p-2 text-center">
                            <small className="text-muted">Efficiency</small>
                            <div className="font-bold">{Math.round(scorecard.grader_averages.efficiency || 0)}%</div>
                          </div>
                          <div className="glass-card p-2 text-center">
                            <small className="text-muted">LLM Judge</small>
                            <div className="font-bold">{Math.round(scorecard.grader_averages.llm_judge || 0)}%</div>
                          </div>
                          <div className="glass-card p-2 text-center">
                            <small className="text-muted">Fact-Checker</small>
                            <div className="font-bold">{Math.round(scorecard.grader_averages.fact_checker || 0)}%</div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {evalMode === 'compare' && compareScorecard && (
                  <div>
                    {compareScorecard.comparison?.winner && (
                      <div
                        className="mb-4 p-3 glass-card"
                        style={{
                          background: 'rgba(16, 185, 129, 0.12)',
                          border: '1px solid var(--accent-emerald)',
                          borderRadius: '10px'
                        }}
                      >
                        <div className="flex-between">
                          <div>
                            <span className="text-xs font-semibold text-accent uppercase tracking-wider">🏆 Top Performing Model</span>
                            <h4 className="text-lg font-bold mt-1 text-white">{compareScorecard.comparison.winner.model}</h4>
                          </div>
                          <div className="text-right">
                            <div className="text-xs text-muted">Composite Score</div>
                            <div className="text-xl font-bold text-accent">{Math.round(compareScorecard.comparison.winner.overall_score || 0)}%</div>
                          </div>
                        </div>
                      </div>
                    )}

                    <div className="comparison-grid">
                      {(compareScorecard.comparison?.runs || []).map((r) => {
                        const isWinner = compareScorecard.comparison?.winner?.run_id === r.run_id;
                        return (
                          <div key={r.run_id} className={`compare-card ${isWinner ? 'winner' : ''}`}>
                            <div className="flex-between mb-2">
                              <h4 style={{ fontSize: '1rem' }}>{r.model}</h4>
                              {isWinner && <span className="badge badge-success">🏆 Top Score</span>}
                            </div>
                            <div className="compare-stat-row">
                              <span className="compare-stat-label">Composite Score:</span>
                              <span className="compare-stat-val text-accent">{Math.round(r.overall_score || 0)}%</span>
                            </div>
                            <div className="compare-stat-row">
                              <span className="compare-stat-label">Pass Rate:</span>
                              <span className="compare-stat-val">{Math.round(r.pass_rate || 0)}%</span>
                            </div>
                            <div className="compare-stat-row">
                              <span className="compare-stat-label">Avg Latency:</span>
                              <span className="compare-stat-val">{Math.round(r.avg_latency_ms || 0)} ms</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {((evalMode === 'single' && !scorecard) || (evalMode === 'compare' && !compareScorecard)) && (
                  <div className="text-center py-6 text-muted">
                    {evalMode === 'single' ? (
                      <span>Select an <strong>Agent Adapter</strong>, <strong>Candidate Model</strong>, and <strong>LLM Judge</strong> on the left, then click <strong>Execute Benchmark Suite</strong> to run evaluation.</span>
                    ) : (
                      <span>Select <strong>2 or more Models</strong> and an <strong>LLM Judge</strong> on the left, then click <strong>Run Head-to-Head Comparison</strong> to benchmark them side-by-side.</span>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Test Case Breakdown Table for Single Model Mode */}
          {evalMode === 'single' && scorecard?.results && (
            <div className="glass-card mb-6">
              <div className="card-header">
                <h3>📋 4-Grader Test Case Breakdown</h3>
              </div>
              <div className="card-body p-0">
                <div className="table-responsive">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Test ID</th>
                        <th>Category</th>
                        <th>Test Name</th>
                        <th>Deterministic</th>
                        <th>Efficiency</th>
                        <th>Judge</th>
                        <th>Fact-Check</th>
                        <th>Composite</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {scorecard.results.map((t) => {
                        const isPassed = Boolean(t.overall_passed ?? t.passed);
                        return (
                          <tr key={t.id}>
                            <td><code>{t.id}</code></td>
                            <td><span className="badge badge-dim">{t.category}</span></td>
                            <td><strong>{t.name}</strong></td>
                            <td>{Math.round((t.deterministic_score || 0) * 100)}%</td>
                            <td>{Math.round((t.efficiency_score || 0) * 100)}%</td>
                            <td>{Math.round((t.judge_score || 0) * 100)}%</td>
                            <td>{Math.round((t.fact_check_score || 0) * 100)}%</td>
                            <td><strong className="text-accent">{Math.round((t.composite_score || t.overall_score || 0) * 100)}%</strong></td>
                            <td>
                              <span className={`badge ${isPassed ? 'badge-success' : 'badge-dim'}`}>
                                {isPassed ? 'PASS' : 'FAIL'}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Comparative Summary Table for Head-to-Head Mode */}
          {evalMode === 'compare' && compareScorecard?.runs && (
            <div className="glass-card mb-6">
              <div className="card-header">
                <h3>📊 Head-to-Head Performance Scorecard Matrix</h3>
              </div>
              <div className="card-body p-0">
                <div className="table-responsive">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Model Name</th>
                        <th>Pass Rate</th>
                        <th>Avg Composite Score</th>
                        <th>Avg Latency</th>
                        <th>Total Tokens</th>
                        <th>Throughput</th>
                      </tr>
                    </thead>
                    <tbody>
                      {compareScorecard.runs.map((r) => {
                        const isTop = compareScorecard.comparison?.winner?.model === r.model;
                        const perf = r.performance_metrics || r.performance || {};
                        return (
                          <tr key={r.run_id || r.model} className={isTop ? 'highlight-row' : ''}>
                            <td>
                              <strong><code>{r.model}</code></strong>
                              {isTop && <span className="badge badge-success ml-2">🏆 Winner</span>}
                            </td>
                            <td><span className="font-semibold">{Math.round(r.pass_rate_pct || r.pass_rate || 0)}%</span> ({r.passed_tests}/{r.total_tests})</td>
                            <td><strong className="text-accent">{Math.round(r.average_score_pct || r.overall_score || 0)}%</strong></td>
                            <td>{Math.round(perf.avg_latency_ms || r.avg_latency_ms || 0)} ms</td>
                            <td>{(perf.total_tokens || r.total_tokens || 0).toLocaleString()}</td>
                            <td>{Math.round(perf.tokens_per_second || 0)} tok/s</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
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
                <h3>➕ Register LLM Judge</h3>
              </div>
              <form onSubmit={handleAddJudge} className="card-body">
                <div className="form-group mb-2">
                  <label>Judge ID</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="judge_claude_sonnet"
                    value={newJudge.id}
                    onChange={(e) => setNewJudge({ ...newJudge, id: e.target.value })}
                  />
                </div>
                <div className="form-group mb-2">
                  <label>Judge Name</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Claude 3.5 Sonnet Judge"
                    value={newJudge.name}
                    onChange={(e) => setNewJudge({ ...newJudge, name: e.target.value })}
                  />
                </div>
                <div className="form-group mb-3">
                  <label>Judge Model</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="anthropic/claude-3-5-sonnet-20241022"
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
        <div className="charts-grid mb-6">
          <div className="glass-card">
            <div className="card-header">
              <h3>🔌 Registered Agent Adapters</h3>
            </div>
            <div className="card-body p-0">
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr><th>Adapter ID</th><th>Name</th><th>Type</th><th>Endpoint</th><th>Action</th></tr>
                  </thead>
                  <tbody>
                    {agents.map((a) => (
                      <tr key={a.id}>
                        <td><code>{a.id}</code></td>
                        <td><strong>{a.name}</strong></td>
                        <td><span className="badge badge-dim">{a.type.toUpperCase()}</span></td>
                        <td><small className="text-muted">{a.endpoint_url || 'Native FastMCP Stdio'}</small></td>
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
