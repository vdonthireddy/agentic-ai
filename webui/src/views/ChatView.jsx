import React, { useState, useRef, useEffect, useMemo } from 'react';
import { api } from '../api/client';
import { Send, Trash2, Copy, Check, Terminal, Sparkles, Wrench, Mic, MicOff, Volume2, ShieldAlert, Layers, Minimize2, AlertTriangle } from 'lucide-react';
import HITLApprovalModal from '../components/HITLApprovalModal';
import ArtifactPanel from '../components/ArtifactPanel';

const PROMPT_CHIPS = [
  { label: '🍕 Split $184.50 dinner bill for 4', prompt: 'Our dinner bill for 4 people is $184.50. Calculate an 18% tip and the split per person using calculator.' },
  { label: '🥐 3-Day Paris trip with weather', prompt: 'Check the live weather in Paris using weather and give me a 3-day vacation itinerary highlighting cozy bakeries.' },
  { label: '🎧 Find headphones & calculate deals', prompt: 'Find top-rated noise-canceling headphones in product_knowledge and calculate the discounted price with calculator.' },
  { label: '🍝 15-Min Creamy Pasta Recipe', prompt: 'Find a delicious 15-minute creamy pasta dinner using web_search and write a simple grocery list.' }
];

export default function ChatView({ models, skills, activeSkill, onSelectSkill, onChatFinished }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [selectedModel, setSelectedModel] = useState(models[0]?.id || 'ollama/gemma2:2b');
  const [selectedSkill, setSelectedSkill] = useState(activeSkill || '');
  const [loading, setLoading] = useState(false);
  const [compacting, setCompacting] = useState(false);
  const [streamingStatus, setStreamingStatus] = useState('');
  const [copied, setCopied] = useState(false);
  const [telemetry, setTelemetry] = useState({ promptTokens: 0, completionTokens: 0, toolsCount: 0 });
  const [sessionId, setSessionId] = useState(() => `conv_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`);
  const [turnCount, setTurnCount] = useState(0);
  const [activeArtifact, setActiveArtifact] = useState(null);

  // HITL state
  const [pendingHITL, setPendingHITL] = useState(null);

  // Voice state
  const [isRecording, setIsRecording] = useState(false);
  const [voiceTtsEnabled, setVoiceTtsEnabled] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const messagesEndRef = useRef(null);

  // Calculate estimated context weight
  const estimatedTokens = useMemo(() => {
    return Math.round(messages.reduce((acc, m) => acc + (typeof m.content === 'string' ? m.content.length / 4 : 20) + 4, 0));
  }, [messages]);

  const showCompactionAlert = estimatedTokens > 1500 || messages.length >= 8;

  useEffect(() => {
    if (activeSkill) setSelectedSkill(activeSkill);
  }, [activeSkill]);

  useEffect(() => {
    if (models.length > 0 && !selectedModel) {
      setSelectedModel(models[0].id);
    }
  }, [models]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading, streamingStatus]);

  // Periodic check for pending HITL requests
  useEffect(() => {
    let interval = null;
    if (loading) {
      interval = setInterval(async () => {
        try {
          const res = await fetch('/api/hitl/pending');
          const data = await res.json();
          if (data.pending && data.pending.length > 0) {
            setPendingHITL(data.pending[0]);
          }
        } catch (e) { /* ignore */ }
      }, 1000);
    } else {
      setPendingHITL(null);
    }
    return () => { if (interval) clearInterval(interval); };
  }, [loading]);

  const speakText = (text) => {
    if (!voiceTtsEnabled || typeof window === 'undefined' || !window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      const cleanText = text.replace(/[`*#_]/g, '');
      const utterance = new SpeechSynthesisUtterance(cleanText.substring(0, 300));
      utterance.rate = 1.05;
      window.speechSynthesis.speak(utterance);
    } catch (e) { /* ignore */ }
  };

  const handleClear = async (skipConfirm = false) => {
    if (!skipConfirm && !confirm('Are you sure you want to start a new conversation?')) return;
    setMessages([]);
    setTurnCount(0);
    const oldId = sessionId;
    const res = await api.clearChat(oldId).catch(() => ({}));
    const newConvId = res?.new_conversation_id || `conv_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    setSessionId(newConvId);
    onChatFinished?.();
  };

  const handleCompact = async () => {
    if (messages.length < 4 || compacting) return;
    setCompacting(true);
    try {
      const data = await api.compactChat({
        messages,
        keep_recent_turns: 2,
        model: selectedModel
      });

      if (data.tokens_saved > 0) {
        const milestoneMsg = {
          role: 'compaction_milestone',
          content: data.summary,
          tokens_saved: data.tokens_saved,
          savings_percent: data.savings_percent,
          pruned_count: data.messages_pruned_count,
          timestamp: new Date().toISOString()
        };
        // Replace previous messages with compacted list + milestone
        setMessages([...data.compacted_messages.filter(m => !m.is_compaction_summary), milestoneMsg]);
      }
    } catch (e) {
      console.error('Compaction failed:', e);
    } finally {
      setCompacting(false);
    }
  };

  const handleSend = async (customPrompt) => {
    const text = (customPrompt || input).trim();
    if (!text || loading || compacting) return;

    if (!customPrompt) setInput('');

    if (text.toLowerCase() === '/clear' || text.toLowerCase() === '/new') {
      await handleClear(true);
      return;
    }

    if (text.toLowerCase() === '/compact') {
      await handleCompact();
      return;
    }

    const nextTurn = turnCount + 1;
    setTurnCount(nextTurn);
    const turnId = `turn_${nextTurn}_${Date.now()}`;

    const userMsg = { role: 'user', content: text, timestamp: new Date().toISOString(), turn_id: turnId };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setStreamingStatus('⚡ Initializing agent reasoning loop...');

    try {
      // Use SSE streaming endpoint
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          model: selectedModel,
          skill_name: selectedSkill || undefined,
          session_id: sessionId,
          conversation_id: sessionId,
          turn_id: turnId
        })
      });

      if (!response.ok) {
        throw new Error(`Gateway returned HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let accumulatedResponse = '';
      let executedToolCalls = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const eventPayload = JSON.parse(line.slice(6));
              const { type, data } = eventPayload;

              if (type === 'step') {
                setStreamingStatus(`🛠️ Tool: ${data?.tool || 'Executing tool'}...`);
              } else if (type === 'final_result') {
                accumulatedResponse = data.response || 'Completed.';
                executedToolCalls = data.tool_calls || [];
                if (data.tokens) {
                  setTelemetry({
                    promptTokens: data.tokens.prompt_tokens || 0,
                    completionTokens: data.tokens.completion_tokens || 0,
                    toolsCount: executedToolCalls.length
                  });
                }
              } else if (type === 'error') {
                accumulatedResponse = `⚠️ ${data?.message || 'The model encountered an error or timed out while generating a response. Please check if the model is loaded in Ollama or select another model.'}`;
              }
            } catch (e) { /* ignore chunk parse error */ }
          }
        }
      }

      const botMsg = {
        role: 'assistant',
        content: accumulatedResponse || 'No response generated.',
        tool_calls: executedToolCalls,
        turn_id: turnId,
        timestamp: new Date().toISOString()
      };

      setMessages((prev) => [...prev, botMsg]);
      speakText(botMsg.content);
      onChatFinished?.();
    } catch (err) {
      // Fallback to static sendChat endpoint
      try {
        const data = await api.sendChat({
          message: text,
          model: selectedModel,
          skill_name: selectedSkill || undefined,
          session_id: sessionId,
          conversation_id: sessionId,
          turn_id: turnId
        });

        const botMsg = {
          role: 'assistant',
          content: data.response || 'No response returned.',
          tool_calls: data.tool_calls || [],
          turn_id: data.turn_id || turnId,
          timestamp: new Date().toISOString()
        };

        setMessages((prev) => [...prev, botMsg]);
        speakText(botMsg.content);
        if (data.tokens) {
          setTelemetry({
            promptTokens: data.tokens.prompt_tokens || 0,
            completionTokens: data.tokens.completion_tokens || 0,
            toolsCount: (data.tool_calls || []).length
          });
        }
        onChatFinished?.();
      } catch (fallbackErr) {
        setMessages((prev) => [
          ...prev,
          { role: 'error', content: fallbackErr.message || err.message, timestamp: new Date().toISOString() }
        ]);
      }
    } finally {
      setLoading(false);
      setStreamingStatus('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCopyJson = () => {
    const payload = JSON.stringify({ conversation_id: sessionId, session_id: sessionId, turns_count: turnCount, messages }, null, 2);
    navigator.clipboard.writeText(payload);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Voice recording handlers
  const handleToggleRecord = async () => {
    if (isRecording) {
      // Stop recording
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      setIsRecording(false);
    } else {
      // Start recording
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunksRef.current = [];
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;

        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) audioChunksRef.current.push(event.data);
        };

        mediaRecorder.onstop = async () => {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          const reader = new FileReader();
          reader.readAsDataURL(audioBlob);
          reader.onloadend = async () => {
            const base64Audio = reader.result.split(',')[1];
            try {
              const res = await fetch('/api/voice/transcribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ audio_base64: base64Audio })
              });
              const data = await res.json();
              if (data.transcription && !data.transcription.startsWith('[')) {
                setInput(data.transcription);
              }
            } catch (e) {
              console.error('Voice transcription error:', e);
            }
          };
          stream.getTracks().forEach((track) => track.stop());
        };

        mediaRecorder.start();
        setIsRecording(true);
      } catch (err) {
        alert('Microphone access not available or permitted.');
      }
    }
  };

  // HITL Approval callbacks
  const handleApproveHITL = async (requestId) => {
    try {
      await fetch(`/api/hitl/approve/${requestId}`, { method: 'POST' });
      setPendingHITL(null);
    } catch (e) { /* ignore */ }
  };

  const handleDenyHITL = async (requestId) => {
    try {
      await fetch(`/api/hitl/deny/${requestId}`, { method: 'POST' });
      setPendingHITL(null);
    } catch (e) { /* ignore */ }
  };

  // Group models
  const modelGroups = {};
  for (const m of models) {
    let group = 'Cloud Providers';
    if (m.provider === 'ollama' || m.is_local) group = 'Local Ollama';
    else if (m.provider === 'openai') group = 'OpenAI';
    else if (m.provider === 'anthropic') group = 'Anthropic Claude';
    else if (m.provider === 'gemini') group = 'Google Gemini';
    else if (m.provider === 'groq') group = 'Groq Cloud';
    else if (m.provider === 'deepseek') group = 'DeepSeek';
    else if (m.provider === 'mistral') group = 'Mistral AI';

    if (!modelGroups[group]) modelGroups[group] = [];
    modelGroups[group].push(m);
  }

  return (
    <div className="chat-layout">
      {/* HITL Safety Modal */}
      {pendingHITL && (
        <HITLApprovalModal
          request={pendingHITL}
          onApprove={handleApproveHITL}
          onDeny={handleDenyHITL}
          onClose={() => setPendingHITL(null)}
        />
      )}

      {/* Main Chat Stream */}
      <div className="glass-card chat-card">
        <div className="chat-header flex-between">
          <div className="chat-controls">
            <div className="control-item">
              <label>Model (Local & Cloud)</label>
              <select
                className="form-control-sm"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
              >
                {Object.entries(modelGroups).map(([group, list]) => (
                  <optgroup key={group} label={group}>
                    {list.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name || m.id}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </div>
            <div className="control-item">
              <label>Active Domain Skill</label>
              <select
                className="form-control-sm"
                value={selectedSkill}
                onChange={(e) => {
                  setSelectedSkill(e.target.value);
                  if (onSelectSkill) onSelectSkill(e.target.value);
                }}
              >
                <option value="">Standard Everyday Assistant</option>
                {skills.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="control-item" style={{ alignSelf: 'center', opacity: 0.85, fontSize: '11px' }}>
              <span className="badge badge-outline" title={`Conversation ID: ${sessionId}`}>
                💬 {sessionId.substring(0, 14)}...
              </span>
              {turnCount > 0 && (
                <span className="badge badge-accent" style={{ marginLeft: '4px' }}>
                  Turn {turnCount}
                </span>
              )}
            </div>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <button
              className={`btn btn-sm ${showCompactionAlert ? 'btn-accent' : 'btn-secondary'}`}
              onClick={handleCompact}
              disabled={messages.length < 4 || compacting}
              title="Compact earlier conversation turns to save tokens (/compact)"
            >
              <Minimize2 size={14} />
              <span>{compacting ? 'Compacting...' : `Compact (${estimatedTokens}t)`}</span>
            </button>
            <button
              className={`btn btn-sm ${voiceTtsEnabled ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setVoiceTtsEnabled(!voiceTtsEnabled)}
              title={voiceTtsEnabled ? 'TTS Audio Enabled' : 'TTS Audio Disabled'}
            >
              <Volume2 size={14} />
              <span>{voiceTtsEnabled ? 'TTS On' : 'TTS Off'}</span>
            </button>
            <button className="btn btn-secondary btn-sm" onClick={handleCopyJson} title="Copy full Conversation JSON">
              {copied ? <Check size={14} /> : <Copy size={14} />}
              <span>{copied ? 'Copied' : 'JSON'}</span>
            </button>
            <button className="btn btn-secondary btn-sm" onClick={() => handleClear(false)} title="Start new conversation (/clear)">
              <Trash2 size={14} />
              <span>New</span>
            </button>
          </div>
        </div>

        {/* Chat Messages */}
        <div className="chat-messages">
          {showCompactionAlert && (
            <div className="compaction-alert-banner flex items-center justify-between" style={{
              background: 'rgba(234, 179, 8, 0.15)',
              border: '1px solid rgba(234, 179, 8, 0.4)',
              borderRadius: '8px',
              padding: '8px 14px',
              marginBottom: '12px',
              fontSize: '12px',
              color: '#facc15'
            }}>
              <div className="flex items-center gap-2">
                <AlertTriangle size={15} />
                <span><strong>Context Alert</strong>: History is ~{estimatedTokens} tokens. Run <code>/compact</code> to summarize and free up context space.</span>
              </div>
              <button
                className="btn btn-sm"
                style={{ background: '#eab308', color: '#0f172a', fontWeight: 'bold', padding: '2px 8px', fontSize: '11px' }}
                onClick={handleCompact}
                disabled={compacting}
              >
                {compacting ? 'Compacting...' : 'Compact Now'}
              </button>
            </div>
          )}

          {messages.length === 0 ? (
            <div className="chat-welcome">
              <div className="welcome-icon">👋</div>
              <h3>Welcome to your Everyday AI Agent!</h3>
              <p>
                Equipped with real-world MCP tools: <strong>Calculator</strong>, <strong>Live Weather</strong>, <strong>Web Search</strong>, <strong>Shopping Catalog</strong>, <strong>Workspace Files</strong>, and <strong>Semantic Memory</strong>.
              </p>
              <div className="prompt-chips">
                {PROMPT_CHIPS.map((chip, idx) => (
                  <button key={idx} className="chip" onClick={() => handleSend(chip.prompt)}>
                    {chip.label}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, i) => (
              msg.role === 'compaction_milestone' ? (
                <div key={i} className="compaction-milestone-card" style={{
                  background: 'rgba(34, 197, 94, 0.08)',
                  border: '1px dashed rgba(34, 197, 94, 0.35)',
                  borderRadius: '10px',
                  padding: '12px 16px',
                  margin: '12px 0',
                  color: '#4ade80',
                  fontSize: '13px'
                }}>
                  <div className="flex items-center justify-between font-semibold" style={{ marginBottom: '6px' }}>
                    <span>📦 Context Compacted Successfully</span>
                    <span className="badge" style={{ background: 'rgba(34,197,94,0.2)', color: '#4ade80', fontSize: '11px' }}>
                      Saved {msg.tokens_saved} tokens ({msg.savings_percent}% reduction)
                    </span>
                  </div>
                  <div style={{ color: '#cbd5e1', fontSize: '12px', whiteSpace: 'pre-wrap' }}>
                    {msg.content}
                  </div>
                </div>
              ) : (
              <div key={i} className={`chat-message message-${msg.role}`}>
                <div className="message-bubble">
                  {msg.tool_calls && msg.tool_calls.length > 0 && (
                    <div className="tool-call-feed">
                      {msg.tool_calls.map((tc, idx) => (
                        <div key={idx} className="tool-call-bubble">
                          <div className="tool-call-header">
                            <span>🛠️ Executed Tool: <strong>{tc.tool || tc.name}</strong></span>
                            {(tc.tool === 'memory_store' || tc.name === 'memory_store') && (
                              <span className="badge" style={{ background: 'rgba(59,130,246,0.2)', color: '#60a5fa', marginLeft: '8px', fontSize: '10px' }}>
                                🧠 Saved to Memory
                              </span>
                            )}
                            {(tc.tool === 'load_skill' || tc.name === 'load_skill') && (
                              <span className="badge badge-accent" style={{ marginLeft: '8px', fontSize: '10px' }}>
                                ✨ Progressive Skill Loaded
                              </span>
                            )}
                          </div>
                          <div className="tool-call-detail">
                            <code>{JSON.stringify(tc.arguments || tc.args || {})}</code>
                            <div className="tool-output-preview">
                              ↳ {typeof (tc.output ?? tc.result) === 'string'
                                  ? (tc.output ?? tc.result).substring(0, 180)
                                  : JSON.stringify(tc.output ?? tc.result ?? {}).substring(0, 180)}
                              {String(tc.output ?? tc.result ?? '').length > 180 ? '...' : ''}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="message-content" style={{ whiteSpace: 'pre-wrap' }}>
                    {msg.content}
                  </div>
                </div>
              </div>
              )
            ))
          )}

          {loading && (
            <div className="chat-message message-bot">
              <div className="message-bubble">
                <span className="text-accent font-mono text-sm">
                  {streamingStatus || '⚡ Agent reasoning & executing tools...'}
                </span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="chat-input-bar">
          <button
            className={`btn btn-sm ${isRecording ? 'btn-danger' : 'btn-secondary'}`}
            style={{
              padding: '8px 12px',
              borderRadius: '8px',
              background: isRecording ? 'rgba(239,68,68,0.3)' : undefined,
              borderColor: isRecording ? '#ef4444' : undefined,
              color: isRecording ? '#ef4444' : undefined
            }}
            onClick={handleToggleRecord}
            title={isRecording ? 'Stop Recording' : 'Voice Input (Microphone)'}
          >
            {isRecording ? <MicOff size={16} /> : <Mic size={16} />}
          </button>
          <textarea
            rows={2}
            placeholder={isRecording ? '🎤 Listening...' : "Ask me anything... (e.g. 'Plan a weekend trip to Tokyo' or 'Remember my favorite coffee is Cappuccino')"}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button className="btn btn-primary" onClick={() => handleSend()} disabled={loading || !input.trim()}>
            <Send size={16} />
            <span>Send</span>
          </button>
        </div>
      </div>

      {/* Live Sidebar Panels / Artifacts Side-Panel */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', minWidth: activeArtifact ? '380px' : '260px' }}>
        {activeArtifact ? (
          <ArtifactPanel 
            artifact={activeArtifact} 
            onClose={() => setActiveArtifact(null)} 
          />
        ) : (
          <>
            <div className="glass-card">
              <div className="card-header flex items-center justify-between">
                <h3>🛠️ Active MCP Tools</h3>
              </div>
              <div className="card-body">
                <div className="tool-badge-list">
                  <div className="tool-item"><span>🧮</span> <code>calculator</code></div>
                  <div className="tool-item"><span>⛅</span> <code>weather</code></div>
                  <div className="tool-item"><span>🔍</span> <code>web_search</code></div>
                  <div className="tool-item"><span>🛍️</span> <code>product_knowledge</code></div>
                  <div className="tool-item"><span>📁</span> <code>workspace_file_ops</code></div>
                  <div className="tool-item"><span>🗄️</span> <code>sql_query</code></div>
                  <div className="tool-item"><span>🐍</span> <code>python_sandbox</code></div>
                  <div className="tool-item"><span>🕸️</span> <code>graph_memory</code></div>
                </div>
              </div>
            </div>

            <div className="glass-card">
              <div className="card-header flex items-center justify-between">
                <h3>📑 Live Artifacts</h3>
                <button 
                  className="text-xs text-indigo-400 hover:text-indigo-300 transition"
                  onClick={() => setActiveArtifact({
                    title: 'Interactive Sales Growth Plot',
                    type: 'plotly',
                    content: 'import plotly.graph_objects as go\nfig = go.Figure()\nfig.add_trace(go.Bar(x=["Q1", "Q2", "Q3", "Q4"], y=[120, 145, 190, 240]))',
                    plotlySpec: {
                      data: [{ x: ['Q1', 'Q2', 'Q3', 'Q4'], y: [120, 145, 190, 240], type: 'bar', name: 'Revenue ($k)' }],
                      layout: { title: 'Quarterly Revenue Performance 2026' }
                    }
                  })}
                >
                  Demo Spec
                </button>
              </div>
              <div className="card-body">
                <p className="text-xs text-slate-400">
                  Agent artifacts (interactive charts, HTML previews, and code files) appear here automatically.
                </p>
              </div>
            </div>

            <div className="glass-card">
              <div className="card-header">
                <h3>⚡ Turn Telemetry</h3>
              </div>
              <div className="card-body">
                <div className="stats-mini-row">
                  <span>Prompt Tokens:</span>
                  <strong className="font-mono">{telemetry.promptTokens}</strong>
                </div>
                <div className="stats-mini-row">
                  <span>Completion Tokens:</span>
                  <strong className="font-mono">{telemetry.completionTokens}</strong>
                </div>
                <div className="stats-mini-row">
                  <span>Tools Invoked:</span>
                  <strong className="font-mono">{telemetry.toolsCount}</strong>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
