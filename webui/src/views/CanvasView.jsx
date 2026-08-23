import React, { useState, useRef, useEffect } from 'react';
import { 
  GitFork, Play, Plus, Trash2, Save, Sparkles, Database, 
  Cpu, Wrench, ShieldAlert, CheckCircle2, ArrowRight, Layers,
  Split, RefreshCw, Info, HelpCircle, XCircle, Zap
} from 'lucide-react';
import { api } from '../api/client';

const NODE_TYPES = [
  { type: 'agent', label: 'Agent Reasoning Node', icon: Cpu, color: 'border-indigo-500 bg-indigo-950/40' },
  { type: 'tool', label: 'MCP Tool Executor', icon: Wrench, color: 'border-amber-500 bg-amber-950/40' },
  { type: 'hitl', label: 'HITL Approval Gate', icon: ShieldAlert, color: 'border-rose-500 bg-rose-950/40' },
  { type: 'memory', label: 'Vector Memory Store', icon: Database, color: 'border-emerald-500 bg-emerald-950/40' }
];

const PREBUILT_TEMPLATES = {
  fork_swarm: {
    name: '🔱 1-to-3 Parallel Swarm Fork',
    nodes: [
      { id: 'node-root', type: 'agent', label: '1. Task Decomposer (Supervisor)', x: 40, y: 220 },
      { id: 'node-fork-1', type: 'tool', label: '2A. Tool: search_web (Worker 1)', x: 360, y: 70 },
      { id: 'node-fork-2', type: 'agent', label: '2B. Analyst Agent (Worker 2)', x: 360, y: 220 },
      { id: 'node-fork-3', type: 'tool', label: '2C. Tool: calculate (Worker 3)', x: 360, y: 370 },
      { id: 'node-join', type: 'agent', label: '3. Consensus Synthesizer', x: 680, y: 220 }
    ],
    edges: [
      { id: 'e1', source: 'node-root', target: 'node-fork-1', isFork: true },
      { id: 'e2', source: 'node-root', target: 'node-fork-2', isFork: true },
      { id: 'e3', source: 'node-root', target: 'node-fork-3', isFork: true },
      { id: 'e4', source: 'node-fork-1', target: 'node-join' },
      { id: 'e5', source: 'node-fork-2', target: 'node-join' },
      { id: 'e6', source: 'node-fork-3', target: 'node-join' }
    ]
  },
  hitl_safety: {
    name: '🛡️ HITL Safety Gate Fork',
    nodes: [
      { id: 'node-class', type: 'agent', label: '1. Intent & Risk Classifier', x: 50, y: 180 },
      { id: 'node-safe', type: 'tool', label: '2A. Auto-Execute (Low Risk)', x: 380, y: 80 },
      { id: 'node-hitl', type: 'hitl', label: '2B. Manager HITL Gate (High Risk)', x: 380, y: 280 },
      { id: 'node-mem', type: 'memory', label: '3. Memory Audit Logger', x: 700, y: 180 }
    ],
    edges: [
      { id: 'e1', source: 'node-class', target: 'node-safe', isFork: true },
      { id: 'e2', source: 'node-class', target: 'node-hitl', isFork: true },
      { id: 'e3', source: 'node-safe', target: 'node-mem' },
      { id: 'e4', source: 'node-hitl', target: 'node-mem' }
    ]
  },
  debate_swarm: {
    name: '⚖️ Multi-Agent Debate Swarm',
    nodes: [
      { id: 'node-prop', type: 'agent', label: '1. Proposer Agent (Author)', x: 60, y: 180 },
      { id: 'node-crit', type: 'agent', label: '2. Critic Agent (Adversary)', x: 370, y: 180 },
      { id: 'node-arb', type: 'agent', label: '3. Arbitrator (Consensus)', x: 680, y: 180 }
    ],
    edges: [
      { id: 'e1', source: 'node-prop', target: 'node-crit' },
      { id: 'e2', source: 'node-crit', target: 'node-arb' }
    ]
  }
};

