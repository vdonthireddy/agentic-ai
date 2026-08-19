import React, { useState, useEffect } from 'react';
import { Rocket, Sparkles, Zap, Coins, DollarSign, TrendingUp } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, PieChart, Pie } from 'recharts';
import { api } from '../api/client';

const COLORS = ['#06B6D4', '#3B82F6', '#8B5CF6', '#10B981', '#F59E0B', '#F43F5E'];

export default function TelemetryView({ stats: initialStats }) {
  const [stats, setStats] = useState(initialStats || {});
  const [costData, setCostData] = useState({ total_cost_usd: 0, by_model: [], by_caller: [] });
  const [forecast, setForecast] = useState({ projected_cost_usd: 0, daily_average_usd: 0, projected_days: 30 });
  const [loading, setLoading] = useState(false);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const [data, costs, fc] = await Promise.all([
        api.getStats().catch(() => ({})),
        fetch('/api/costs').then(r => r.json()).catch(() => ({ total_cost_usd: 0, by_model: [] })),
        fetch('/api/costs/forecast').then(r => r.json()).catch(() => ({ projected_cost_usd: 0, daily_average_usd: 0 }))
      ]);
      if (data) setStats(data);
      if (costs) setCostData(costs);
      if (fc) setForecast(fc);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  useEffect(() => {
    if (initialStats && Object.keys(initialStats).length > 0) {
      setStats(initialStats);
    }
  }, [initialStats]);

  const totalCalls = stats.total_calls || 0;
  const successRate = stats.success_rate !== undefined
    ? stats.success_rate
    : (totalCalls > 0 ? Math.round(((stats.successful_calls ?? totalCalls) / totalCalls) * 100) : 100);
  const avgLatency = Math.round(stats.average_latency_ms || stats.avg_latency_ms || 0);
  const tokenUsage = stats.token_usage || { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 };

  const promptTokens = tokenUsage.prompt_tokens || 0;
  const compTokens = tokenUsage.completion_tokens || 0;
  const totalTokens = tokenUsage.total_tokens || 0;

  // Pie data for tokens
  const tokenData = [
    { name: 'Prompt Tokens', value: promptTokens, fill: '#06B6D4' },
    { name: 'Completion Tokens', value: compTokens, fill: '#3B82F6' },
  ];

  // Bar data for models
  const modelUsage = stats.models_usage || {};
  const modelData = Object.entries(modelUsage).map(([name, count]) => ({
    name: name.replace('ollama/', '').replace('openai/', '').replace('anthropic/', ''),
    fullName: name,
    count
  }));

  // Cost by model data
  const costModelData = (costData.by_model || []).map(m => ({
    name: m.model.replace('openai/', '').replace('anthropic/', '').replace('gemini/', ''),
    cost: m.cost_usd,
    fullName: m.model
  }));

  return (
    <div>
      {/* KPI Cards */}
      <div className="metrics-grid mb-6" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
        <div className="glass-card metric-card">
          <div className="metric-icon" style={{ color: '#06B6D4' }}>
            <Rocket size={24} />
          </div>
          <div className="metric-data">
            <div className="metric-value">{totalCalls}</div>
            <div className="metric-label">Total LLM Calls</div>
          </div>
        </div>

        <div className="glass-card metric-card">
          <div className="metric-icon" style={{ color: '#10B981' }}>
            <Sparkles size={24} />
          </div>
          <div className="metric-data">
            <div className="metric-value">{successRate}%</div>
            <div className="metric-label">Success Rate</div>
          </div>
        </div>

        <div className="glass-card metric-card">
          <div className="metric-icon" style={{ color: '#F59E0B' }}>
            <Zap size={24} />
          </div>
          <div className="metric-data">
            <div className="metric-value">{avgLatency} ms</div>
            <div className="metric-label">Average Latency</div>
          </div>
        </div>

        <div className="glass-card metric-card">
          <div className="metric-icon" style={{ color: '#8B5CF6' }}>
            <Coins size={24} />
          </div>
          <div className="metric-data">
            <div className="metric-value">{totalTokens.toLocaleString()}</div>
            <div className="metric-label">Total Tokens Streamed</div>
          </div>
        </div>

        <div className="glass-card metric-card">
          <div className="metric-icon" style={{ color: '#22c55e' }}>
            <DollarSign size={24} />
          </div>
          <div className="metric-data">
            <div className="metric-value">${(costData.total_cost_usd || 0).toFixed(4)}</div>
            <div className="metric-label">Total Est. Spend</div>
          </div>
        </div>
      </div>

      {/* Visual Charts Grid */}
      <div className="charts-grid mb-6">
        {/* Token Distribution Chart */}
        <div className="glass-card">
          <div className="card-header">
            <h3>🪙 Token Telemetry Breakdown</h3>
            <p>Distribution between prompt input tokens and completion outputs</p>
          </div>
          <div className="card-body" style={{ height: '300px' }}>
            {totalTokens > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={tokenData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={90}
                    label={(entry) => `${entry.name}: ${entry.value.toLocaleString()}`}
                  >
                    {tokenData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: '#1F2937',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '8px',
                      color: '#F9FAFB',
                      boxShadow: '0 8px 24px rgba(0, 0, 0, 0.5)',
                      padding: '8px 12px'
                    }}
                    itemStyle={{ color: '#F9FAFB', fontWeight: 600, fontSize: '13px' }}
                    labelStyle={{ color: '#9CA3AF', fontWeight: 600, fontSize: '12px', marginBottom: '4px' }}
                    formatter={(value) => [`${value.toLocaleString()} tokens`, 'Count']}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center py-6 text-muted">No token stream activity recorded yet.</div>
            )}
          </div>
        </div>

        {/* Model Calls Distribution Chart */}
        <div className="glass-card">
          <div className="card-header">
            <h3>🤖 Models Execution Share</h3>
            <p>Comparison of inference calls across local and cloud providers</p>
          </div>
          <div className="card-body" style={{ height: '300px' }}>
            {modelData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={modelData}>
                  <XAxis dataKey="name" stroke="#9CA3AF" tick={{ fontSize: 11 }} />
                  <YAxis stroke="#9CA3AF" allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      background: '#1F2937',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '8px',
                      color: '#F9FAFB',
                      boxShadow: '0 8px 24px rgba(0, 0, 0, 0.5)',
                      padding: '8px 12px'
                    }}
                    itemStyle={{ color: '#F9FAFB', fontWeight: 600, fontSize: '13px' }}
                    labelStyle={{ color: '#9CA3AF', fontWeight: 600, fontSize: '12px', marginBottom: '4px' }}
                    formatter={(val, name, item) => [`${val} calls`, item.payload.fullName]}
                  />
                  <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                    {modelData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center py-6 text-muted">No model inference calls recorded yet.</div>
            )}
          </div>
        </div>
      </div>

      {/* Cost Forecasting Card */}
      <div className="glass-card mb-6" style={{ padding: '20px' }}>
        <div className="flex-between" style={{ marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <TrendingUp size={20} style={{ color: '#22c55e' }} />
            <h3 style={{ margin: 0, color: '#f0f0f0', fontSize: '16px' }}>Cost Forecast & Spend Analytics</h3>
          </div>
          <span className="badge badge-outline" style={{ color: '#22c55e', borderColor: 'rgba(34,197,94,0.4)' }}>
            30-Day Projection
          </span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginTop: '14px' }}>
          <div style={{ background: 'rgba(0,0,0,0.25)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ color: '#888', fontSize: '12px', marginBottom: '4px' }}>Daily Average Spend</div>
            <div style={{ color: '#22c55e', fontSize: '18px', fontWeight: 'bold' }}>
              ${(forecast.daily_average_usd || 0).toFixed(4)} / day
            </div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.25)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ color: '#888', fontSize: '12px', marginBottom: '4px' }}>Projected 30-Day Spend</div>
            <div style={{ color: '#60a5fa', fontSize: '18px', fontWeight: 'bold' }}>
              ${(forecast.projected_cost_usd || 0).toFixed(2)}
            </div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.25)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ color: '#888', fontSize: '12px', marginBottom: '4px' }}>Local Models (Ollama)</div>
            <div style={{ color: '#a78bfa', fontSize: '18px', fontWeight: 'bold' }}>
              $0.00 (Zero-Cost Local)
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
