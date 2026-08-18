/**
 * Unified API client communicating with FastAPI LLM Gateway backend.
 */

export const api = {
  // Chat
  async sendChat({ message, model, skill_name, session_id, conversation_id, turn_id }) {
    const convId = conversation_id || session_id;
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        model,
        skill_name,
        session_id: convId,
        conversation_id: convId,
        turn_id
      })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.message || err.detail || 'Chat request failed');
    }
    return res.json();
  },

  async clearChat(conversation_id) {
    const res = await fetch('/api/chat/clear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conversation_id, session_id: conversation_id })
    });
    return res.json();
  },

  // Gateway Models, Stats & Logs
  async getModels() {
    const res = await fetch('/v1/models');
    return res.json();
  },

  async getStats() {
    const res = await fetch('/v1/stats');
    return res.json();
  },

  async getLogs(options = 50) {
    let url = '/v1/logs?';
    if (typeof options === 'number') {
      url += `limit=${options}`;
    } else {
      const params = new URLSearchParams();
      if (options.limit) params.append('limit', options.limit);
      if (options.offset) params.append('offset', options.offset);
      if (options.conversation_id) params.append('conversation_id', options.conversation_id);
      if (options.turn_id) params.append('turn_id', options.turn_id);
      if (options.request_id) params.append('request_id', options.request_id);
      if (options.session_id) params.append('session_id', options.session_id);
      if (options.model) params.append('model', options.model);
      if (options.agent_name) params.append('agent_name', options.agent_name);
      if (options.hierarchical) params.append('hierarchical', 'true');
      url += params.toString();
    }
    const res = await fetch(url);
    return res.json();
  },

  async getHealth() {
    const res = await fetch('/health');
    return res.json();
  },

  // MCP Tools
  async getTools() {
    const res = await fetch('/api/tools');
    return res.json();
  },

  async executeTool(tool, args = {}) {
    const res = await fetch('/api/tools/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool, args })
    });
    return res.json();
  },

  // Domain Skills
  async getSkills() {
    const res = await fetch('/api/skills');
    return res.json();
  },

  async createCustomSkill(skill) {
    const res = await fetch('/api/skills/custom', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(skill)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to create skill');
    }
    return res.json();
  },

  async deleteCustomSkill(skillId) {
    const res = await fetch(`/api/skills/custom/${encodeURIComponent(skillId)}`, {
      method: 'DELETE'
    });
    return res.json();
  },

  // Workspace Files
  async getWorkspaceFiles() {
    const res = await fetch('/api/workspace/files');
    return res.json();
  },

  async getWorkspaceFile(filename) {
    const res = await fetch(`/api/workspace/files/${encodeURIComponent(filename)}`);
    if (!res.ok) throw new Error('File not found');
    return res.json();
  },

  async saveWorkspaceFile(filename, content) {
    const res = await fetch('/api/workspace/files', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename, content })
    });
    return res.json();
  },

  async deleteWorkspaceFile(filename) {
    const res = await fetch(`/api/workspace/files/${encodeURIComponent(filename)}`, {
      method: 'DELETE'
    });
    return res.json();
  },

  // System Telemetry
  async getSystemMetrics() {
    const res = await fetch('/api/system/metrics');
    return res.json();
  },

  // Gateway Config
  async getConfig() {
    const res = await fetch('/api/config');
    return res.json();
  },

  async updateConfig(config) {
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    return res.json();
  },

  // Evals Registries & Runner
  async getEvalAgents() {
    const res = await fetch('/api/evals/agents');
    return res.json();
  },

  async registerEvalAgent(agent) {
    const res = await fetch('/api/evals/agents', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(agent)
    });
    return res.json();
  },

  async deleteEvalAgent(id) {
    const res = await fetch(`/api/evals/agents/${encodeURIComponent(id)}`, {
      method: 'DELETE'
    });
    return res.json();
  },

  async getEvalModels() {
    const res = await fetch('/api/evals/models');
    return res.json();
  },

  async registerEvalModel(model) {
    const res = await fetch('/api/evals/models', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(model)
    });
    return res.json();
  },

  async deleteEvalModel(id) {
    const res = await fetch(`/api/evals/models/${encodeURIComponent(id)}`, {
      method: 'DELETE'
    });
    return res.json();
  },

  async getEvalJudges() {
    const res = await fetch('/api/evals/judges');
    return res.json();
  },

  async registerEvalJudge(judge) {
    const res = await fetch('/api/evals/judges', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(judge)
    });
    return res.json();
  },

  async deleteEvalJudge(id) {
    const res = await fetch(`/api/evals/judges/${encodeURIComponent(id)}`, {
      method: 'DELETE'
    });
    return res.json();
  },

  async runEvals({ agent_id, model, judge_model, categories, iterations = 1 }) {
    const res = await fetch('/api/evals/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent_id, model, judge_model, categories, iterations })
    });
    return res.json();
  },

  async compareModels({ models, agent_id, judge_model, categories, iterations = 1 }) {
    const res = await fetch('/api/evals/compare-models', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ models, agent_id, judge_model, categories, iterations })
    });
    return res.json();
  },

  async getEvalRuns() {
    const res = await fetch('/api/evals/runs');
    return res.json();
  },

  async compareRuns(runIds) {
    const res = await fetch(`/api/evals/compare?runs=${encodeURIComponent(runIds.join(','))}`);
    return res.json();
  }
};
