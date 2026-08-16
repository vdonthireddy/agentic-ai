// Global State
let currentTab = 'chat';
let activeSessionId = `chat_ui_${Date.now()}`;
let allLogs = [];
let gatewayStats = {};
let availableModels = [];
let chatHistory = [];

// Tab Switching
function switchTab(tabId) {
  currentTab = tabId;
  document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
  
  const targetPane = document.getElementById(`tab-${tabId}`);
  const targetNav = document.getElementById(`nav-${tabId}`);
  if (targetPane) targetPane.classList.add('active');
  if (targetNav) targetNav.classList.add('active');

  const titleMap = {
    chat: { title: 'AI Agent Chatbot', subtitle: 'Interactive ReAct Agent with Everyday Tools & Fun Domain Skills' },
    overview: { title: 'Observatory Overview', subtitle: 'Real-time LLM inference audit trails, token telemetry & agent interactions' },
    logs: { title: 'Interaction Audit Logs', subtitle: 'Searchable historical prompts, responses, tool calls, and caller contexts' },
    evals: { title: 'Evals & Benchmarks', subtitle: 'Evaluate tool accuracy, skill adherence, and execution correctness across models' }
  };

  const meta = titleMap[tabId] || { title: 'Unified Studio', subtitle: '' };
  document.getElementById('page-title').innerText = meta.title;
  document.getElementById('page-subtitle').innerText = meta.subtitle;

  if (tabId === 'evals') {
    fetchEvalReports();
  }
}

// ----------------------------------------------------------------------
// 1. Interactive Chatbot Logic
// ----------------------------------------------------------------------

function usePromptChip(text) {
  document.getElementById('chat-input-text').value = text;
  sendChatMessage();
}

function selectSkill(skillName) {
  document.getElementById('chat-skill-select').value = skillName;
  onSkillChange();
}

function onSkillChange() {
  const skill = document.getElementById('chat-skill-select').value;
  const welcome = document.querySelector('.chat-welcome');
  if (skill && welcome) {
    // Show active skill notice
  }
}

function handleChatKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendChatMessage();
  }
}

async function sendChatMessage() {
  const input = document.getElementById('chat-input-text');
  const message = input.value.trim();
  if (!message) return;

  const model = document.getElementById('chat-model-select').value;
  const skill = document.getElementById('chat-skill-select').value;
  const sendBtn = document.getElementById('chat-send-btn');
  const container = document.getElementById('chat-messages-container');

  // Remove welcome screen if present
  const welcome = container.querySelector('.chat-welcome');
  if (welcome) welcome.remove();

  // 1. Render User Message
  renderUserMessage(message);
  input.value = '';
  input.focus();

  // 2. Render Loading Bubble
  const loadingBubbleId = `loading_${Date.now()}`;
  renderBotLoading(loadingBubbleId);
  container.scrollTop = container.scrollHeight;

  sendBtn.disabled = true;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: message,
        model: model,
        skill_name: skill,
        session_id: activeSessionId
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.message || data.detail || 'Chat request failed');

    // Remove loading bubble
    const loadingElem = document.getElementById(loadingBubbleId);
    if (loadingElem) loadingElem.remove();

    // 3. Render Assistant Response with Tool Execution steps
    renderBotResponse(data);
    container.scrollTop = container.scrollHeight;

    // Refresh telemetry & logs
    setTimeout(fetchData, 400);

  } catch (err) {
    const loadingElem = document.getElementById(loadingBubbleId);
    if (loadingElem) loadingElem.remove();

    renderErrorMessage(err.message);
    container.scrollTop = container.scrollHeight;
  } finally {
    sendBtn.disabled = false;
  }
}

function renderUserMessage(text) {
  chatHistory.push({
    role: 'user',
    timestamp: new Date().toISOString(),
    content: text
  });

  const container = document.getElementById('chat-messages-container');
  const row = document.createElement('div');
  row.className = 'chat-bubble-row user-row';
  row.innerHTML = `
    <div class="chat-bubble user">${escapeHtml(text)}</div>
    <div class="avatar avatar-user">U</div>
  `;
  container.appendChild(row);
}

function renderBotLoading(id) {
  const container = document.getElementById('chat-messages-container');
  const row = document.createElement('div');
  row.className = 'chat-bubble-row';
  row.id = id;
  row.innerHTML = `
    <div class="avatar avatar-bot">🤖</div>
    <div class="chat-bubble bot" style="color:var(--text-muted);">
      <span class="refresh-dot" style="display:inline-block; margin-right:6px;"></span>
      Thinking, routing to Gateway & invoking tools...
    </div>
  `;
  container.appendChild(row);
}

