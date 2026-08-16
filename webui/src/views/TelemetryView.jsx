import React, { useState, useEffect } from 'react';
import { Rocket, Sparkles, Zap, Coins, RefreshCw } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, PieChart, Pie } from 'recharts';
import { api } from '../api/client';

const COLORS = ['#06B6D4', '#3B82F6', '#8B5CF6', '#10B981', '#F59E0B', '#F43F5E'];

export default function TelemetryView({ stats: initialStats }) {
  const [stats, setStats] = useState(initialStats || {});
  const [loading, setLoading] = useState(false);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const data = await api.getStats();
      if (data) setStats(data);
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

  return (
    <div>
      {/* KPI Cards */}
      <div className="metrics-grid mb-6">
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
    </div>
  );
}
