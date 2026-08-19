import React, { useState, useEffect, useRef } from 'react';
import { api } from '../api/client';

const STATUS_COLORS = {
  pending: '#f59e0b',
  running: '#3b82f6',
  completed: '#22c55e',
  failed: '#ef4444',
  partial: '#f97316'
};

const STATUS_ICONS = {
  pending: '⏳',
  running: '🔄',
  completed: '✅',
  failed: '❌',
  partial: '⚠️'
};

function TaskNode({ task, isActive }) {
  return (
    <div className={`task-node ${task.status} ${isActive ? 'active' : ''}`} style={{
      padding: '12px 16px',
      borderRadius: '10px',
      background: task.status === 'completed' ? 'rgba(34,197,94,0.1)' :
                  task.status === 'running' ? 'rgba(59,130,246,0.15)' :
                  task.status === 'failed' ? 'rgba(239,68,68,0.1)' :
                  'rgba(255,255,255,0.04)',
      border: `1px solid ${STATUS_COLORS[task.status] || '#333'}`,
      marginBottom: '8px',
      transition: 'all 0.3s ease'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
        <span style={{ fontSize: '16px' }}>{STATUS_ICONS[task.status] || '⏳'}</span>
        <strong style={{ color: '#e0e0e0', fontSize: '13px' }}>{task.task_id}</strong>
        {task.skill && <span className="badge" style={{ background: 'rgba(139,92,246,0.2)', color: '#a78bfa', fontSize: '10px', padding: '2px 6px', borderRadius: '4px' }}>{task.skill}</span>}
      </div>
      <p style={{ color: '#aaa', fontSize: '12px', margin: 0, lineHeight: '1.4' }}>{task.description}</p>
      {task.depends_on && task.depends_on.length > 0 && (
        <div style={{ marginTop: '4px', fontSize: '10px', color: '#666' }}>
          Depends on: {task.depends_on.join(', ')}
        </div>
      )}
      {task.result && (
        <div style={{ marginTop: '8px', padding: '8px', background: 'rgba(0,0,0,0.2)', borderRadius: '6px', fontSize: '11px', color: '#ccc', maxHeight: '100px', overflowY: 'auto' }}>
          {task.result.substring(0, 300)}{task.result.length > 300 ? '...' : ''}
        </div>
      )}
    </div>
  );
}

export default function OrchestratorView({ models }) {
  const [prompt, setPrompt] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [maxWorkers, setMaxWorkers] = useState(4);
  const [isRunning, setIsRunning] = useState(false);
  const [dag, setDag] = useState(null);
  const [events, setEvents] = useState([]);
  const [finalResult, setFinalResult] = useState(null);
  const [error, setError] = useState('');
  const eventSourceRef = useRef(null);
  const eventsEndRef = useRef(null);

  useEffect(() => {
    if (eventsEndRef.current) {
      eventsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events]);

  const handleRun = async () => {
    if (!prompt.trim()) return;
    
    setIsRunning(true);
    setDag(null);
    setEvents([]);
    setFinalResult(null);
    setError('');

    try {
      const response = await fetch('/api/orchestrator/run-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt.trim(),
          model: selectedModel || undefined,
          max_workers: maxWorkers
        })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const eventData = JSON.parse(line.slice(6));
              setEvents(prev => [...prev, eventData]);
              
              if (eventData.type === 'dag_created') {
                setDag(eventData);
              }
              if (eventData.type === 'worker_complete' || eventData.type === 'worker_failed') {
                setDag(prev => {
                  if (!prev) return prev;
                  const tasks = [...(prev.tasks || [])];
                  const idx = tasks.findIndex(t => t.task_id === eventData.task_id);
                  if (idx >= 0) {
                    tasks[idx] = { ...tasks[idx], status: eventData.status || 'completed' };
                  }
                  return { ...prev, tasks };
                });
              }
              if (eventData.type === 'final_result') {
                setFinalResult(eventData.result);
              }
              if (eventData.type === 'error') {
                setError(eventData.message || 'An error occurred');
              }
            } catch (e) { /* skip unparseable */ }
          }
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1200px' }}>
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ color: '#f0f0f0', margin: 0, fontSize: '22px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          🤖 Multi-Agent Orchestrator
          <span style={{ fontSize: '12px', background: 'rgba(139,92,246,0.2)', color: '#a78bfa', padding: '3px 10px', borderRadius: '12px' }}>Phase 2</span>
        </h2>
        <p style={{ color: '#888', fontSize: '13px', marginTop: '6px' }}>
          Decompose complex tasks into a DAG of sub-tasks executed by specialized worker agents in parallel.
        </p>
      </div>

      {/* Input Section */}
      <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', padding: '20px', marginBottom: '20px' }}>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe a complex task requiring multiple agents... (e.g., 'Research the best vacation spots in Italy, plan a 7-day itinerary, budget the trip for 2 people, and create a packing list')"
          style={{ width: '100%', minHeight: '80px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '12px', color: '#e0e0e0', fontSize: '13px', resize: 'vertical', fontFamily: 'inherit' }}
          disabled={isRunning}
        />
        <div style={{ display: 'flex', gap: '12px', marginTop: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '8px 12px', color: '#ccc', fontSize: '12px' }}
          >
            <option value="">Default Model</option>
            {(models || []).map(m => (
              <option key={m.id} value={m.id}>{m.id}</option>
            ))}
          </select>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <label style={{ color: '#888', fontSize: '12px' }}>Max Workers:</label>
            <input
              type="number"
              min="1"
              max="8"
              value={maxWorkers}
              onChange={(e) => setMaxWorkers(parseInt(e.target.value) || 4)}
              style={{ width: '50px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '8px', color: '#ccc', fontSize: '12px', textAlign: 'center' }}
            />
          </div>
          <button
            onClick={handleRun}
            disabled={isRunning || !prompt.trim()}
            style={{
              background: isRunning ? 'rgba(139,92,246,0.3)' : 'linear-gradient(135deg, #7c3aed, #6d28d9)',
              color: '#fff',
              border: 'none',
              borderRadius: '8px',
              padding: '10px 24px',
              cursor: isRunning ? 'wait' : 'pointer',
              fontSize: '13px',
              fontWeight: '600',
              marginLeft: 'auto'
            }}
          >
            {isRunning ? '⏳ Orchestrating...' : '🚀 Run Orchestration'}
          </button>
        </div>
      </div>

      {/* DAG Visualization */}
      {dag && (
        <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', padding: '20px', marginBottom: '20px' }}>
          <h3 style={{ color: '#e0e0e0', margin: '0 0 16px 0', fontSize: '15px' }}>
            📊 Task DAG <span style={{ color: '#888', fontWeight: 'normal', fontSize: '12px' }}>({dag.total_tasks || dag.tasks?.length || 0} tasks)</span>
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
            {(dag.tasks || []).map(task => (
              <TaskNode key={task.task_id} task={task} isActive={task.status === 'running'} />
            ))}
          </div>
        </div>
      )}

      {/* Live Events Stream */}
      {events.length > 0 && (
        <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', padding: '20px', marginBottom: '20px' }}>
          <h3 style={{ color: '#e0e0e0', margin: '0 0 12px 0', fontSize: '15px' }}>📡 Live Events</h3>
          <div style={{ maxHeight: '250px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '11px' }}>
            {events.map((ev, i) => (
              <div key={i} style={{ padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.04)', color: ev.type === 'error' ? '#ef4444' : ev.type?.includes('complete') ? '#22c55e' : '#aaa' }}>
                <span style={{ color: '#666', marginRight: '8px' }}>[{ev.type}]</span>
                {ev.message || ev.description || ev.task_id || JSON.stringify(ev).substring(0, 120)}
              </div>
            ))}
            <div ref={eventsEndRef} />
          </div>
        </div>
      )}

      {/* Final Result */}
      {finalResult && (
        <div style={{ background: 'rgba(34,197,94,0.05)', border: '1px solid rgba(34,197,94,0.2)', borderRadius: '12px', padding: '20px', marginBottom: '20px' }}>
          <h3 style={{ color: '#22c55e', margin: '0 0 12px 0', fontSize: '15px' }}>✅ Orchestration Result</h3>
          <div style={{ color: '#ccc', fontSize: '13px', lineHeight: '1.6', whiteSpace: 'pre-wrap' }}>
            {finalResult.synthesized_response || finalResult.response || JSON.stringify(finalResult, null, 2)}
          </div>
          {finalResult.elapsed_seconds && (
            <div style={{ marginTop: '12px', color: '#888', fontSize: '11px' }}>
              Completed in {finalResult.elapsed_seconds}s | {finalResult.total_tasks || 0} tasks | 
              {finalResult.total_prompt_tokens || 0} prompt + {finalResult.total_completion_tokens || 0} completion tokens
            </div>
          )}
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '12px', padding: '16px', color: '#ef4444' }}>
          ❌ {error}
        </div>
      )}
    </div>
  );
}