export default function CanvasView() {
  const [workflowName, setWorkflowName] = useState('1-to-3 Parallel Swarm Fork DAG');
  const [nodes, setNodes] = useState(PREBUILT_TEMPLATES.fork_swarm.nodes);
  const [edges, setEdges] = useState(PREBUILT_TEMPLATES.fork_swarm.edges);
  
  // Drag & Drop State
  const [draggingNodeId, setDraggingNodeId] = useState(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const canvasRef = useRef(null);

  // Wire Connection State
  const [connectingSourceId, setConnectingSourceId] = useState(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  // Execution State
  const [executing, setExecuting] = useState(false);
  const [activeNodeId, setActiveNodeId] = useState(null);
  const [executionResult, setExecutionResult] = useState(null);

  // Load Template
  const applyTemplate = (key) => {
    const tmpl = PREBUILT_TEMPLATES[key];
    if (!tmpl) return;
    setWorkflowName(tmpl.name);
    setNodes(tmpl.nodes);
    setEdges(tmpl.edges);
    setExecutionResult(null);
  };

  // Add Node
  const addNode = (type) => {
    const nextId = `node-${Date.now().toString().slice(-4)}`;
    const tmpl = NODE_TYPES.find(t => t.type === type) || NODE_TYPES[0];
    const newNode = {
      id: nextId,
      type: tmpl.type,
      label: `${nodes.length + 1}. ${tmpl.label}`,
      x: 100 + (nodes.length % 4) * 60,
      y: 100 + (nodes.length % 3) * 60
    };
    setNodes(prev => [...prev, newNode]);
  };

  const removeNode = (id, e) => {
    e.stopPropagation();
    setNodes(prev => prev.filter(n => n.id !== id));
    setEdges(prev => prev.filter(edge => edge.source !== id && edge.target !== id));
  };

  // Mouse Handlers for Freeform Dragging
  const handleMouseDownNode = (id, e) => {
    if (e.target.classList.contains('node-port') || e.target.closest('button')) return;
    setDraggingNodeId(id);
    const node = nodes.find(n => n.id === id);
    if (!node || !canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    setDragOffset({
      x: (e.clientX - rect.left) - node.x,
      y: (e.clientY - rect.top) - node.y
    });
  };

  const handleMouseMove = (e) => {
    if (!canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;
    setMousePos({ x: currentX, y: currentY });

    if (draggingNodeId) {
      setNodes(prev => prev.map(node => {
        if (node.id === draggingNodeId) {
          const newX = Math.max(10, Math.min(rect.width - 250, currentX - dragOffset.x));
          const newY = Math.max(10, Math.min(rect.height - 110, currentY - dragOffset.y));
          return { ...node, x: newX, y: newY };
        }
        return node;
      }));
    }
  };

  const handleMouseUp = () => {
    setDraggingNodeId(null);
  };

  // Port Connection Handlers
  const handleStartConnect = (sourceId, e) => {
    e.stopPropagation();
    setConnectingSourceId(sourceId);
  };

  const handleCompleteConnect = (targetId, e) => {
    e.stopPropagation();
    if (!connectingSourceId || connectingSourceId === targetId) {
      setConnectingSourceId(null);
      return;
    }

    // Check if edge already exists
    const exists = edges.some(edge => edge.source === connectingSourceId && edge.target === targetId);
    if (!exists) {
      // Check if source already has other outgoing edges (marks it as a Fork!)
      const outgoingCount = edges.filter(e => e.source === connectingSourceId).length;
      const isFork = outgoingCount >= 1;
      
      const newEdge = {
        id: `e_${connectingSourceId}_${targetId}_${Date.now()}`,
        source: connectingSourceId,
        target: targetId,
        isFork: isFork
      };
      
      // Update any existing edges from this source to also be marked as forks
      setEdges(prev => [
        ...prev.map(e => e.source === connectingSourceId ? { ...e, isFork: true } : e),
        newEdge
      ]);
    }
    setConnectingSourceId(null);
  };

  const removeEdge = (edgeId, e) => {
    e.stopPropagation();
    setEdges(prev => prev.filter(e => e.id !== edgeId));
  };

  // Helper to compute node center coordinates
  const getNodePorts = (node) => {
    const width = 240;
    const height = 80;
    return {
      inPort: { x: node.x, y: node.y + height / 2 },
      outPort: { x: node.x + width, y: node.y + height / 2 }
    };
  };

  // Bezier path generator
  const createBezierPath = (p1, p2) => {
    const dx = Math.abs(p2.x - p1.x) * 0.5;
    return `M ${p1.x} ${p1.y} C ${p1.x + dx} ${p1.y}, ${p2.x - dx} ${p2.y}, ${p2.x} ${p2.y}`;
  };

  // Execution Simulation with Node Highlighting
  const handleExecute = async () => {
    setExecuting(true);
    setExecutionResult(null);

    try {
      // Simulate sequential / parallel step highlighting
      for (const node of nodes) {
        setActiveNodeId(node.id);
        await new Promise(r => setTimeout(r, 450));
      }
      setActiveNodeId(null);

      const res = await fetch('/api/canvas/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow_name: workflowName,
          nodes: nodes.map(n => ({ id: n.id, type: n.type, data: { label: n.label } })),
          edges: edges
        })
      });
      const data = await res.json();
      setExecutionResult(data);
    } catch (err) {
      setExecutionResult({ status: 'error', final_output: String(err) });
    } finally {
      setExecuting(false);
      setActiveNodeId(null);
    }
  };

  return (
    <div className="view-container animate-fade-in" onMouseUp={handleMouseUp}>
      {/* Header */}
      <div className="view-header">
        <div>
          <h2 className="view-title flex items-center gap-2">
            <GitFork className="text-indigo-400" /> Visual Workflow Canvas (DAG Studio)
          </h2>
          <p className="view-subtitle">
            Drag nodes freely, connect output ports to input ports to create <strong>Forks (Fan-Out)</strong> and <strong>Joins (Fan-In)</strong>.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button 
            className="primary-btn flex items-center gap-2"
            onClick={handleExecute}
            disabled={executing || nodes.length === 0}
          >
            <Play size={16} /> {executing ? 'Running DAG Pipeline...' : '▶️ Run Workflow DAG'}
          </button>
        </div>
      </div>

      {/* Quick Templates Bar */}
      <div className="mb-4 flex items-center gap-2 flex-wrap">
        <span className="text-xs text-slate-400 font-semibold flex items-center gap-1">
          <Sparkles size={14} className="text-amber-400" /> Quick Fork Templates:
        </span>
        <button className="template-pill-btn" onClick={() => applyTemplate('fork_swarm')}>
          🔱 1-to-3 Parallel Swarm Fork
        </button>
        <button className="template-pill-btn" onClick={() => applyTemplate('hitl_safety')}>
          🛡️ HITL Approval Fork
        </button>
        <button className="template-pill-btn" onClick={() => applyTemplate('debate_swarm')}>
          ⚖️ Multi-Agent Debate
        </button>
      </div>

      {/* Canvas Grid Layout */}
      <div className="canvas-grid-layout">
        {/* Node Palette Sidebar */}
        <div className="canvas-sidebar-palette">
          <h4 className="palette-title">Node Palette</h4>
          <p className="text-xs text-slate-400 mb-3">Click to spawn onto canvas:</p>
          
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

          <div className="mt-4 p-3 bg-slate-900/60 border border-slate-800 rounded-lg text-[11px] text-slate-400 leading-relaxed">
            <strong className="text-indigo-300 block mb-1">💡 How to Create a Fork:</strong>
            1. Click the <span className="text-pink-400 font-bold">Pink Output Port (●)</span> on the parent node.<br/>
            2. Click the <span className="text-sky-400 font-bold">Cyan Input Port (●)</span> on 2 or 3 worker nodes.<br/>
            3. <em>The dashed pink lines indicate active parallel forking branches!</em>
          </div>
        </div>

        {/* 2D Interactive Visual Board */}
        <div 
          ref={canvasRef}
          className="canvas-board-2d"
          onMouseMove={handleMouseMove}
          onClick={() => setConnectingSourceId(null)}
        >
          {/* SVG Connection Layer */}
          <svg className="canvas-svg-layer">
            <defs>
              <marker id="arrowhead" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
                <polygon points="0 0, 8 4, 0 8" fill="#6366f1" />
              </marker>
              <marker id="arrowhead-fork" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
                <polygon points="0 0, 8 4, 0 8" fill="#ec4899" />
              </marker>
            </defs>

            {/* Rendered Existing Edges */}
            {edges.map(edge => {
              const srcNode = nodes.find(n => n.id === edge.source);
              const tgtNode = nodes.find(n => n.id === edge.target);
              if (!srcNode || !tgtNode) return null;

              const srcPort = getNodePorts(srcNode).outPort;
              const tgtPort = getNodePorts(tgtNode).inPort;
              const pathStr = createBezierPath(srcPort, tgtPort);
              const midX = (srcPort.x + tgtPort.x) / 2;
              const midY = (srcPort.y + tgtPort.y) / 2;

              return (
                <g key={edge.id} className="group">
                  <path 
                    d={pathStr} 
                    className={`dag-wire ${edge.isFork ? 'dag-wire-fork' : ''} ${activeNodeId === edge.source ? 'dag-wire-active' : ''}`}
                    markerEnd={edge.isFork ? "url(#arrowhead-fork)" : "url(#arrowhead)"}
                  />
                  {/* Delete Wire Button at Midpoint */}
                  <g 
                    transform={`translate(${midX - 8}, ${midY - 8})`} 
                    className="cursor-pointer opacity-40 hover:opacity-100 transition"
                    onClick={(e) => removeEdge(edge.id, e)}
                  >
                    <circle cx="8" cy="8" r="8" fill="#1e293b" stroke="#f43f5e" strokeWidth="1.5" />
                    <text x="8" y="11" textAnchor="middle" fill="#f43f5e" fontSize="9" fontWeight="bold">✕</text>
                  </g>
                </g>
              );
            })}

            {/* Active Drawing Wire */}
            {connectingSourceId && (() => {
              const srcNode = nodes.find(n => n.id === connectingSourceId);
              if (!srcNode) return null;
              const srcPort = getNodePorts(srcNode).outPort;
              const pathStr = createBezierPath(srcPort, mousePos);
              return (
                <path 
                  d={pathStr} 
                  className="dag-wire"
                  style={{ stroke: '#ec4899', strokeDasharray: '4 4' }}
                />
              );
            })()}
          </svg>

          {/* Rendered Draggable Nodes */}
          {nodes.map((node) => {
            const tmpl = NODE_TYPES.find(t => t.type === node.type) || NODE_TYPES[0];
            const Icon = tmpl.icon;
            const isExecutingThis = activeNodeId === node.id;
            const isConnectingFromThis = connectingSourceId === node.id;

            return (
              <div
                key={node.id}
                style={{ left: `${node.x}px`, top: `${node.y}px` }}
                className={`dag-node-draggable ${tmpl.color} ${isExecutingThis ? 'executing' : ''} ${isConnectingFromThis ? 'selected' : ''}`}
                onMouseDown={(e) => handleMouseDownNode(node.id, e)}
              >
                {/* Input Port (Cyan) */}
                <div 
                  className="node-port node-port-in"
                  title="Input Port: Click to connect wire here"
                  onClick={(e) => handleCompleteConnect(node.id, e)}
                />

                {/* Output Port (Pink) */}
                <div 
                  className="node-port node-port-out"
                  title="Output Port: Click to start a new connection or Fork branch"
                  onClick={(e) => handleStartConnect(node.id, e)}
                />

                {/* Card Header */}
                <div className="flex items-center justify-between mb-1.5">
                  <span className="node-type-tag">{node.type.toUpperCase()}</span>
                  <button 
                    onClick={(e) => removeNode(node.id, e)}
                    className="text-slate-500 hover:text-rose-400 transition"
                    title="Delete Node"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>

                {/* Card Content */}
                <div className="flex items-center gap-2">
                  <Icon size={16} className="text-slate-300 shrink-0" />
                  <span className="text-xs font-semibold text-slate-100 truncate">{node.label}</span>
                </div>
                <div className="text-[10px] text-slate-400 mt-1">
                  Pos: ({Math.round(node.x)}, {Math.round(node.y)})
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Execution Results & Live Trace */}
      {executionResult && (
        <div className="canvas-execution-report mt-6 animate-fade-in">
          <div className="report-header">
            <CheckCircle2 size={18} className="text-emerald-400" />
            <h4 className="text-sm font-semibold text-emerald-100">
              DAG Execution Succeeded ({executionResult.duration_ms}ms)
            </h4>
            <span className="text-xs text-emerald-300 ml-auto font-mono">
              {executionResult.nodes_count} Nodes Executed
            </span>
          </div>

          <p className="text-xs text-emerald-200 mb-3">{executionResult.final_output}</p>

          <div className="trace-list">
            {executionResult.execution_trace?.map((step, idx) => (
              <div key={idx} className="trace-step-item">
                <span className="badge badge-outline text-[10px]">{step.type}</span>
                <span className="text-xs font-medium text-slate-200">{step.label}</span>
                <span className="text-xs text-slate-400 ml-auto font-mono">{step.output}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