function formatBotText(text) {
  if (!text) return 'No response generated.';
  let clean = escapeHtml(text);
  
  // Format code blocks
  clean = clean.replace(/```([\s\S]*?)```/g, '<pre class="bg-dark p-2 rounded my-2 font-mono text-xs overflow-x-auto">$1</pre>');
  // Format inline code
  clean = clean.replace(/`([^`]+)`/g, '<code class="font-mono text-xs bg-dark px-1 py-0.5 rounded">$1</code>');
  // Format bold
  clean = clean.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  // Convert newlines to breaks
  clean = clean.replace(/\n/g, '<br/>');
  return clean;
}

function renderBotResponse(data) {
  chatHistory.push({
    role: 'assistant',
    timestamp: new Date().toISOString(),
    content: data.response || '',
    tool_calls: data.tool_calls || [],
    active_skills: data.active_skills || [],
    tokens: data.tokens || {},
    session_id: data.session_id || activeSessionId,
    success: data.success !== false
  });

  const container = document.getElementById('chat-messages-container');
  const row = document.createElement('div');
  row.className = 'chat-bubble-row';

  let toolHtml = '';
  if (data.tool_calls && data.tool_calls.length > 0) {
    toolHtml = '<div style="margin-bottom:10px;">';
    for (const t of data.tool_calls) {
      toolHtml += `
        <div class="tool-execution-card">
          <div class="tool-execution-header">
            <span>⚙️ Invoked Tool: <strong>${t.tool}</strong></span>
          </div>
          <div style="color:var(--text-secondary); margin-top:2px;">Args: ${escapeHtml(JSON.stringify(t.arguments || {}))}</div>
        </div>
      `;
    }
    toolHtml += '</div>';
  }

  const tokens = data.tokens || {};
  const metaHtml = `
    <div class="chat-meta">
      <span>Tokens: ${tokens.total_tokens || 0} (P:${tokens.prompt_tokens || 0} / C:${tokens.completion_tokens || 0})</span>
      ${data.active_skills && data.active_skills.length > 0 ? `<span style="color:var(--accent-purple);">Skill: ${data.active_skills.join(', ')}</span>` : ''}
    </div>
  `;

  row.innerHTML = `
    <div class="avatar avatar-bot">🤖</div>
    <div class="chat-bubble bot">
      ${toolHtml}
      <div style="line-height:1.6;">${formatBotText(data.response)}</div>
      ${metaHtml}
    </div>
  `;
  container.appendChild(row);
}

function renderErrorMessage(msg) {
  chatHistory.push({
    role: 'error',
    timestamp: new Date().toISOString(),
    error: msg,
    success: false
  });

  const container = document.getElementById('chat-messages-container');
  const row = document.createElement('div');
  row.className = 'chat-bubble-row';
  row.innerHTML = `
    <div class="avatar avatar-bot">⚠️</div>
    <div class="chat-bubble bot" style="border-color:var(--accent-rose); color:var(--accent-rose);">
      <strong>Error:</strong> ${escapeHtml(msg)}
    </div>
  `;
  container.appendChild(row);
}

async function copyConversationJson() {
  const copyBtn = document.getElementById('copy-chat-btn');
  const originalText = copyBtn ? copyBtn.innerHTML : '📋 Copy Conversation';
  
  const exportData = {
    session_id: activeSessionId,
    exported_at: new Date().toISOString(),
    model: document.getElementById('chat-model-select') ? document.getElementById('chat-model-select').value : '',
    active_skill: document.getElementById('chat-skill-select') ? document.getElementById('chat-skill-select').value : '',
    total_messages: chatHistory.length,
    conversation: chatHistory
  };

  const jsonString = JSON.stringify(exportData, null, 2);

  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(jsonString);
    } else {
      const textarea = document.createElement('textarea');
      textarea.value = jsonString;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }

    if (copyBtn) {
      copyBtn.innerHTML = '✅ Copied JSON!';
      copyBtn.classList.remove('btn-secondary');
      copyBtn.classList.add('btn-primary');
      setTimeout(() => {
        copyBtn.innerHTML = originalText;
        copyBtn.classList.remove('btn-primary');
        copyBtn.classList.add('btn-secondary');
      }, 2000);
    }
  } catch (err) {
    console.error('Failed to copy conversation JSON:', err);
    alert('Could not copy conversation to clipboard: ' + err.message);
  }
}

async function clearChat() {
  chatHistory = [];
  activeSessionId = `chat_ui_${Date.now()}`;
  await fetch('/api/chat/clear', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: activeSessionId })
  });

  const container = document.getElementById('chat-messages-container');
  container.innerHTML = `
    <div class="chat-welcome">
      <div class="welcome-icon">👋</div>
      <h3>Conversation cleared!</h3>
      <p>Ask a question or pick an everyday prompt to start a fresh agent session.</p>
      <div class="prompt-chips">
        <button class="chip" onclick="usePromptChip('Our dinner bill for 4 people is $184.50. Calculate an 18% tip and the split per person using calculator.')">
          🍕 Split $184.50 dinner bill for 4
        </button>
        <button class="chip" onclick="usePromptChip('Check the live weather in Paris using weather and give me a 3-day vacation itinerary highlighting cozy bakeries.')">
          🥐 3-Day Paris trip with weather
        </button>
      </div>
    </div>
  `;
}

// ----------------------------------------------------------------------
// 2. Telemetry, Stats & Audit Logs
// ----------------------------------------------------------------------

async function fetchData() {
  try {
    // Stats
    const statsRes = await fetch('/v1/stats');
    if (statsRes.ok) {
      gatewayStats = await statsRes.json();
      renderStats();
    }

    // Logs
    const logsRes = await fetch('/v1/logs?limit=100');
    if (logsRes.ok) {
      const data = await logsRes.json();
      allLogs = data.logs || [];
      renderRecentLogs();
      renderAllLogs();
    }

    // Models
    const modelsRes = await fetch('/v1/models');
    if (modelsRes.ok) {
      const data = await modelsRes.json();
      availableModels = data.data || [];
      window.configuredDefaultModel = data.default_model || '';
      populateModelSelectors(data.default_model);
    }
  } catch (err) {
    console.error('Failed to fetch telemetry data:', err);
  }
}

function renderStats() {
  document.getElementById('stat-total-calls').innerText = (gatewayStats.total_calls || 0).toLocaleString();
  
  const successRate = gatewayStats.total_calls > 0
    ? Math.round((gatewayStats.successful_calls / gatewayStats.total_calls) * 100)
    : 100;
  document.getElementById('stat-success-rate').innerText = `${successRate}% Success (${gatewayStats.successful_calls || 0} pass, ${gatewayStats.error_calls || 0} err)`;

  const tokens = gatewayStats.token_usage || {};
  document.getElementById('stat-total-tokens').innerText = (tokens.total_tokens || 0).toLocaleString();
  document.getElementById('stat-token-breakdown').innerText = `${(tokens.prompt_tokens || 0).toLocaleString()} Prompt / ${(tokens.completion_tokens || 0).toLocaleString()} Comp`;

  document.getElementById('stat-avg-latency').innerText = `${Math.round(gatewayStats.average_latency_ms || 0)} ms`;

  // Render Models Chart
  renderModelsChart();
  // Render Tools Chart
  renderToolsChart();
}

function renderModelsChart() {
  const container = document.getElementById('models-distribution-container');
  const models = gatewayStats.models_usage || {};
  const total = Object.values(models).reduce((a, b) => a + b, 0);

  if (total === 0) {
    container.innerHTML = '<div class="text-center text-muted py-4">No model invocations logged yet.</div>';
    return;
  }

  let html = '';
  for (const [model, count] of Object.entries(models)) {
    const pct = Math.round((count / total) * 100);
    html += `
      <div class="bar-item">
        <div class="bar-header">
          <strong>${model}</strong>
          <span>${count.toLocaleString()} calls (${pct}%)</span>
        </div>
        <div class="bar-track">
          <div class="bar-fill bar-fill-cyan" style="width: ${pct}%;"></div>
        </div>
      </div>
    `;
  }
  container.innerHTML = html;
}

function renderToolsChart() {
  const container = document.getElementById('tools-distribution-container');
  const tools = gatewayStats.tools_usage_frequency || {};
  const skills = gatewayStats.skills_usage_frequency || {};
  
  const hasTools = Object.keys(tools).length > 0;
  const hasSkills = Object.keys(skills).length > 0;

  if (!hasTools && !hasSkills) {
    container.innerHTML = '<div class="text-center text-muted py-4">No tools or skills invoked yet.</div>';
    return;
  }

  let html = '<div class="mb-4">';
  if (hasSkills) {
    html += '<h4 style="font-size:0.8rem; color:var(--accent-purple); text-transform:uppercase; margin-bottom:8px;">Active Domain Skills</h4>';
    const skillMax = Math.max(...Object.values(skills), 1);
    for (const [skill, count] of Object.entries(skills)) {
      const pct = Math.round((count / skillMax) * 100);
      html += `
        <div class="bar-item">
          <div class="bar-header">
            <strong>${skill}</strong>
            <span>${count} times</span>
          </div>
          <div class="bar-track">
            <div class="bar-fill bar-fill-purple" style="width: ${pct}%;"></div>
          </div>
        </div>
      `;
    }
  }

  if (hasTools) {
    html += '<h4 style="font-size:0.8rem; color:var(--accent-emerald); text-transform:uppercase; margin:16px 0 8px 0;">Everyday MCP Tools</h4>';
    const toolMax = Math.max(...Object.values(tools), 1);
    for (const [tool, count] of Object.entries(tools)) {
      const pct = Math.round((count / toolMax) * 100);
      html += `
        <div class="bar-item">
          <div class="bar-header">
            <strong>${tool}</strong>
            <span>${count} times</span>
          </div>
          <div class="bar-track">
            <div class="bar-fill bar-fill-emerald" style="width: ${pct}%;"></div>
          </div>
        </div>
      `;
    }
  }
  html += '</div>';
  container.innerHTML = html;
}

function renderRecentLogs() {
  const tbody = document.getElementById('recent-logs-tbody');
  const previewLogs = allLogs.slice(0, 7);

  if (previewLogs.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" class="text-center py-6">No audit records found.</td></tr>';
    return;
  }

  let html = '';
  for (const log of previewLogs) {
    const statusBadge = log.status === 'SUCCESS'
      ? '<span class="badge badge-emerald">SUCCESS</span>'
      : '<span class="badge badge-rose">ERROR</span>';

    const toolsDisplay = (log.tool_names && log.tool_names.length > 0)
      ? `<span class="badge badge-cyan">${log.tool_names.join(', ')}</span>`
      : '<span class="badge badge-dim">-</span>';

    const skillsDisplay = (log.skill_names && log.skill_names.length > 0)
      ? `<span class="badge badge-purple">${log.skill_names.join(', ')}</span>`
      : '';

    html += `
      <tr>
        <td><strong class="font-mono" style="color:var(--accent-cyan);">${log.id}</strong></td>
        <td style="color:var(--text-muted); font-size:0.8rem;">${formatTime(log.timestamp)}</td>
        <td>
          <div style="font-weight:600; color:#fff;">${escapeHtml(log.agent_name || 'Agent')}</div>
          <div style="font-size:0.75rem; color:var(--text-muted);">${escapeHtml(log.caller_id || '-')}</div>
        </td>
        <td><span class="badge badge-dim">${escapeHtml(log.model)}</span></td>
        <td>${skillsDisplay} ${toolsDisplay}</td>
        <td class="font-mono">${log.total_tokens.toLocaleString()}</td>
        <td class="font-mono">${Math.round(log.latency_ms)}ms</td>
        <td>${statusBadge}</td>
        <td>
          <button class="btn btn-secondary" style="padding:4px 10px; font-size:0.78rem;" onclick="openDetailModal('${log.id}')">Inspect</button>
        </td>
      </tr>
    `;
  }
  tbody.innerHTML = html;
}

function renderAllLogs() {
  filterLogs();
}

function filterLogs() {
  const search = document.getElementById('log-search-input').value.toLowerCase().trim();
  const modelFilter = document.getElementById('log-model-filter').value;
  const statusFilter = document.getElementById('log-status-filter').value;

  const filtered = allLogs.filter(log => {
    if (modelFilter && log.model !== modelFilter) return false;
    if (statusFilter && log.status !== statusFilter) return false;
    if (search) {
      const matchId = (log.id || '').toLowerCase().includes(search);
      const matchSession = (log.session_id || '').toLowerCase().includes(search);
      const matchAgent = (log.agent_name || '').toLowerCase().includes(search);
      const matchCaller = (log.caller_id || '').toLowerCase().includes(search);
      const matchModel = (log.model || '').toLowerCase().includes(search);
      if (!matchId && !matchSession && !matchAgent && !matchCaller && !matchModel) return false;
    }
    return true;
  });

  document.getElementById('filtered-logs-count').innerText = `Showing ${filtered.length} of ${allLogs.length} calls`;

  const tbody = document.getElementById('all-logs-tbody');
  if (filtered.length === 0) {
    tbody.innerHTML = '<tr><td colspan="11" class="text-center py-8">No matching audit logs found.</td></tr>';
    return;
  }

  let html = '';
  for (const log of filtered) {
    const statusBadge = log.status === 'SUCCESS'
      ? '<span class="badge badge-emerald">SUCCESS</span>'
      : '<span class="badge badge-rose">ERROR</span>';

    const toolsDisplay = (log.tool_names && log.tool_names.length > 0)
      ? log.tool_names.map(t => `<span class="badge badge-cyan">${t}</span>`).join(' ')
      : '<span class="badge badge-dim">-</span>';

    const skillsDisplay = (log.skill_names && log.skill_names.length > 0)
      ? log.skill_names.map(s => `<span class="badge badge-purple">${s}</span>`).join(' ')
      : '<span class="badge badge-dim">-</span>';

    html += `
      <tr>
        <td><strong class="font-mono" style="color:var(--accent-cyan);">${log.id}</strong></td>
        <td style="color:var(--text-muted); font-size:0.8rem;">${formatTime(log.timestamp)}</td>
        <td>${escapeHtml(log.caller_id || '-')}</td>
        <td><strong>${escapeHtml(log.agent_name || 'Agent')}</strong></td>
        <td><span class="badge badge-dim">${escapeHtml(log.model)}</span></td>
        <td>${skillsDisplay}</td>
        <td>${toolsDisplay}</td>
        <td class="font-mono">${log.prompt_tokens}/${log.completion_tokens}/${log.total_tokens}</td>
        <td class="font-mono">${Math.round(log.latency_ms)}ms</td>
        <td>${statusBadge}</td>
        <td>
          <button class="btn btn-secondary" style="padding:4px 10px; font-size:0.78rem;" onclick="openDetailModal('${log.id}')">View</button>
        </td>
      </tr>
    `;
  }
  tbody.innerHTML = html;
}

function populateModelSelectors(defaultModel) {
  const selects = [
    document.getElementById('chat-model-select'),
    document.getElementById('log-model-filter'),
    document.getElementById('eval-model-select')
  ];

  if (availableModels.length === 0) return;

  const def = defaultModel || window.configuredDefaultModel || (availableModels[0] ? availableModels[0].id : '');

  for (const sel of selects) {
    if (!sel) continue;
    const cur = sel.dataset.userSelected ? sel.value : null;
    let opts = sel.id === 'log-model-filter' ? '<option value="">All Models</option>' : '';
    for (const m of availableModels) {
      const isDef = m.id === def;
      opts += `<option value="${m.id}" ${isDef ? 'selected' : ''}>${m.id}${isDef ? ' (Default)' : ''}</option>`;
    }
    sel.innerHTML = opts;
    if (cur) {
      sel.value = cur;
    } else if (sel.id !== 'log-model-filter' && def) {
      sel.value = def;
    }

    if (!sel.dataset.listenerAttached) {
      sel.addEventListener('change', () => { sel.dataset.userSelected = 'true'; });
      sel.dataset.listenerAttached = 'true';
    }
  }

  const activeModelDisplay = document.getElementById('active-model-display');
  if (activeModelDisplay) {
    activeModelDisplay.innerText = def;
  }
}

// Modal Inspector
function openDetailModal(callId) {
  const log = allLogs.find(l => l.id === callId);
  if (!log) return;

  document.getElementById('modal-badge-id').innerText = log.id;
  document.getElementById('modal-title').innerText = `Interaction: ${log.agent_name} (${log.model})`;

  const modalBody = document.getElementById('modal-body-content');
  
  let messagesHtml = '';
  const msgs = Array.isArray(log.request_messages) ? log.request_messages : [];
  for (const m of msgs) {
    const roleClass = `role-${m.role}`;
    let content = m.content || '';
    if (m.tool_calls) {
      content += '\n[Tool Call Requested]: ' + JSON.stringify(m.tool_calls, null, 2);
    }
    messagesHtml += `
      <div class="message-bubble ${roleClass}">
        <div class="bubble-header">${m.role.toUpperCase()}</div>
        <div class="bubble-content">${escapeHtml(content)}</div>
      </div>
    `;
  }

  // Response bubble
  if (log.response_content || (log.response_tool_calls && log.response_tool_calls.length > 0)) {
    let respText = log.response_content || '';
    if (log.response_tool_calls && log.response_tool_calls.length > 0) {
      respText += '\n[Generated Tool Calls]:\n' + JSON.stringify(log.response_tool_calls, null, 2);
    }
    messagesHtml += `
      <div class="message-bubble role-assistant">
        <div class="bubble-header">ASSISTANT (OUTPUT)</div>
        <div class="bubble-content">${escapeHtml(respText)}</div>
      </div>
    `;
  }

  modalBody.innerHTML = `
    <!-- Top Telemetry Row -->
    <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:12px; margin-bottom:20px;">
      <div style="background:rgba(255,255,255,0.03); padding:12px; border-radius:8px; border:1px solid var(--border-color);">
        <div style="font-size:0.75rem; color:var(--text-muted);">LATENCY</div>
        <div style="font-size:1.1rem; font-weight:700; color:#fff;">${log.latency_ms} ms</div>
      </div>
      <div style="background:rgba(255,255,255,0.03); padding:12px; border-radius:8px; border:1px solid var(--border-color);">
        <div style="font-size:0.75rem; color:var(--text-muted);">PROMPT TOKENS</div>
        <div style="font-size:1.1rem; font-weight:700; color:var(--accent-cyan);">${log.prompt_tokens}</div>
      </div>
      <div style="background:rgba(255,255,255,0.03); padding:12px; border-radius:8px; border:1px solid var(--border-color);">
        <div style="font-size:0.75rem; color:var(--text-muted);">COMPLETION TOKENS</div>
        <div style="font-size:1.1rem; font-weight:700; color:var(--accent-purple);">${log.completion_tokens}</div>
      </div>
      <div style="background:rgba(255,255,255,0.03); padding:12px; border-radius:8px; border:1px solid var(--border-color);">
        <div style="font-size:0.75rem; color:var(--text-muted);">TOTAL TOKENS</div>
        <div style="font-size:1.1rem; font-weight:700; color:#fff;">${log.total_tokens}</div>
      </div>
    </div>

    <!-- Caller Context Info -->
    <div class="modal-section">
      <h4>Caller Identity & Session Context</h4>
      <div style="background:#04060A; border:1px solid var(--border-color); border-radius:8px; padding:12px; font-family:var(--font-mono); font-size:0.82rem;">
        <div><strong>Session ID:</strong> ${escapeHtml(log.session_id || '-')}</div>
        <div><strong>Caller ID:</strong> ${escapeHtml(log.caller_id || '-')}</div>
        <div><strong>Agent Name:</strong> ${escapeHtml(log.agent_name || '-')}</div>
        <div><strong>Context Data:</strong> ${JSON.stringify(log.caller_context || {}, null, 2)}</div>
      </div>
    </div>

    <!-- Conversation Messages -->
    <div class="modal-section">
      <h4>Full Conversation & Tool Interaction Flow</h4>
      ${messagesHtml}
    </div>
  `;

  document.getElementById('detail-modal').classList.add('active');
}

function closeModal(event) {
  if (event && event.target !== document.getElementById('detail-modal') && !event.target.classList.contains('btn-close')) {
    return;
  }
  document.getElementById('detail-modal').classList.remove('active');
}

// ----------------------------------------------------------------------
// 3. Generic Evals Framework & Comparative Dashboard
// ----------------------------------------------------------------------

let selectedRunIds = new Set();
let registeredAgentsList = [];
let registeredModelsList = [];
let registeredJudgesList = [];

function switchEvalsHubTab(tabKey) {
  const tabs = ['runner', 'models', 'agents', 'history'];
  for (const t of tabs) {
    const btn = document.getElementById(`hub-nav-${t}`);
    const pane = document.getElementById(`evals-pane-${t}`);
    if (btn) btn.classList.toggle('active', t === tabKey);
    if (pane) pane.classList.toggle('active', t === tabKey);
  }
  if (tabKey === 'models' || tabKey === 'agents') {
    fetchEvalRegistries();
  } else if (tabKey === 'history') {
    fetchEvalRuns();
    fetchEvalReports();
  }
}

async function fetchEvalRegistries() {
  try {
    // 1. Agents Registry
    const agentsRes = await fetch('/api/evals/agents');
    if (agentsRes.ok) {
      const data = await agentsRes.json();
      registeredAgentsList = data.agents || [];
      
      // Update dropdown selector
      const sel = document.getElementById('eval-agent-select');
      if (sel) {
        sel.innerHTML = registeredAgentsList.map(a => 
          `<option value="${a.id}">${escapeHtml(a.name)} (${a.type})</option>`
        ).join('');
      }

      // Update Agents Registry Table
      renderAgentsRegistryTable();
    }

    // 2. Models Registry
    const modelsRes = await fetch('/api/evals/models');
    if (modelsRes.ok) {
      const data = await modelsRes.json();
      registeredModelsList = data.models || [];

      // Update dropdown selector
      const sel = document.getElementById('eval-model-select');
      if (sel) {
        sel.innerHTML = registeredModelsList.map(m => 
          `<option value="${m.model_id}">${escapeHtml(m.name)} [${m.model_id}]</option>`
        ).join('');
      }

      // Update Models Registry Table
      renderModelsRegistryTable();
    }

    // 3. Judges Registry
    const judgesRes = await fetch('/api/evals/judges');
    if (judgesRes.ok) {
      const data = await judgesRes.json();
      registeredJudgesList = data.judges || [];

      // Update dropdown selector
      const sel = document.getElementById('eval-judge-select');
      if (sel) {
        sel.innerHTML = registeredJudgesList.map(j => 
          `<option value="${j.model}">${escapeHtml(j.name)} (${j.model})</option>`
        ).join('');
      }

      // Update Judges Registry Table
      renderJudgesRegistryTable();
    }
  } catch (err) {
    console.error('Failed to load eval registries:', err);
  }
}

function renderAgentsRegistryTable() {
  const tbody = document.getElementById('agents-registry-tbody');
  if (!tbody) return;

  if (registeredAgentsList.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="text-center py-6 text-muted">No agents registered.</td></tr>';
    return;
  }

  tbody.innerHTML = registeredAgentsList.map(a => `
    <tr>
      <td><strong class="font-mono" style="color:var(--accent-cyan); font-size:0.85rem;">${escapeHtml(a.id)}</strong></td>
      <td><strong>${escapeHtml(a.name)}</strong></td>
      <td><span class="badge ${a.type === 'MCPAgentAdapter' ? 'badge-purple' : 'badge-emerald'}">${escapeHtml(a.type || 'Agent')}</span></td>
      <td style="color:var(--text-secondary); font-size:0.82rem;">${escapeHtml(a.endpoint_url || a.description || '-')}</td>
      <td>
        ${a.id !== 'mcp_default' ? `<button class="btn btn-secondary" style="padding:2px 8px; font-size:0.75rem; color:var(--accent-rose);" onclick="deleteEvalAgent('${a.id}')">Delete</button>` : '<span class="badge badge-dim">System</span>'}
      </td>
    </tr>
  `).join('');
}

function renderModelsRegistryTable() {
  const tbody = document.getElementById('models-registry-tbody');
  if (!tbody) return;

  if (registeredModelsList.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" class="text-center py-6 text-muted">No candidate models registered.</td></tr>';
    return;
  }

  tbody.innerHTML = registeredModelsList.map(m => `
    <tr>
      <td><strong class="font-mono" style="color:var(--accent-cyan); font-size:0.85rem;">${escapeHtml(m.model_id)}</strong></td>
      <td><strong>${escapeHtml(m.name)}</strong></td>
      <td><span class="badge badge-dim">${escapeHtml(m.provider || 'ollama')}</span></td>
      <td>
        ${!m.is_default ? `<button class="btn btn-secondary" style="padding:2px 8px; font-size:0.75rem; color:var(--accent-rose);" onclick="deleteEvalModel('${m.model_id}')">Delete</button>` : '<span class="badge badge-dim">Default</span>'}
      </td>
    </tr>
  `).join('');
}

function renderJudgesRegistryTable() {
  const tbody = document.getElementById('judges-registry-tbody');
  if (!tbody) return;

  if (registeredJudgesList.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" class="text-center py-6 text-muted">No judges registered.</td></tr>';
    return;
  }

  tbody.innerHTML = registeredJudgesList.map(j => `
    <tr>
      <td><strong class="font-mono" style="color:var(--accent-cyan); font-size:0.85rem;">${escapeHtml(j.judge_id)}</strong></td>
      <td><strong>${escapeHtml(j.name)}</strong></td>
      <td><span class="badge badge-purple font-mono">${escapeHtml(j.model)}</span></td>
      <td>
        ${!j.is_default ? `<button class="btn btn-secondary" style="padding:2px 8px; font-size:0.75rem; color:var(--accent-rose);" onclick="deleteEvalJudge('${j.judge_id}')">Delete</button>` : '<span class="badge badge-dim">Default</span>'}
      </td>
    </tr>
  `).join('');
}

// Inline Registry Form Submissions
function toggleInlineAgentType() {
  const type = document.getElementById('inline-agent-type').value;
  const urlGrp = document.getElementById('inline-agent-url-group');
  const modelGrp = document.getElementById('inline-agent-model-group');
  if (urlGrp) urlGrp.style.display = type === 'http' ? 'block' : 'none';
  if (modelGrp) modelGrp.style.display = type === 'mcp' ? 'block' : 'none';
}

async function submitInlineRegisterAgent() {
  const type = document.getElementById('inline-agent-type').value;
  const payload = {
    adapter_id: document.getElementById('inline-agent-id').value.trim(),
    name: document.getElementById('inline-agent-name').value.trim(),
    type: type,
    model: document.getElementById('inline-agent-model') ? document.getElementById('inline-agent-model').value.trim() : null,
    endpoint_url: document.getElementById('inline-agent-url') ? document.getElementById('inline-agent-url').value.trim() : null,
    description: document.getElementById('inline-agent-desc').value.trim()
  };
  if (!payload.adapter_id || !payload.name) {
    alert('Please provide Adapter ID and Name.');
    return;
  }
  if (type === 'http' && !payload.endpoint_url) {
    alert('Please provide a valid Endpoint URL for external HTTP agents.');
    return;
  }
  try {
    const res = await fetch('/api/evals/agents', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Agent registration failed');
    document.getElementById('inline-agent-id').value = '';
    document.getElementById('inline-agent-name').value = '';
    if (document.getElementById('inline-agent-url')) document.getElementById('inline-agent-url').value = '';
    document.getElementById('inline-agent-desc').value = '';
    fetchEvalRegistries();
    alert(`Agent '${payload.name}' successfully registered!`);
  } catch (err) { alert(err.message); }
}

async function submitInlineRegisterModel() {
  const payload = {
    model_id: document.getElementById('inline-model-id').value.trim(),
    name: document.getElementById('inline-model-name').value.trim(),
    provider: document.getElementById('inline-model-provider').value.trim(),
    api_base: document.getElementById('inline-model-base').value.trim()
  };
  if (!payload.model_id || !payload.name) {
    alert('Please provide Model ID and Name.');
    return;
  }
  try {
    const res = await fetch('/api/evals/models', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Model registration failed');
    document.getElementById('inline-model-id').value = '';
    document.getElementById('inline-model-name').value = '';
    document.getElementById('inline-model-base').value = '';
    fetchEvalRegistries();
    alert(`Model '${payload.name}' successfully registered!`);
  } catch (err) { alert(err.message); }
}

async function submitInlineRegisterJudge() {
  const payload = {
    judge_id: document.getElementById('inline-judge-id').value.trim(),
    name: document.getElementById('inline-judge-name').value.trim(),
    model: document.getElementById('inline-judge-model').value.trim(),
    rubric_description: document.getElementById('inline-judge-rubric').value.trim()
  };
  if (!payload.judge_id || !payload.name || !payload.model) {
    alert('Please fill out Judge ID, Name, and Model.');
    return;
  }
  try {
    const res = await fetch('/api/evals/judges', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Judge registration failed');
    document.getElementById('inline-judge-id').value = '';
    document.getElementById('inline-judge-name').value = '';
    document.getElementById('inline-judge-rubric').value = '';
    fetchEvalRegistries();
    alert(`Judge '${payload.name}' successfully registered!`);
  } catch (err) { alert(err.message); }
}

async function deleteEvalModel(modelId) {
  if (!confirm(`Remove model '${modelId}' from registry?`)) return;
  try {
    const res = await fetch(`/api/evals/models/${encodeURIComponent(modelId)}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete model');
    fetchEvalRegistries();
  } catch (err) { alert(err.message); }
}

