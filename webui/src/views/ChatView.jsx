import React, { useState, useRef, useEffect } from 'react';
import { api } from '../api/client';
import { Send, Trash2, Copy, Check, Terminal, Sparkles, Wrench } from 'lucide-react';

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
  const [copied, setCopied] = useState(false);
  const [telemetry, setTelemetry] = useState({ promptTokens: 0, completionTokens: 0, toolsCount: 0 });
  const [sessionId, setSessionId] = useState(() => `conv_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`);
  const [turnCount, setTurnCount] = useState(0);

  const messagesEndRef = useRef(null);

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
  }, [messages, loading]);

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

  const handleSend = async (customPrompt) => {
    const text = (customPrompt || input).trim();
    if (!text || loading) return;

    if (!customPrompt) setInput('');

    // Handle /clear or /new commands
    if (text.toLowerCase() === '/clear' || text.toLowerCase() === '/new') {
      await handleClear(true);
      return;
    }

    const nextTurn = turnCount + 1;
    setTurnCount(nextTurn);
    const turnId = `turn_${nextTurn}_${Date.now()}`;

    const userMsg = { role: 'user', content: text, timestamp: new Date().toISOString(), turn_id: turnId };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

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
        request_ids: data.request_ids || [],
        timestamp: new Date().toISOString()
      };

      setMessages((prev) => [...prev, botMsg]);

      if (data.tokens) {
        setTelemetry({
          promptTokens: data.tokens.prompt_tokens || 0,
          completionTokens: data.tokens.completion_tokens || 0,
          toolsCount: (data.tool_calls || []).length
        });
      }

      onChatFinished?.();
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'error', content: err.message, timestamp: new Date().toISOString() }
      ]);
    } finally {
      setLoading(false);
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
            <button className="btn btn-secondary btn-sm" onClick={handleCopyJson} title="Copy full Conversation JSON">
              {copied ? <Check size={14} /> : <Copy size={14} />}
              <span>{copied ? 'Copied' : 'JSON'}</span>
            </button>
            <button className="btn btn-secondary btn-sm" onClick={() => handleClear(false)} title="Start new conversation (/clear)">
              <Trash2 size={14} />
              <span>New Conversation</span>
            </button>
          </div>
        </div>

        {/* Chat Messages */}
        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="chat-welcome">
              <div className="welcome-icon">👋</div>
              <h3>Welcome to your Everyday AI Agent!</h3>
              <p>
                Equipped with real-world MCP tools: <strong>Calculator</strong>, <strong>Live Weather</strong>, <strong>Web Search</strong>, <strong>Shopping Catalog</strong>, and <strong>Workspace Files</strong>.
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
              <div key={i} className={`chat-message message-${msg.role}`}>
                <div className="message-bubble">
                  {msg.tool_calls && msg.tool_calls.length > 0 && (
                    <div className="tool-call-feed">
                      {msg.tool_calls.map((tc, idx) => (
                        <div key={idx} className="tool-call-bubble">
                          <div className="tool-call-header">
                            <span>🛠️ Executed Tool: <strong>{tc.tool || tc.name}</strong></span>
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
            ))
          )}

          {loading && (
            <div className="chat-message message-bot">
              <div className="message-bubble">
                <span className="text-accent font-mono text-sm">⚡ Agent reasoning & executing tools...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="chat-input-bar">
          <textarea
            rows={2}
            placeholder="Ask me anything... (e.g. 'Plan a weekend trip to Tokyo with weather check' or 'Split a $184.50 dinner bill for 4 with 18% tip')"
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

      {/* Live Sidebar Panels */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div className="glass-card">
          <div className="card-header">
            <h3>🛠️ Active MCP Tools</h3>
          </div>
          <div className="card-body">
            <div className="tool-badge-list">
              <div className="tool-item"><span>🧮</span> <code>calculator</code></div>
              <div className="tool-item"><span>⛅</span> <code>weather</code></div>
              <div className="tool-item"><span>🔍</span> <code>web_search</code></div>
              <div className="tool-item"><span>🛍️</span> <code>product_knowledge</code></div>
              <div className="tool-item"><span>📁</span> <code>workspace_file_ops</code></div>
              <div className="tool-item"><span>💻</span> <code>system_tools</code></div>
            </div>
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
      </div>
    </div>
  );
}
