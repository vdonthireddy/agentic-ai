// State
let allLogs = [];
let gatewayStats = {};
let availableModels = [];
let currentTab = 'overview';
let activeCallDetail = null;

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
    overview: 'Observatory Overview',
    logs: 'Interaction Audit Logs',
    playground: 'Gateway Playground & Tester'
  };
  document.getElementById('page-title').innerText = titleMap[tabId] || 'Observatory';
}

// Fetch Stats & Logs
async function fetchData() {
  try {
    // 1. Fetch Stats
    const statsRes = await fetch('/v1/stats');
    if (statsRes.ok) {
      gatewayStats = await statsRes.json();
      renderStats();
    }

    // 2. Fetch Logs
    const logsRes = await fetch('/v1/logs?limit=100');
    if (logsRes.ok) {
      const data = await logsRes.json();
      allLogs = data.logs || [];
      renderRecentLogs();
      renderAllLogs();
    }

    // 3. Fetch Models
    const modelsRes = await fetch('/v1/models');
    if (modelsRes.ok) {
      const data = await modelsRes.json();
      availableModels = data.data || [];
      populateModelFilters();
    }
  } catch (err) {
    console.error('Failed to fetch dashboard data:', err);
  }
}

// Render KPI Cards and Charts
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

  const toolCount = Object.keys(gatewayStats.tools_usage_frequency || {}).length;
  const skillCount = Object.keys(gatewayStats.skills_usage_frequency || {}).length;
  document.getElementById('stat-tools-count').innerText = `${toolCount} Tools Active`;
  document.getElementById('stat-skills-count').innerText = `${skillCount} Skills Injected`;

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
    html += '<h4 style="font-size:0.8rem; color:var(--accent-purple); text-transform:uppercase; margin-bottom:8px;">Active Skills Injected</h4>';
    const skillMax = Math.max(...Object.values(skills), 1);
    for (const [skill, count] of Object.entries(skills)) {
      const pct = Math.round((count / skillMax) * 100);
      html += `
        <div class="bar-item">
          <div class="bar-header">
            <strong>${skill}</strong>
            <span>${count} invocations</span>
          </div>
          <div class="bar-track">
            <div class="bar-fill bar-fill-purple" style="width: ${pct}%;"></div>
          </div>
        </div>
      `;
    }
  }

  if (hasTools) {
    html += '<h4 style="font-size:0.8rem; color:var(--accent-emerald); text-transform:uppercase; margin:16px 0 8px 0;">MCP Tools Dispatched</h4>';
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

// Render Recent Table (Overview)
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

// Render All Logs Table
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

function populateModelFilters() {
  const filterSelect = document.getElementById('log-model-filter');
  const pgModelSelect = document.getElementById('pg-model-select');
  
  if (filterSelect && availableModels.length > 0) {
    const currentVal = filterSelect.value;
    let opts = '<option value="">All Models</option>';
    let pgOpts = '';
    for (const m of availableModels) {
      opts += `<option value="${m.id}">${m.id}</option>`;
      pgOpts += `<option value="${m.id}">${m.id}</option>`;
    }
    filterSelect.innerHTML = opts;
    filterSelect.value = currentVal;
    
    if (pgModelSelect && pgOpts) {
      const curPg = pgModelSelect.value;
      pgModelSelect.innerHTML = pgOpts;
      pgModelSelect.value = curPg || availableModels[0].id;
    }
  }
}

// Modal Inspector
function openDetailModal(callId) {
  const log = allLogs.find(l => l.id === callId);
  if (!log) return;
  activeCallDetail = log;

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

// Playground Execution
async function sendPlaygroundRequest() {
  const model = document.getElementById('pg-model-select').value;
  const agentName = document.getElementById('pg-agent-name').value;
  const callerId = document.getElementById('pg-caller-id').value;
  const skillName = document.getElementById('pg-skill-select').value;
  const prompt = document.getElementById('pg-prompt').value;

  const btn = document.getElementById('pg-submit-btn');
  const output = document.getElementById('pg-output-container');
  const meta = document.getElementById('pg-response-meta');

  btn.disabled = true;
  btn.innerHTML = '<span>⏳ Invoking LLM...</span>';
  meta.innerText = 'Processing request...';
  meta.className = 'badge badge-amber';

  try {
    const payload = {
      model: model,
      messages: [
        { role: 'system', content: 'You are an intelligent assistant tested from the Gateway Playground.' },
        { role: 'user', content: prompt }
      ],
      caller_id: callerId,
      agent_name: agentName,
      session_id: `pg_${Date.now()}`,
      skill_names: skillName ? [skillName] : [],
      caller_context: { source: 'playground_ui' }
    };

    const res = await fetch('/v1/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.message || data.detail || 'Gateway error');
    }

    const choice = data.choices && data.choices[0];
    const msg = choice ? choice.message : {};
    const content = msg.content || (msg.tool_calls ? JSON.stringify(msg.tool_calls, null, 2) : 'No content');
    const usage = data.usage || {};
    const gwMeta = data.gateway_metadata || {};

    output.innerText = content;
    meta.innerText = `Call ID: ${gwMeta.call_id} | Tokens: ${usage.total_tokens || 0} | Latency: ${Math.round(gwMeta.latency_ms || 0)}ms`;
    meta.className = 'badge badge-emerald';

    // Refresh tables
    setTimeout(fetchData, 400);

  } catch (err) {
    output.innerText = `[Error]: ${err.message}`;
    meta.innerText = 'Request Failed';
    meta.className = 'badge badge-rose';
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>⚡ Dispatch Request</span>';
  }
}

// Utilities
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

// Initial Load & Auto Refresh
document.addEventListener('DOMContentLoaded', () => {
  fetchData();
  setInterval(fetchData, 6000);
});
