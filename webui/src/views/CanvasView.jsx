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
  const scrollContainerRef = useRef(null);
  const canvasRef = useRef(null);
  const isPaletteDraggingRef = useRef(false);

  // Dynamic Canvas Dimensions (Auto-Expands horizontally and vertically as more agents are added)
  const canvasBoardWidth = Math.max(2600, ...nodes.map(n => (n.x || 0) + 400));
  const canvasBoardHeight = Math.max(1200, ...nodes.map(n => (n.y || 0) + 300));

  // Wire Connection State
  const [connectingSourceId, setConnectingSourceId] = useState(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  // Execution State
  const [executing, setExecuting] = useState(false);
  const [activeNodeIds, setActiveNodeIds] = useState([]);
  const [executionResult, setExecutionResult] = useState(null);

  // Globally Unique ID Generator (Prevents React key collisions and phantom nodes)
  const generateUniqueId = (prefix = 'node') => {
    return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).substring(2, 8)}`;
  };

  // Load Template
  const applyTemplate = (key) => {
    const tmpl = PREBUILT_TEMPLATES[key];
    if (!tmpl) return;
    setWorkflowName(tmpl.name);
    // Clone nodes with fresh unique IDs
    const idMap = {};
    const clonedNodes = tmpl.nodes.map(n => {
      const freshId = generateUniqueId(n.id);
      idMap[n.id] = freshId;
      return { ...n, id: freshId };
    });
    const clonedEdges = tmpl.edges.map(e => ({
      ...e,
      id: `e_${idMap[e.source] || e.source}_${idMap[e.target] || e.target}_${Date.now().toString(36)}`,
      source: idMap[e.source] || e.source,
      target: idMap[e.target] || e.target
    }));
    setNodes(clonedNodes);
    setEdges(clonedEdges);
    setExecutionResult(null);
  };

  // Add Node via Click
  const addNode = (type) => {
    const nextId = generateUniqueId('node');
    const tmpl = NODE_TYPES.find(t => t.type === type) || NODE_TYPES[0];
    const newNode = {
      id: nextId,
      type: tmpl.type,
      label: `${nodes.length + 1}. ${tmpl.label}`,
      x: 120 + (nodes.length * 60),
      y: 120 + ((nodes.length % 4) * 80)
    };
    setNodes(prev => [...prev, newNode]);
  };

  // Remove Node with edge isFork recalculation
  const removeNode = (id, e) => {
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    setNodes(prev => prev.filter(n => n.id !== id));
    setEdges(prev => {
      const remaining = prev.filter(edge => edge.source !== id && edge.target !== id);
      const sourceCounts = {};
      remaining.forEach(edge => {
        sourceCounts[edge.source] = (sourceCounts[edge.source] || 0) + 1;
      });
      return remaining.map(edge => ({
        ...edge,
        isFork: (sourceCounts[edge.source] || 0) > 1
      }));
    });
  };

  // Clear Canvas / Start Blank
  const clearCanvas = () => {
    setNodes([]);
    setEdges([]);
    setExecutionResult(null);
  };

  // HTML5 Drag & Drop from Palette directly onto Canvas
  const handleDropFromPalette = (e) => {
    e.preventDefault();
    const type = e.dataTransfer.getData('text/plain') || e.dataTransfer.getData('application/node-type');
    if (!type) return;

    const container = scrollContainerRef.current;
    if (!container) return;
    const rect = container.getBoundingClientRect();
    
    // Position node centered under the user's drop cursor
    const dropCanvasX = Math.max(20, Math.min(canvasBoardWidth - 260, (e.clientX - rect.left) + container.scrollLeft - 120));
    const dropCanvasY = Math.max(20, Math.min(canvasBoardHeight - 120, (e.clientY - rect.top) + container.scrollTop - 40));

    const nextId = generateUniqueId('node');
    const tmpl = NODE_TYPES.find(t => t.type === type) || NODE_TYPES[0];
    const newNode = {
      id: nextId,
      type: tmpl.type,
      label: `${nodes.length + 1}. ${tmpl.label}`,
      x: Math.round(dropCanvasX),
      y: Math.round(dropCanvasY)
    };
    setNodes(prev => [...prev, newNode]);
  };

  // Mouse Handlers for Freeform Dragging with Scroll Compensation
  const handleMouseDownNode = (id, e) => {
    if (e.target.classList?.contains('node-port') || e.target.closest('button') || e.target.closest('.node-delete-btn')) return;
    e.preventDefault(); // Prevents browser ghost drag images and text selection
    setDraggingNodeId(id);
    const node = nodes.find(n => n.id === id);
    const container = scrollContainerRef.current;
    if (!node || !container) return;
    const rect = container.getBoundingClientRect();
    const currentX = (e.clientX - rect.left) + container.scrollLeft;
    const currentY = (e.clientY - rect.top) + container.scrollTop;
    setDragOffset({
      x: currentX - node.x,
      y: currentY - node.y
    });
  };

  // Window-level mouse tracking for 100% reliable drag-and-drop
  useEffect(() => {
    if (!draggingNodeId && !connectingSourceId) return;

    const handleWindowMouseMove = (e) => {
      const container = scrollContainerRef.current;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const currentX = (e.clientX - rect.left) + container.scrollLeft;
      const currentY = (e.clientY - rect.top) + container.scrollTop;
      setMousePos({ x: currentX, y: currentY });

      if (draggingNodeId) {
        setNodes(prev => prev.map(node => {
          if (node.id === draggingNodeId) {
            const newX = Math.max(10, Math.min(canvasBoardWidth - 250, currentX - dragOffset.x));
            const newY = Math.max(10, Math.min(canvasBoardHeight - 110, currentY - dragOffset.y));
            return { ...node, x: newX, y: newY };
          }
          return node;
        }));
      }
    };

    const handleWindowMouseUp = (e) => {
      setDraggingNodeId(null);
      if (connectingSourceId && e && !e.target.classList?.contains('node-port-in')) {
        setConnectingSourceId(null);
      }
    };

    window.addEventListener('mousemove', handleWindowMouseMove);
    window.addEventListener('mouseup', handleWindowMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleWindowMouseMove);
      window.removeEventListener('mouseup', handleWindowMouseUp);
    };
  }, [draggingNodeId, connectingSourceId, dragOffset, canvasBoardWidth, canvasBoardHeight]);

  // Port Connection Handlers (Supports both Drag-and-Drop AND Click-to-Connect!)
  const handleStartConnect = (sourceId, e) => {
    e.stopPropagation();
    e.preventDefault();
    setConnectingSourceId(sourceId);
    const container = scrollContainerRef.current;
    if (container) {
      const rect = container.getBoundingClientRect();
      setMousePos({
        x: (e.clientX - rect.left) + container.scrollLeft,
        y: (e.clientY - rect.top) + container.scrollTop
      });
    }
  };

  // Cycle & Acyclicity Validator for DAG Integrity
  const checkCycle = (nodesList, edgesList, proposedEdge) => {
    if (proposedEdge.source === proposedEdge.target) return true; // Self-loop

    const testEdges = [...edgesList, proposedEdge];
    const adj = {};
    nodesList.forEach(n => { adj[n.id] = []; });
    testEdges.forEach(e => {
      if (adj[e.source]) adj[e.source].push(e.target);
    });

    const state = {}; // 0: unvisited, 1: visiting in stack, 2: visited
    nodesList.forEach(n => { state[n.id] = 0; });

    function dfs(nodeId) {
      state[nodeId] = 1;
      for (const neighbor of (adj[nodeId] || [])) {
        if (state[neighbor] === 1) return true; // Back-edge = Cycle!
        if (state[neighbor] === 0) {
          if (dfs(neighbor)) return true;
        }
      }
      state[nodeId] = 2;
      return false;
    }

    for (const n of nodesList) {
      if (state[n.id] === 0) {
        if (dfs(n.id)) return true;
      }
    }
    return false;
  };

  const [dagAlert, setDagAlert] = useState(null);

  const showDAGWarning = (msg) => {
    setDagAlert(msg);
    setTimeout(() => setDagAlert(null), 4000);
  };

  const handleCompleteConnect = (targetId, e) => {
    e.stopPropagation();
    e.preventDefault();
    if (!connectingSourceId) return;

    if (connectingSourceId === targetId) {
      showDAGWarning("🚫 Self-loops are forbidden in a Directed Acyclic Graph (DAG)!");
      setConnectingSourceId(null);
      return;
    }

    // Check if edge already exists
    const exists = edges.some(edge => edge.source === connectingSourceId && edge.target === targetId);
    if (exists) {
      setConnectingSourceId(null);
      return;
    }

    const proposedEdge = {
      id: `e_${connectingSourceId}_${targetId}_${Date.now()}`,
      source: connectingSourceId,
      target: targetId,
      isFork: false
    };

    // Strict DAG Acyclicity Check: Block any backward or circular edges
    if (checkCycle(nodes, edges, proposedEdge)) {
      showDAGWarning("🚫 Circular dependency detected! Cycles are not permitted in a DAG (A ➔ B ➔ A).");
      setConnectingSourceId(null);
      return;
    }

    // Check if source already has other outgoing edges (marks it as a Fork!)
    const outgoingCount = edges.filter(e => e.source === connectingSourceId).length;
    proposedEdge.isFork = outgoingCount >= 1;

    // Update any existing edges from this source to also be marked as forks
    setEdges(prev => [
      ...prev.map(e => e.source === connectingSourceId ? { ...e, isFork: true } : e),
      proposedEdge
    ]);

    setConnectingSourceId(null);
  };

  const removeEdge = (edgeId, e) => {
    if (e) e.stopPropagation();
    setEdges(prev => {
      const remaining = prev.filter(e => e.id !== edgeId);
      const sourceCounts = {};
      remaining.forEach(edge => {
        sourceCounts[edge.source] = (sourceCounts[edge.source] || 0) + 1;
      });
      return remaining.map(edge => ({
        ...edge,
        isFork: (sourceCounts[edge.source] || 0) > 1
      }));
    });
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

  // Execution Simulation with Wave / Stage Highlighting
  const handleExecute = async () => {
    setExecuting(true);
    setExecutionResult(null);
    setActiveNodeIds([]);

    try {
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
      
      if (!res.ok) {
        throw new Error(data.detail || data.error || 'Execution failed');
      }

      // Animate through topological execution stages
      if (data.stages && data.stages.length > 0) {
        for (const stageNodeIds of data.stages) {
          setActiveNodeIds(stageNodeIds);
          await new Promise(r => setTimeout(r, 650));
        }
      } else {
        for (const node of nodes) {
          setActiveNodeIds([node.id]);
          await new Promise(r => setTimeout(r, 450));
        }
      }
      setActiveNodeIds([]);
      setExecutionResult(data);
    } catch (err) {
      setExecutionResult({ status: 'error', final_output: String(err) });
    } finally {
      setExecuting(false);
      setActiveNodeIds([]);
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
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg border border-slate-700 transition"
            onClick={clearCanvas}
            title="Clear all nodes and start blank"
          >
            🗑️ Clear Canvas
          </button>
          <button 
            className="primary-btn flex items-center gap-2"
            onClick={handleExecute}
            disabled={executing || nodes.length === 0}
          >
            <Play size={16} /> {executing ? 'Running DAG Pipeline...' : '▶️ Run Workflow DAG'}
          </button>
        </div>
      </div>

      {/* DAG Integrity Alert Banner */}
      {dagAlert && (
        <div className="mb-4 p-3 bg-rose-950/90 border border-rose-500 rounded-lg text-xs text-rose-200 flex items-center gap-2 animate-fade-in shadow-xl">
          <ShieldAlert size={16} className="text-rose-400 shrink-0" />
          <span><strong>DAG Topology Violation:</strong> {dagAlert}</span>
          <button onClick={() => setDagAlert(null)} className="ml-auto text-rose-400 hover:text-white text-sm font-bold">✕</button>
        </div>
      )}

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
          <p className="text-xs text-slate-400 mb-3">Drag onto canvas or click to add:</p>
          
          <div className="palette-items">
            {NODE_TYPES.map((nt) => {
              const Icon = nt.icon;
              return (
                <div
                  key={nt.type}
                  draggable={true}
                  onDragStart={(e) => {
                    isPaletteDraggingRef.current = true;
                    e.dataTransfer.setData('text/plain', nt.type);
                    e.dataTransfer.setData('application/node-type', nt.type);
                    e.dataTransfer.effectAllowed = 'copy';
                  }}
                  onDragEnd={() => {
                    setTimeout(() => {
                      isPaletteDraggingRef.current = false;
                    }, 250);
                  }}
                  onClick={(e) => {
                    if (isPaletteDraggingRef.current) {
                      e.preventDefault();
                      e.stopPropagation();
                      return;
                    }
                    addNode(nt.type);
                  }}
                  className="palette-node-btn"
                  title="Drag and drop onto canvas or click to add"
                >
                  <Icon size={16} className="text-indigo-400" />
                  <div className="text-left">
                    <div className="text-xs font-semibold text-slate-200">{nt.label}</div>
                    <div className="text-[10px] text-slate-400">{nt.type.toUpperCase()} • Drag Me</div>
                  </div>
                  <Plus size={14} className="ml-auto text-slate-500" />
                </div>
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
            1. Drag nodes from palette onto the canvas.<br/>
            2. Click the <span className="text-pink-400 font-bold">Pink Output Port (●)</span> on the parent node.<br/>
            3. Click the <span className="text-sky-400 font-bold">Cyan Input Port (●)</span> on 2 or 3 worker nodes.<br/>
            4. <em>The dashed pink lines indicate active parallel forking branches!</em>
          </div>
        </div>

        {/* 2D Interactive Scrollable Visual Workspace */}
        <div 
          ref={scrollContainerRef} 
          className="canvas-scroll-container"
          onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; }}
          onDrop={handleDropFromPalette}
        >
          <div 
            ref={canvasRef}
            className="canvas-board-2d"
            style={{ width: `${canvasBoardWidth}px`, height: `${canvasBoardHeight}px` }}
            onMouseMove={handleMouseMove}
            onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; }}
            onDrop={handleDropFromPalette}
            onClick={() => setConnectingSourceId(null)}
          >
            {/* SVG Connection Layer */}
            <svg 
              className="canvas-svg-layer"
              width={canvasBoardWidth}
              height={canvasBoardHeight}
              style={{ width: `${canvasBoardWidth}px`, height: `${canvasBoardHeight}px` }}
            >
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
                      className={`dag-wire ${edge.isFork ? 'dag-wire-fork' : ''} ${activeNodeIds.includes(edge.source) ? 'dag-wire-active' : ''}`}
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
              const isExecutingThis = activeNodeIds.includes(node.id);
              const isConnectingFromThis = connectingSourceId === node.id;

              return (
                <div
                  key={node.id}
                  style={{ left: `${node.x}px`, top: `${node.y}px` }}
                  className={`dag-node-draggable ${tmpl.color} ${isExecutingThis ? 'executing' : ''} ${isConnectingFromThis ? 'selected' : ''}`}
                  onMouseDown={(e) => handleMouseDownNode(node.id, e)}
                >
                  {/* Input Port (Cyan) - Accepts both Drop and Click */}
                  <div 
                    className={`node-port node-port-in ${connectingSourceId && connectingSourceId !== node.id ? 'highlight-target' : ''}`}
                    title="Input Port: Drop wire here or click to connect"
                    onMouseUp={(e) => handleCompleteConnect(node.id, e)}
                    onClick={(e) => handleCompleteConnect(node.id, e)}
                  />

                  {/* Output Port (Pink) - Starts wire drag or click */}
                  <div 
                    className="node-port node-port-out"
                    title="Output Port: Drag to another node's input port to connect or Fork"
                    onMouseDown={(e) => handleStartConnect(node.id, e)}
                    onClick={(e) => handleStartConnect(node.id, e)}
                  />

                  {/* Card Header */}
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="node-type-tag">{node.type.toUpperCase()}</span>
                    <button 
                      type="button"
                      onMouseDown={(e) => { e.stopPropagation(); }}
                      onClick={(e) => { e.stopPropagation(); e.preventDefault(); removeNode(node.id, e); }}
                      className="node-delete-btn"
                      title="Delete Node"
                    >
                      <Trash2 size={13} className="text-slate-400 hover:text-rose-400" />
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
              {executionResult.stages_count ? `${executionResult.stages_count} Stages • ` : ''}{executionResult.nodes_count} Nodes Executed
            </span>
          </div>

          <p className="text-xs text-emerald-200 mb-3 whitespace-pre-wrap">{executionResult.final_output}</p>

          <div className="trace-list">
            {executionResult.execution_trace?.map((step, idx) => (
              <div key={idx} className="trace-step-item flex items-center gap-3">
                {step.stage && (
                  <span className="px-2 py-0.5 rounded bg-indigo-950/80 border border-indigo-500/40 text-[10px] font-mono text-indigo-300">
                    Stage {step.stage}
                  </span>
                )}
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