async function deleteEvalJudge(judgeId) {
  if (!confirm(`Remove judge '${judgeId}' from registry?`)) return;
  try {
    const res = await fetch(`/api/evals/judges/${encodeURIComponent(judgeId)}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete judge');
    fetchEvalRegistries();
  } catch (err) { alert(err.message); }
}

async function deleteEvalAgent(agentId) {
  if (!confirm(`Remove agent adapter '${agentId}' from registry?`)) return;
  try {
    const res = await fetch(`/api/evals/agents/${encodeURIComponent(agentId)}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete agent adapter');
    fetchEvalRegistries();
  } catch (err) { alert(err.message); }
}

async function startEvals() {
  const agentId = document.getElementById('eval-agent-select').value;
  const model = document.getElementById('eval-model-select').value;
  const judgeModel = document.getElementById('eval-judge-select').value;

  const categories = [];
  if (document.getElementById('chk-tool-calling').checked) categories.push('tool_calling');
  if (document.getElementById('chk-skill-adherence').checked) categories.push('skill_adherence');
  if (document.getElementById('chk-reasoning').checked) categories.push('reasoning');

  const btn = document.getElementById('eval-run-btn');
  const badge = document.getElementById('eval-status-badge');
  const placeholder = document.getElementById('eval-placeholder');
  const content = document.getElementById('eval-scorecard-content');

  btn.disabled = true;
  btn.innerHTML = '<span>⏳ Running 4-Grader Benchmarks...</span>';
  badge.innerText = 'Evaluating...';
  badge.className = 'badge badge-amber';

  switchEvalSubtab('scorecard');
  if (placeholder) placeholder.style.display = 'none';
  if (content) {
    content.style.display = 'block';
    content.innerHTML = `
      <div class="text-center py-8">
        <div style="font-size:36px; margin-bottom:12px;">🧪</div>
        <h3>Benchmarking Model: ${escapeHtml(model)}</h3>
        <p class="text-muted">Running 4-grader evaluation (Deterministic, Efficiency, LLM Judge, Fact-Checker)...</p>
      </div>
    `;
  }

  try {
    const res = await fetch('/api/evals/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        agent_id: agentId,
        model: model,
        judge_model: judgeModel,
        categories: categories
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.message || data.detail || 'Evaluation failed');

    badge.innerText = `Score: ${data.average_score_pct}%`;
    badge.className = data.pass_rate_pct >= 70 ? 'badge badge-emerald' : 'badge badge-rose';

    renderEvalScorecard(data);
    fetchEvalRuns();
    fetchEvalReports();

  } catch (err) {
    badge.innerText = 'Evaluation Failed';
    badge.className = 'badge badge-rose';
    if (content) content.innerHTML = `<div class="text-rose py-4">[Error]: ${escapeHtml(err.message)}</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>🚀 Execute Benchmark Suite</span>';
  }
}

function renderEvalScorecard(data) {
  const content = document.getElementById('eval-scorecard-content');
  if (!content) return;

  const perf = data.performance_metrics || {};
  const grad = data.grader_averages || {};

  let html = `
    <!-- Top KPI Score Boxes -->
    <div class="scorecard-summary">
      <div class="score-box">
        <span>Pass Rate</span>
        <h4 style="color:var(--accent-cyan);">${data.passed_tests}/${data.total_tests} (${data.pass_rate_pct}%)</h4>
      </div>
      <div class="score-box">
        <span>Composite Score</span>
        <h4 style="color:var(--accent-emerald);">${data.average_score_pct}%</h4>
      </div>
      <div class="score-box">
        <span>Total Tokens</span>
        <h4 style="color:var(--accent-purple);">${(perf.total_tokens || data.total_tokens || 0).toLocaleString()}</h4>
      </div>
      <div class="score-box">
        <span>Avg Latency</span>
        <h4 style="color:#fff;">${Math.round(perf.avg_latency_ms || data.avg_latency_ms || 0)} ms</h4>
      </div>
    </div>

    <!-- 4-Grader Average Gauges -->
    <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:10px; padding:12px 16px; margin-bottom:20px;">
      <h5 style="margin:0 0 10px 0; font-size:0.85rem; color:var(--text-muted); text-transform:uppercase;">🧑‍⚖️ 4-Grader Dimensional Averages</h5>
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:12px;">
        <div style="background:rgba(0,0,0,0.3); padding:10px; border-radius:8px; text-align:center;">
          <div style="font-size:0.75rem; color:var(--text-muted);">📏 Rulebook / Det</div>
          <div style="font-size:1.2rem; font-weight:700; color:var(--accent-cyan);">${grad.deterministic || 0}%</div>
        </div>
        <div style="background:rgba(0,0,0,0.3); padding:10px; border-radius:8px; text-align:center;">
          <div style="font-size:0.75rem; color:var(--text-muted);">⚡ Efficiency / Loops</div>
          <div style="font-size:1.2rem; font-weight:700; color:var(--accent-emerald);">${grad.efficiency || 0}%</div>
        </div>
        <div style="background:rgba(0,0,0,0.3); padding:10px; border-radius:8px; text-align:center;">
          <div style="font-size:0.75rem; color:var(--text-muted);">⚖️ LLM Judge Safety</div>
          <div style="font-size:1.2rem; font-weight:700; color:var(--accent-purple);">${grad.llm_judge || 0}%</div>
        </div>
        <div style="background:rgba(0,0,0,0.3); padding:10px; border-radius:8px; text-align:center;">
          <div style="font-size:0.75rem; color:var(--text-muted);">🔍 Truth / Fact-Check</div>
          <div style="font-size:1.2rem; font-weight:700; color:var(--accent-amber);">${grad.fact_checker || 0}%</div>
        </div>
      </div>
    </div>

    <!-- Test Case Breakdown Table -->
    <h4 style="margin:20px 0 10px 0; font-size:0.95rem;">Test Case Breakdown (${(data.results || []).length} items)</h4>
    <div class="table-responsive">
      <table class="data-table">
        <thead>
          <tr>
            <th>Status</th>
            <th>Test Name</th>
            <th>Category</th>
            <th>Det</th>
            <th>Eff</th>
            <th>Judge</th>
            <th>Fact</th>
            <th>Overall</th>
          </tr>
        </thead>
        <tbody>
  `;

  for (const t of data.results || []) {
    const statusIcon = t.passed
      ? '<span class="badge badge-emerald">PASS</span>'
      : '<span class="badge badge-rose">FAIL</span>';

    html += `
      <tr>
        <td>${statusIcon}</td>
        <td><strong>${escapeHtml(t.name)}</strong></td>
        <td><span class="badge badge-dim">${escapeHtml(t.category)}</span></td>
        <td class="font-mono">${Math.round((t.deterministic_score || 0) * 100)}%</td>
        <td class="font-mono">${Math.round((t.efficiency_score || 0) * 100)}%</td>
        <td class="font-mono">${Math.round((t.judge_score || 0) * 100)}%</td>
        <td class="font-mono">${Math.round((t.fact_check_score || 0) * 100)}%</td>
        <td class="font-mono"><strong>${Math.round((t.overall_score || 0) * 100)}%</strong></td>
      </tr>
    `;
  }

  html += `
        </tbody>
      </table>
    </div>
  `;

  content.innerHTML = html;
}

// ----------------------------------------------------------------------
// Historical Runs & Comparative Matrix Logic
// ----------------------------------------------------------------------

async function fetchEvalRuns() {
  const tbody = document.getElementById('eval-history-tbody');
  try {
    const res = await fetch('/api/evals/runs');
    if (!res.ok) return;
    const data = await res.json();
    const runs = data.runs || [];

    if (runs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="11" class="text-center py-6 text-muted">No historical benchmark runs found yet. Run a suite above to record history.</td></tr>';
      return;
    }

    let html = '';
    for (const r of runs) {
      const isChecked = selectedRunIds.has(r.run_id);
      const passColor = r.pass_rate_pct >= 70 ? 'var(--accent-emerald)' : 'var(--accent-rose)';

      html += `
        <tr>
          <td>
            <input type="checkbox" value="${r.run_id}" ${isChecked ? 'checked' : ''} onchange="toggleRunSelection('${r.run_id}', this.checked)">
          </td>
          <td><strong class="font-mono" style="color:var(--accent-cyan); font-size:0.8rem;">${escapeHtml(r.run_id)}</strong></td>
          <td style="color:var(--text-muted); font-size:0.8rem;">${formatTime(r.timestamp)}</td>
          <td><span class="badge badge-dim">${escapeHtml(r.agent_name || 'Agent')}</span></td>
          <td><strong>${escapeHtml(r.model)}</strong></td>
          <td><span class="badge badge-purple">${escapeHtml(r.judge_model || '-')}</span></td>
          <td class="font-mono" style="color:${passColor}; font-weight:600;">${r.pass_rate_pct}%</td>
          <td class="font-mono"><strong>${r.average_score_pct}%</strong></td>
          <td class="font-mono">${Math.round(r.avg_latency_ms || 0)}ms</td>
          <td class="font-mono">${(r.total_tokens || 0).toLocaleString()}</td>
          <td>
            <button class="btn btn-secondary" style="padding:3px 8px; font-size:0.75rem;" onclick="loadSingleRunDetail('${r.run_id}')">View</button>
          </td>
        </tr>
      `;
    }
    tbody.innerHTML = html;
    updateCompareButtonState();
  } catch (err) {
    console.error('Failed to load eval runs:', err);
  }
}

function toggleRunSelection(runId, isChecked) {
  if (isChecked) {
    selectedRunIds.add(runId);
  } else {
    selectedRunIds.delete(runId);
  }
  updateCompareButtonState();
}

function toggleSelectAllRuns(masterCheckbox) {
  const checkboxes = document.querySelectorAll('#eval-history-tbody input[type="checkbox"]');
  for (const cb of checkboxes) {
    cb.checked = masterCheckbox.checked;
    if (masterCheckbox.checked) {
      selectedRunIds.add(cb.value);
    } else {
      selectedRunIds.delete(cb.value);
    }
  }
  updateCompareButtonState();
}

function updateCompareButtonState() {
  const btn = document.getElementById('compare-runs-btn');
  if (!btn) return;
  const count = selectedRunIds.size;
  btn.disabled = count < 2;
  btn.innerHTML = `<span>⚖️ Compare Selected (${count})</span>`;
  if (count >= 2) {
    btn.classList.remove('btn-secondary');
    btn.classList.add('btn-primary');
  } else {
    btn.classList.remove('btn-primary');
    btn.classList.add('btn-secondary');
  }
}

async function loadSingleRunDetail(runId) {
  try {
    const res = await fetch(`/api/evals/runs/${runId}`);
    if (!res.ok) throw new Error('Could not fetch run details');
    const data = await res.json();
    switchEvalSubtab('scorecard');
    renderEvalScorecard(data);
  } catch (err) {
    alert(err.message);
  }
}

async function compareSelectedRuns() {
  if (selectedRunIds.size < 2) {
    alert('Please select at least 2 benchmark runs to generate a comparative analysis.');
    return;
  }

  const runIdsArray = Array.from(selectedRunIds);
  const modal = document.getElementById('compare-modal');
  const modalBody = document.getElementById('compare-modal-body');

  modal.classList.add('active');
  modalBody.innerHTML = '<div class="text-center py-8"><h3>Computing comparative scorecard across selected runs...</h3></div>';

  try {
    const res = await fetch(`/api/evals/compare?runs=${encodeURIComponent(runIdsArray.join(','))}`);
    if (!res.ok) throw new Error('Failed to compute comparison matrix');
    const data = await res.json();

    const runs = data.runs || [];
    const matrix = data.matrix || [];

    // Identify winning run (highest average score)
    let bestScore = -1;
    let winnerId = '';
    for (const r of runs) {
      if (r.average_score_pct > bestScore) {
        bestScore = r.average_score_pct;
        winnerId = r.run_id;
      }
    }

    let cardsHtml = '<div class="comparison-grid">';
    for (const r of runs) {
      const isWinner = r.run_id === winnerId;
      const grad = r.graders || {};

      cardsHtml += `
        <div class="compare-card ${isWinner ? 'winner' : ''}">
          <div class="flex-between mb-2">
            <h4 style="margin:0; font-size:1rem; color:#fff;">${escapeHtml(r.model)}</h4>
            ${isWinner ? '<span class="badge badge-emerald">🏆 Top Performer</span>' : '<span class="badge badge-dim">Run</span>'}
          </div>
          <div style="font-size:0.78rem; color:var(--text-muted); margin-bottom:10px;">
            Agent: <strong>${escapeHtml(r.agent_name)}</strong> | Judge: ${escapeHtml(r.judge_model || '-')}
          </div>
          
          <div class="compare-stat-row">
            <span class="compare-stat-label">Composite Score</span>
            <span class="compare-stat-val" style="color:var(--accent-cyan); font-size:1.1rem;">${r.average_score_pct}%</span>
          </div>
          <div class="compare-stat-row">
            <span class="compare-stat-label">Pass Rate</span>
            <span class="compare-stat-val" style="color:var(--accent-emerald);">${r.pass_rate_pct}%</span>
          </div>
          <div class="compare-stat-row">
            <span class="compare-stat-label">Rulebook / Det</span>
            <span class="compare-stat-val">${grad.deterministic || 0}%</span>
          </div>
          <div class="compare-stat-row">
            <span class="compare-stat-label">Efficiency / Loops</span>
            <span class="compare-stat-val">${grad.efficiency || 0}%</span>
          </div>
          <div class="compare-stat-row">
            <span class="compare-stat-label">LLM Safety Judge</span>
            <span class="compare-stat-val">${grad.llm_judge || 0}%</span>
          </div>
          <div class="compare-stat-row">
            <span class="compare-stat-label">Truth / Fact-Check</span>
            <span class="compare-stat-val">${grad.fact_checker || 0}%</span>
          </div>
          <div class="compare-stat-row">
            <span class="compare-stat-label">Avg Latency</span>
            <span class="compare-stat-val">${Math.round(r.avg_latency_ms || 0)}ms</span>
          </div>
          <div class="compare-stat-row">
            <span class="compare-stat-label">Total Tokens</span>
            <span class="compare-stat-val">${(r.total_tokens || 0).toLocaleString()}</span>
          </div>
        </div>
      `;
    }
    cardsHtml += '</div>';

    // Test case side-by-side matrix table
    let matrixHtml = `
      <h4 style="margin:24px 0 12px 0; font-size:1rem; color:#fff;">Side-by-Side Test Case Diffs</h4>
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>Test Case</th>
              ${runs.map(r => `<th>${escapeHtml(r.model)}</th>`).join('')}
            </tr>
          </thead>
          <tbody>
    `;

    for (const row of matrix) {
      matrixHtml += `
        <tr>
          <td><strong>${escapeHtml(row.test_name)}</strong></td>
          ${runs.map(r => {
            const sc = row.scores[r.run_id];
            if (!sc) return '<td><span class="badge badge-dim">-</span></td>';
            const badge = sc.passed
              ? `<span class="badge badge-emerald">${Math.round(sc.overall_score * 100)}%</span>`
              : `<span class="badge badge-rose">${Math.round(sc.overall_score * 100)}%</span>`;
            return `<td>${badge} <span style="font-size:0.75rem; color:var(--text-muted);">${Math.round(sc.latency_ms)}ms</span></td>`;
          }).join('')}
        </tr>
      `;
    }

    matrixHtml += `
          </tbody>
        </table>
      </div>
    `;

    modalBody.innerHTML = cardsHtml + matrixHtml;

  } catch (err) {
    modalBody.innerHTML = `<div class="text-rose py-4">[Error]: ${escapeHtml(err.message)}</div>`;
  }
}

function closeCompareModal(event) {
  if (event && event.target !== document.getElementById('compare-modal') && !event.target.classList.contains('btn-close')) {
    return;
  }
  document.getElementById('compare-modal').classList.remove('active');
}

// ----------------------------------------------------------------------
// Registration Modals (Agent, Model, Judge)
// ----------------------------------------------------------------------

function openRegisterAgentModal() {
  document.getElementById('register-agent-modal').classList.add('active');
}
function closeRegisterAgentModal(event) {
  if (event && event.target !== document.getElementById('register-agent-modal') && !event.target.classList.contains('btn-close') && !event.target.classList.contains('btn-secondary')) return;
  document.getElementById('register-agent-modal').classList.remove('active');
}
function toggleAgentTypeFields() {
  const type = document.getElementById('reg-agent-type').value;
  document.getElementById('reg-agent-url-group').style.display = type === 'http' ? 'block' : 'none';
}
async function submitRegisterAgent() {
  const payload = {
    adapter_id: document.getElementById('reg-agent-id').value.trim(),
    name: document.getElementById('reg-agent-name').value.trim(),
    type: document.getElementById('reg-agent-type').value,
    endpoint_url: document.getElementById('reg-agent-url').value.trim(),
    description: document.getElementById('reg-agent-desc').value.trim()
  };
  if (!payload.adapter_id || !payload.name) {
    alert('Please provide Adapter ID and Name.');
    return;
  }
  try {
    const res = await fetch('/api/evals/agents', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Registration failed');
    closeRegisterAgentModal();
    fetchEvalRegistries();
  } catch (err) { alert(err.message); }
}

function openRegisterModelModal() {
  document.getElementById('register-model-modal').classList.add('active');
}
function closeRegisterModelModal(event) {
  if (event && event.target !== document.getElementById('register-model-modal') && !event.target.classList.contains('btn-close') && !event.target.classList.contains('btn-secondary')) return;
  document.getElementById('register-model-modal').classList.remove('active');
}
async function submitRegisterModel() {
  const payload = {
    model_id: document.getElementById('reg-model-id').value.trim(),
    name: document.getElementById('reg-model-name').value.trim(),
    provider: document.getElementById('reg-model-provider').value.trim(),
    api_base: document.getElementById('reg-model-base').value.trim()
  };
  if (!payload.model_id || !payload.name) {
    alert('Please provide Model ID and Name.');
    return;
  }
  try {
    const res = await fetch('/api/evals/models', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Registration failed');
    closeRegisterModelModal();
    fetchEvalRegistries();
  } catch (err) { alert(err.message); }
}

function openRegisterJudgeModal() {
  document.getElementById('register-judge-modal').classList.add('active');
}
function closeRegisterJudgeModal(event) {
  if (event && event.target !== document.getElementById('register-judge-modal') && !event.target.classList.contains('btn-close') && !event.target.classList.contains('btn-secondary')) return;
  document.getElementById('register-judge-modal').classList.remove('active');
}
async function submitRegisterJudge() {
  const payload = {
    judge_id: document.getElementById('reg-judge-id').value.trim(),
    name: document.getElementById('reg-judge-name').value.trim(),
    model: document.getElementById('reg-judge-model').value.trim(),
    rubric_description: document.getElementById('reg-judge-rubric').value.trim()
  };
  if (!payload.judge_id || !payload.name || !payload.model) {
    alert('Please fill out all required Judge fields.');
    return;
  }
  try {
    const res = await fetch('/api/evals/judges', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Registration failed');
    closeRegisterJudgeModal();
    fetchEvalRegistries();
  } catch (err) { alert(err.message); }
}

async function fetchEvalReports() {
  const container = document.getElementById('eval-reports-list');
  try {
    const res = await fetch('/api/evals/reports');
    if (!res.ok) return;
    const data = await res.json();
    const reports = data.reports || [];

    if (reports.length === 0) {
      container.innerHTML = '<div class="text-muted" style="font-size:0.85rem;">No benchmark reports saved yet.</div>';
      return;
    }

    let html = '';
    for (const r of reports.slice(0, 10)) {
      html += `
        <div class="report-item" onclick="viewReport('${r.filename}')">
          <span style="color:#fff; font-family:var(--font-mono);">${r.filename}</span>
          <span class="badge badge-dim">${Math.round(r.size_bytes / 1024)} KB</span>
        </div>
      `;
    }
    container.innerHTML = html;
  } catch (err) {
    console.error('Failed to load reports:', err);
  }
}

async function viewReport(filename) {
  try {
    const res = await fetch(`/api/evals/reports/${filename}`);
    if (!res.ok) throw new Error('Could not fetch report');
    const data = await res.json();

    document.getElementById('report-modal-filename').innerText = filename;
    document.getElementById('report-modal-content').innerText = data.content || '';
    document.getElementById('report-modal').classList.add('active');
  } catch (err) {
    alert(err.message);
  }
}

function closeReportModal(event) {
  if (event && event.target !== document.getElementById('report-modal') && !event.target.classList.contains('btn-close')) {
    return;
  }
  document.getElementById('report-modal').classList.remove('active');
}

// ----------------------------------------------------------------------
// 4. Utilities & Bootstrap
// ----------------------------------------------------------------------

function formatTime(isoStr) {
  if (!isoStr) return '-';
  try {
    const d = new Date(isoStr);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return isoStr;
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Init
document.addEventListener('DOMContentLoaded', () => {
  fetchData();
  fetchEvalRegistries();
  fetchEvalRuns();
  fetchEvalReports();
  setInterval(fetchData, 8000);

  // Global Escape key listener to close all open modals
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' || e.key === 'Esc') {
      const activeModals = document.querySelectorAll('.modal-backdrop.active');
      activeModals.forEach(modal => modal.classList.remove('active'));
    }
  });
});
