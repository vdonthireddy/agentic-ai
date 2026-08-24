import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ChatView from '../views/ChatView';
import SkillsView from '../views/SkillsView';
import TelemetryView from '../views/TelemetryView';
import WorkspaceView from '../views/WorkspaceView';
import SettingsView from '../views/SettingsView';
import OrchestratorView from '../views/OrchestratorView';
import MemoryView from '../views/MemoryView';
import { api } from '../api/client';

vi.mock('../api/client', () => ({
  api: {
    sendChat: vi.fn(),
    clearChat: vi.fn(),
    getTools: vi.fn().mockResolvedValue({ tools: [] }),
    getSkills: vi.fn().mockResolvedValue({ skills: [] }),
    getStats: vi.fn().mockResolvedValue({ total_calls: 0, successful_calls: 0, average_latency_ms: 0, token_usage: {} }),
    getLogs: vi.fn().mockResolvedValue({ logs: [] }),
    getWorkspaceFiles: vi.fn().mockResolvedValue({ files: [] }),
    getSystemMetrics: vi.fn().mockResolvedValue({ cpu: { usage_percent: 10 }, memory: { percent_used: 40 } }),
    getConfig: vi.fn().mockResolvedValue({ transport: 'http', default_model: 'ollama/gemma2:2b' }),
    updateConfig: vi.fn().mockResolvedValue({ success: true }),
    getEvalAgents: vi.fn().mockResolvedValue({ agents: [] }),
    getEvalModels: vi.fn().mockResolvedValue({ models: [] }),
    getEvalJudges: vi.fn().mockResolvedValue({ judges: [] }),
    getEvalRuns: vi.fn().mockResolvedValue({ runs: [] }),
  }
}));

