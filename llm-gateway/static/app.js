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

function renderBotResponse(data) {
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
      <div>${escapeHtml(data.response || 'No response generated.')}</div>
      ${metaHtml}
    </div>
  `;
  container.appendChild(row);
}

function renderErrorMessage(msg) {
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

async function clearChat() {
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
      populateModelSelectors();
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

function populateModelSelectors() {
  const selects = [
    document.getElementById('chat-model-select'),
    document.getElementById('log-model-filter'),
    document.getElementById('eval-model-select')
  ];

  if (availableModels.length === 0) return;

  for (const sel of selects) {
    if (!sel) continue;
    const cur = sel.value;
    let opts = sel.id === 'log-model-filter' ? '<option value="">All Models</option>' : '';
    for (const m of availableModels) {
      opts += `<option value="${m.id}">${m.id}</option>`;
    }
    sel.innerHTML = opts;
    if (cur) sel.value = cur;
  }

  const activeModelDisplay = document.getElementById('active-model-display');
  if (activeModelDisplay && availableModels[0]) {
    activeModelDisplay.innerText = availableModels[0].id;
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
// 3. Evals Framework Runner & Reports
// ----------------------------------------------------------------------

async function startEvals() {
  const model = document.getElementById('eval-model-select').value;
  const categories = [];
  if (document.getElementById('chk-tool-calling').checked) categories.push('tool_calling');
  if (document.getElementById('chk-skill-adherence').checked) categories.push('skill_adherence');
  if (document.getElementById('chk-reasoning').checked) categories.push('reasoning');

  const btn = document.getElementById('eval-run-btn');
  const badge = document.getElementById('eval-status-badge');
  const container = document.getElementById('eval-results-container');

  btn.disabled = true;
  btn.innerHTML = '<span>⏳ Running Benchmarks...</span>';
  badge.innerText = 'Evaluating...';
  badge.className = 'badge badge-amber';

  container.innerHTML = `
    <div class="text-center py-8">
      <div style="font-size:32px; margin-bottom:12px;">🧪</div>
      <h3>Executing Benchmark Suite on ${model}</h3>
      <p class="text-muted">Evaluating tool calling accuracy, skill adherence, and numerical correctness...</p>
    </div>
  `;

  try {
    const res = await fetch('/api/evals/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: model, categories: categories })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.message || data.detail || 'Evaluation failed');

    badge.innerText = `Score: ${data.average_score}%`;
    badge.className = data.pass_rate >= 70 ? 'badge badge-emerald' : 'badge badge-rose';

    renderEvalScorecard(data);
    fetchEvalReports();

  } catch (err) {
    badge.innerText = 'Evaluation Failed';
    badge.className = 'badge badge-rose';
    container.innerHTML = `<div class="text-rose py-4">[Error]: ${escapeHtml(err.message)}</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>🚀 Execute Evaluation Suite</span>';
  }
}

function renderEvalScorecard(data) {
  const container = document.getElementById('eval-results-container');
  const perf = data.performance_metrics || {};

  let html = `
    <div class="scorecard-summary">
      <div class="score-box">
        <span>Pass Rate</span>
        <h4 style="color:var(--accent-cyan);">${data.passed_tests}/${data.total_tests} (${data.pass_rate}%)</h4>
      </div>
      <div class="score-box">
        <span>Average Score</span>
        <h4 style="color:var(--accent-emerald);">${data.average_score}%</h4>
      </div>
      <div class="score-box">
        <span>Total Tokens</span>
        <h4 style="color:var(--accent-purple);">${(perf.total_tokens || 0).toLocaleString()}</h4>
      </div>
      <div class="score-box">
        <span>Avg Latency</span>
        <h4 style="color:#fff;">${Math.round(perf.avg_latency_ms || 0)} ms</h4>
      </div>
    </div>

    <h4 style="margin:20px 0 10px 0; font-size:0.95rem;">Test Case Breakdown</h4>
    <div class="table-responsive">
      <table class="data-table">
        <thead>
          <tr>
            <th>Status</th>
            <th>Test Name</th>
            <th>Category</th>
            <th>Tool Score</th>
            <th>Skill Score</th>
            <th>Score</th>
          </tr>
        </thead>
        <tbody>
  `;

  for (const t of data.test_results || []) {
    const statusIcon = t.overall_passed
      ? '<span class="badge badge-emerald">PASS</span>'
      : '<span class="badge badge-rose">FAIL</span>';

    html += `
      <tr>
        <td>${statusIcon}</td>
        <td><strong>${escapeHtml(t.name)}</strong></td>
        <td><span class="badge badge-dim">${escapeHtml(t.category)}</span></td>
        <td class="font-mono">${Math.round((t.tool_score || 0) * 100)}%</td>
        <td class="font-mono">${Math.round((t.skill_score || 0) * 100)}%</td>
        <td class="font-mono"><strong>${Math.round((t.composite_score || 0) * 100)}%</strong></td>
      </tr>
    `;
  }

  html += `
        </tbody>
      </table>
    </div>
  `;

  container.innerHTML = html;
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
    for (const r of reports.slice(0, 5)) {
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
  setInterval(fetchData, 8000);
});
