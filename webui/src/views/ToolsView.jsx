import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Play, Check, AlertCircle } from 'lucide-react';

export default function ToolsView() {
  const [tools, setTools] = useState([]);
  const [selectedTool, setSelectedTool] = useState('calculator');
  const [argsJson, setArgsJson] = useState('{"expression": "184.50 * 0.18"}');
  const [execResult, setExecResult] = useState(null);
  const [latency, setLatency] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadTools();
  }, []);

  const loadTools = async () => {
    try {
      const data = await api.getTools();
      const list = data.tools || [];
      setTools(list);
      if (list.length > 0) {
        populateDefaultArgs(list[0]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const populateDefaultArgs = (tool) => {
    if (tool && tool.params && tool.params.length > 0) {
      const exampleArgs = {};
      for (const p of tool.params) {
        exampleArgs[p.name] = p.example !== undefined ? p.example : '';
      }
      setArgsJson(JSON.stringify(exampleArgs, null, 2));
    } else {
      setArgsJson('{}');
    }
  };

  const handleToolChange = (toolName) => {
    setSelectedTool(toolName);
    const t = tools.find((x) => x.name === toolName);
    if (t) populateDefaultArgs(t);
  };

  const handleExecute = async () => {
    let parsedArgs = {};
    try {
      if (argsJson.trim()) {
        parsedArgs = JSON.parse(argsJson);
      }
    } catch (e) {
      alert('Invalid JSON in arguments: ' + e.message);
      return;
    }

    setLoading(true);
    setExecResult(null);

    try {
      const data = await api.executeTool(selectedTool, parsedArgs);
      setExecResult(data.result !== undefined ? data.result : data);
      setLatency(data.latency_ms);
    } catch (err) {
      setExecResult({ error: err.message });
      setLatency(0);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="charts-grid mb-6">
        {/* Tool Catalog Table */}
        <div className="glass-card">
          <div className="card-header flex-between">
            <h3>📦 Registered MCP Tools</h3>
            <span className="badge badge-accent">{tools.length} Tools</span>
          </div>
          <div className="card-body p-0">
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Tool</th>
                    <th>Category</th>
                    <th>Description</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {tools.map((t) => (
                    <tr key={t.name}>
                      <td>
                        <strong>{t.icon || '🛠️'} <code>{t.name}</code></strong>
                      </td>
                      <td>
                        <span className="badge badge-dim">{t.category}</span>
                      </td>
                      <td className="text-secondary text-sm">{t.description}</td>
                      <td>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => handleToolChange(t.name)}
                        >
                          ⚡ Load
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Live Tool Execution Sandbox */}
        <div className="glass-card">
          <div className="card-header">
            <h3>⚡ Live Tool Sandbox Playground</h3>
            <p>Execute tools standalone with arbitrary parameters and view raw outputs</p>
          </div>
          <div className="card-body">
            <div className="form-group mb-3">
              <label>Select Tool to Execute</label>
              <select
                className="form-control"
                value={selectedTool}
                onChange={(e) => handleToolChange(e.target.value)}
              >
                {tools.map((t) => (
                  <option key={t.name} value={t.name}>
                    {t.name} ({t.category})
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group mb-3">
              <label>Arguments (JSON Object)</label>
              <textarea
                className="form-control code-font"
                rows={5}
                value={argsJson}
                onChange={(e) => setArgsJson(e.target.value)}
              />
            </div>

            <button
              className="btn btn-primary w-full"
              onClick={handleExecute}
              disabled={loading}
            >
              <Play size={16} />
              <span>{loading ? 'Executing...' : '🚀 Execute Tool in Sandbox'}</span>
            </button>

            {execResult && (
              <div className="mt-4">
                <div className="flex-between mb-2">
                  <label className="font-bold">Output Execution Result:</label>
                  {latency !== null && (
                    <span className="badge badge-dim">{latency} ms</span>
                  )}
                </div>
                <pre className="json-code-box">
                  {typeof execResult === 'string'
                    ? execResult
                    : JSON.stringify(execResult, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