describe('React WebUI Views Unit Tests', () => {
  it('ChatView renders prompt chips and sends user messages', async () => {
    api.sendChat.mockResolvedValueOnce({
      response: 'Trip planned for Paris!',
      tool_calls: [{ tool: 'weather', args: { city: 'Paris' }, result: 'Sunny 22C' }],
      tokens: { prompt_tokens: 20, completion_tokens: 15 }
    });

    render(
      <ChatView
        models={[{ id: 'ollama/qwen2.5-coder:7b', name: 'Qwen 2.5 Coder' }]}
        skills={[{ id: 'travel_planner_skill', name: '✈️ Vacation Concierge' }]}
      />
    );

    expect(screen.getByText(/Welcome to your Everyday AI Agent!/)).toBeInTheDocument();

    const input = screen.getByPlaceholderText(/Ask me anything/);
    fireEvent.change(input, { target: { value: 'Plan a trip to Paris' } });
    fireEvent.click(screen.getByText('Send'));

    await waitFor(() => {
      expect(screen.getByText('Trip planned for Paris!')).toBeInTheDocument();
      expect(screen.getByText(/Executed Tool:/)).toBeInTheDocument();
    });
  });

  it('ChatView renders Progressive Disclosure badge when load_skill executes', async () => {
    api.sendChat.mockResolvedValueOnce({
      response: 'Loaded Travel Concierge Persona!',
      tool_calls: [{ tool: 'load_skill', args: { skill_name: 'travel_planner_skill' }, result: { status: 'success' } }],
      tokens: { prompt_tokens: 10, completion_tokens: 10 }
    });

    render(
      <ChatView
        models={[{ id: 'ollama/qwen2.5-coder:7b', name: 'Qwen 2.5 Coder' }]}
        skills={[{ id: 'travel_planner_skill', name: '✈️ Vacation Concierge' }]}
      />
    );

    const input = screen.getByPlaceholderText(/Ask me anything/);
    fireEvent.change(input, { target: { value: 'Load travel planner' } });
    fireEvent.click(screen.getByText('Send'));

    await waitFor(() => {
      expect(screen.getByText('✨ Progressive Skill Loaded')).toBeInTheDocument();
    });
  });

  it('SkillsView renders domain skill cards, Progressive Disclosure banner, and triggers activation', () => {
    const onActivate = vi.fn();
    const skills = [
      { id: 'travel_planner_skill', name: '✈️ Vacation Concierge', description: 'Plans trips', category: 'Travel & Lifestyle', recommended_tools: ['weather'] }
    ];

    render(<SkillsView skills={skills} onActivateSkill={onActivate} />);

    expect(screen.getByText(/Progressive Disclosure Enabled/i)).toBeInTheDocument();
    expect(screen.getByText('Vacation Concierge')).toBeInTheDocument();
    expect(screen.getByText('Plans trips')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Activate in Chat'));
    expect(onActivate).toHaveBeenCalledWith('travel_planner_skill');
  });

  it('TelemetryView renders KPI metric values', () => {
    const stats = {
      total_calls: 42,
      success_rate: 98,
      avg_latency_ms: 250,
      token_usage: { prompt_tokens: 500, completion_tokens: 200, total_tokens: 700 },
      models_usage: { 'openai/gpt-4o': 30, 'ollama/qwen2.5-coder:7b': 12 }
    };

    render(<TelemetryView stats={stats} />);

    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('98%')).toBeInTheDocument();
    expect(screen.getByText('250 ms')).toBeInTheDocument();
    expect(screen.getByText('700')).toBeInTheDocument();
  });

  it('SettingsView loads and saves configuration', async () => {
    render(<SettingsView />);

    await waitFor(() => {
      expect(screen.getByText('🔑 Multi-Provider API Keys & Endpoints')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Save Gateway Configuration/));
    await waitFor(() => {
      expect(api.updateConfig).toHaveBeenCalled();
    });
  });

  it('AuditLogsView renders categorized hierarchical interactions', async () => {
    const mockHierarchicalConvs = [
      {
        conv_id: 'conv_test_123',
        started_at: new Date().toISOString(),
        last_activity: new Date().toISOString(),
        total_requests: 2,
        total_tokens: 450,
        agent_name: 'EverydayAssistant',
        model: 'ollama/qwen2.5-coder:7b',
        turns: [
          {
            t_id: 'turn_1_999',
            turn_started_at: new Date().toISOString(),
            request_count: 2,
            turn_total_tokens: 450,
            turn_total_latency_ms: 180,
            requests: [
              {
                request_id: 'req_1_abc',
                status: 'SUCCESS',
                model: 'ollama/qwen2.5-coder:7b',
                tool_names: ['calculator'],
                prompt_tokens: 150,
                completion_tokens: 50,
                total_tokens: 200,
                latency_ms: 90
              }
            ]
          }
        ]
      }
    ];

    api.getLogs.mockResolvedValueOnce({ logs: [] });
    api.getLogs.mockResolvedValueOnce({ conversations: mockHierarchicalConvs });

    const AuditLogsView = (await import('../views/AuditLogsView')).default;
    render(<AuditLogsView models={[{ id: 'ollama/qwen2.5-coder:7b' }]} />);

    await waitFor(() => {
      expect(screen.getByText(/Interaction Audit Logs/)).toBeInTheDocument();
      expect(screen.getByText('conv_test_123')).toBeInTheDocument();
      expect(screen.getByText(/Turn #1/)).toBeInTheDocument();
      expect(screen.getByText('req_1_abc')).toBeInTheDocument();
    });
  });

  it('OrchestratorView renders task planner input, model select, and run button', () => {
    render(<OrchestratorView models={[{ id: 'ollama/gemma2:2b', name: 'Gemma 2' }]} />);

    expect(screen.getByText(/Multi-Agent Orchestrator/)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Describe a complex task/)).toBeInTheDocument();
    expect(screen.getByText(/Run Task Decomposition/i)).toBeInTheDocument();
  });

  it('MemoryView renders search bar, namespace tabs, and store section', async () => {
    global.fetch = vi.fn().mockImplementation((url) => {
      if (url.includes('/api/memory/list')) {
        return Promise.resolve({
          json: () => Promise.resolve({ memories: [{ memory_id: 'mem_1', content: 'Test memory content', namespace: 'default' }], available_namespaces: ['default'] })
        });
      }
      if (url.includes('/api/memory/namespaces')) {
        return Promise.resolve({
          json: () => Promise.resolve({ namespaces: ['default', 'work'] })
        });
      }
      return Promise.resolve({ json: () => Promise.resolve({}) });
    });

    render(<MemoryView />);

    expect(screen.getByText(/Memory Explorer/)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Search memories semantically/)).toBeInTheDocument();
    expect(screen.getByText(/Store New Memory/)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Test memory content')).toBeInTheDocument();
    });
  });
});
