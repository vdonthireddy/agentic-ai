import React, { useState } from 'react';
import { 
  GitFork, Play, Plus, Trash2, Save, Sparkles, Database, 
  Cpu, Wrench, ShieldAlert, CheckCircle2, ArrowRight, Layers 
} from 'lucide-react';
import { api } from '../api/client';

const NODE_TYPES = [
  { type: 'agent', label: 'Agent Reasoning Node', icon: Cpu, color: 'border-indigo-500 bg-indigo-950/30' },
  { type: 'tool', label: 'MCP Tool Executor', icon: Wrench, color: 'border-amber-500 bg-amber-950/30' },
  { type: 'hitl', label: 'HITL Approval Gate', icon: ShieldAlert, color: 'border-rose-500 bg-rose-950/30' },
  { type: 'memory', label: 'Vector Memory Store', icon: Database, color: 'border-emerald-500 bg-emerald-950/30' }
];

export default function CanvasView() {
  const [workflowName, setWorkflowName] = useState('Customer Support & Automated Refund DAG');
  const [nodes, setNodes] = useState([
    { id: 'node-1', type: 'agent', label: '1. Sentiment Classifier Agent', desc: 'Classifies customer tone & urgency' },
    { id: 'node-2', type: 'tool', label: '2. Tool: product_knowledge', desc: 'Queries warranty & refund limits' },
    { id: 'node-3', type: 'hitl', label: '3. HITL Manager Gate', desc: 'Approval required if refund > $100' },
    { id: 'node-4', type: 'memory', label: '4. Memory Store', desc: 'Saves case resolution to CRM namespace' }
  ]);
  const [executing, setExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState(null);

  const addNode = (nodeType) => {
    const nextId = `node-${nodes.length + 1}`;
    const tmpl = NODE_TYPES.find(t => t.type === nodeType) || NODE_TYPES[0];
    setNodes([...nodes, {
      id: nextId,
      type: tmpl.type,
      label: `${nodes.length + 1}. ${tmpl.label}`,
      desc: 'Configurable pipeline step'
    }]);
  };

  const removeNode = (id) => {
    setNodes(nodes.filter(n => n.id !== id));
  };

  const handleExecute = async () => {
    setExecuting(true);
    setExecutionResult(null);
    try {
      const res = await fetch('/api/canvas/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow_name: workflowName,
          nodes: nodes.map(n => ({ id: n.id, type: n.type, data: { label: n.label } })),
          edges: nodes.slice(0, -1).map((n, idx) => ({ source: n.id, target: nodes[idx + 1].id }))
        })
      });
      const data = await res.json();
      setExecutionResult(data);
    } catch (err) {
      setExecutionResult({ status: 'error', final_output: String(err) });
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="view-container animate-fade-in">
      {/* Header */}
      <div className="view-header">
        <div>
          <h2 className="view-title flex items-center gap-2">
            <GitFork className="text-indigo-400" /> Visual Workflow Canvas (DAG)
          </h2>
          <p className="view-subtitle">
            Compose and execute multi-agent pipelines, tool execution chains, and HITL safety gates visually.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button 
            className="primary-btn flex items-center gap-2"
            onClick={handleExecute}
            disabled={executing}
          >
            <Play size={16} /> {executing ? 'Executing Pipeline...' : 'Run Workflow DAG'}
          </button>
        </div>
      </div>

      {/* Canvas Layout */}
      <div className="canvas-grid-layout">
        {/* Node Palette */}
        <div className="canvas-sidebar-palette">
          <h4 className="palette-title">Node Palette</h4>
          <p className="text-xs text-slate-400 mb-3">Click to add step to pipeline:</p>
          
          <div className="palette-items">
            {NODE_TYPES.map((nt) => {
              const Icon = nt.icon;
              return (
                <button
                  key={nt.type}
                  className="palette-node-btn"
                  onClick={() => addNode(nt.type)}
                >
                  <Icon size={16} className="text-indigo-400" />
                  <div className="text-left">
                    <div className="text-xs font-semibold text-slate-200">{nt.label}</div>
                    <div className="text-[10px] text-slate-400">{nt.type.toUpperCase()}</div>
                  </div>
                  <Plus size={14} className="ml-auto text-slate-500" />
                </button>
              );
            })}
          </div>

          <div className="workflow-meta-card mt-6">
            <label className="text-xs text-slate-400 font-medium">Pipeline Name</label>
            <input 
              type="text"
              value={workflowName}
              onChange={(e) => setWorkflowName(e.target.value)}
              className="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        {/* Visual Pipeline Track */}
        <div className="canvas-board">
          <div className="board-header">
            <span className="text-xs text-slate-400 font-mono">DAG Execution Sequence ({nodes.length} nodes)</span>
          </div>

          <div className="dag-flow-track">
            {nodes.map((node, index) => {
              const tmpl = NODE_TYPES.find(t => t.type === node.type) || NODE_TYPES[0];
              const Icon = tmpl.icon;
              return (
                <React.Fragment key={node.id}>
                  <div className={`dag-node-card ${tmpl.color}`}>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="node-type-tag">{node.type.toUpperCase()}</span>
                      <button 
                        onClick={() => removeNode(node.id)}
                        className="text-slate-500 hover:text-rose-400 transition"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                    <div className="flex items-center gap-2">
                      <Icon size={16} className="text-slate-300" />
                      <span className="text-xs font-semibold text-slate-100">{node.label}</span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1">{node.desc}</p>
                  </div>

                  {index < nodes.length - 1 && (
                    <div className="dag-arrow-connector">
                      <div className="connector-line"></div>
                      <ArrowRight size={16} className="text-indigo-400" />
                    </div>
                  )}
                </React.Fragment>
              );
            })}
          </div>

          {/* Execution Trace Output */}
          {executionResult && (
            <div className="canvas-execution-report animate-slide-up mt-6">
              <div className="report-header">
                <CheckCircle2 size={16} className="text-emerald-400" />
                <h4 className="text-xs font-semibold text-emerald-300">
                  DAG Run Successful ({executionResult.duration_ms} ms)
                </h4>
              </div>
              <div className="trace-list">
                {executionResult.execution_trace?.map((trace, i) => (
                  <div key={i} className="trace-step-item">
                    <span className="text-indigo-400 font-mono text-xs">Step {i+1}:</span>
                    <span className="text-slate-200 font-medium text-xs">{trace.label}</span>
                    <span className="text-slate-400 text-xs ml-auto">{trace.status}</span>
                  </div>
                ))}
              </div>
              <div className="text-xs text-slate-300 bg-slate-900/80 p-2.5 rounded border border-slate-800 mt-3 font-mono">
                {executionResult.final_output}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
