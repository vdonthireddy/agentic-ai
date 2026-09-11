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
import CanvasView from '../views/CanvasView';
import ApprovalsView from '../views/ApprovalsView';
import SmartRouterView from '../views/SmartRouterView';
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
    getHITLPending: vi.fn().mockResolvedValue({ pending: [] }),
    approveHITL: vi.fn().mockResolvedValue({ success: true }),
    denyHITL: vi.fn().mockResolvedValue({ success: true }),
    getHITLRules: vi.fn().mockResolvedValue({ rules: [] }),
    getHITLHistory: vi.fn().mockResolvedValue({ history: [] }),
    getSmartRouterConfig: vi.fn().mockResolvedValue({
      enabled: true,
      default_reasoning_model: 'ollama/llama3.2:latest',
      fallback_model: 'ollama/mistral:latest',
      categories: {
        coding: {
          name: 'Coding & Software Engineering',
          description: 'Code generation and debugging',
          accuracy_threshold: 0.75,
          target_model: 'ollama/qwen2.5-coder:7b'
        }
      },
      available_models: ['ollama/llama3.2:latest', 'ollama/qwen2.5-coder:7b']
    }),
    routeSmartPrompt: vi.fn().mockResolvedValue({
      success: true,
      response: 'def test(): pass',
      target_model: 'ollama/qwen2.5-coder:7b',
      trace: {
        id: 'sr_123',
        prompt: 'Write python',
        reasoning_model: 'ollama/llama3.2:latest',
        target_model: 'ollama/qwen2.5-coder:7b',
        target_prompt: 'Write python',
        target_response: 'def test(): pass',
        category: 'coding',
        confidence: 0.95,
        threshold: 0.75,
        threshold_met: true,
        routing_decision: {
          category: 'coding',
          confidence: 0.95,
          threshold: 0.75,
          threshold_met: true,
          reasoning: 'Python code requested'
        },
        stage1_latency_ms: 100,
        stage2_latency_ms: 200,
        total_latency_ms: 300,
        total_tokens: 50
      }
    }),
    updateSmartRouterConfig: vi.fn().mockResolvedValue({ success: true }),
    getSmartRouterLogs: vi.fn().mockResolvedValue({
      logs: [{
        id: 'sr_log_1',
        timestamp: new Date().toISOString(),
        prompt: 'Write a python server',
        reasoning_model: 'ollama/llama3.2:latest',
        category: 'coding',
        confidence: 0.95,
        threshold: 0.75,
        threshold_met: true,
        target_model: 'ollama/qwen2.5-coder:7b',
        target_prompt: 'Write a python server',
        target_response: 'import http.server',
        stage1_latency_ms: 100,
        stage2_latency_ms: 200,
        total_latency_ms: 300,
        total_tokens: 50
      }]
    }),
    clearSmartRouterLogs: vi.fn().mockResolvedValue({ deleted: 1 })
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

  it('ChatView does not force auto-scroll down on initial mount with welcome screen', () => {
    const scrollIntoViewSpy = vi.fn();
    window.HTMLElement.prototype.scrollIntoView = scrollIntoViewSpy;

    render(
      <ChatView
        models={[{ id: 'ollama/gemma2:2b', name: 'Gemma 2' }]}
        skills={[]}
      />
    );

    expect(screen.getByText(/Welcome to your Everyday AI Agent!/i)).toBeInTheDocument();
    // Verify scrollIntoView is NOT called on initial empty mount
    expect(scrollIntoViewSpy).not.toHaveBeenCalled();
  });

  it('CanvasView renders Runs History button and opens runs modal', async () => {
    global.fetch = vi.fn().mockImplementation((url) => {
      if (url.includes('/api/canvas/pipelines')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ pipelines: [] })
        });
      }
      if (url.endsWith('/api/canvas/runs/run_test_abc123')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            run: {
              run_id: 'run_test_abc123',
              workflow_name: 'Safety Fork DAG',
              status: 'paused',
              created_at: '2026-09-07T06:06:54.000Z',
              duration_ms: 120
            },
            checkpoints: [
              {
                id: 'chk_1',
                run_id: 'run_test_abc123',
                node_id: 'node_test_gate',
                stage: 1,
                label: '1. Intent Classifier',
                status: 'COMPLETED',
                step_input: 'Hello',
                output: 'Approved',
                created_at: '2026-09-07T06:06:55.000Z',
                duration_ms: 45
              }
            ]
          })
        });
      }
      if (url.includes('/api/canvas/runs')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            runs: [
              {
                run_id: 'run_test_abc123',
                workflow_name: 'Safety Fork DAG',
                name: 'Safety Fork DAG',
                status: 'paused',
                nodes_count: 4,
                duration_ms: 120,
                created_at: '2026-09-07T06:06:54.000Z'
              }
            ]
          })
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });

    render(<CanvasView />);

    expect(screen.getByText(/Visual Workflow Canvas/i)).toBeInTheDocument();
    const runsBtn = screen.getByText(/Runs History/i);
    expect(runsBtn).toBeInTheDocument();

    fireEvent.click(runsBtn);

    await waitFor(() => {
      expect(screen.getByText(/Workflow Execution Runs & Checkpoints/i)).toBeInTheDocument();
      expect(screen.getByText('Safety Fork DAG')).toBeInTheDocument();
      expect(screen.getByText('🛡️ PAUSED')).toBeInTheDocument();
      expect(screen.getByText('Resume Execution')).toBeInTheDocument();
      // Verify run timestamp is rendered
      expect(screen.getByText(/2026/i)).toBeInTheDocument();
    });

    // Click on run to inspect checkpoints and run header details
    fireEvent.click(screen.getByText('Safety Fork DAG'));

    await waitFor(() => {
      expect(screen.getByText(/Durable Step Checkpoints \(1\)/i)).toBeInTheDocument();
      expect(screen.getByText('1. Intent Classifier')).toBeInTheDocument();
      expect(screen.getByText(/Node ID: node_test_gate/i)).toBeInTheDocument();
      expect(screen.getByText(/Started:/i)).toBeInTheDocument();
    });

    // Test that pressing Escape closes the Runs History modal
    fireEvent.keyDown(window, { key: 'Escape', code: 'Escape' });
    await waitFor(() => {
      expect(screen.queryByText(/Workflow Execution Runs & Checkpoints/i)).not.toBeInTheDocument();
    });
  });

  it('ApprovalsView displays pending requests, triggers approve/deny, and displays rules', async () => {
    api.getHITLPending.mockResolvedValue({
      pending: [
        {
          request_id: 'hitl_test_pending_01',
          tool_name: 'DAG_HITL_Gate',
          arguments: { node_id: 'node_6', task: 'hi' },
          risk_level: 'high',
          description: 'Workflow Approval Required: Node 6',
          created_at: Date.now() / 1000,
          timeout_seconds: 120
        }
      ]
    });

    api.getHITLRules.mockResolvedValue({
      rules: [
        {
          tool_name: 'workspace_file_ops',
          risk_level: 'high',
          description: 'File deletion requires approval.',
          action_filter: ['delete'],
          timeout_seconds: 60
        }
      ]
    });

    api.getHITLHistory.mockResolvedValue({
      history: [
        {
          request_id: 'hitl_hist_01',
          tool_name: 'DAG_HITL_Gate',
          status: 'approved',
          resolved_by: 'web_ui_user',
          created_at: Date.now() / 1000
        }
      ]
    });

    render(<ApprovalsView onRefreshAll={vi.fn()} />);

    expect(screen.getByText(/Human-in-the-Loop \(HITL\) Safety & Approvals/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('DAG_HITL_Gate')).toBeInTheDocument();
      expect(screen.getByText('HIGH RISK')).toBeInTheDocument();
      expect(screen.getByText(/Workflow Approval Required: Node 6/)).toBeInTheDocument();
      expect(screen.getByTitle(/Submitted:/)).toBeInTheDocument();
      expect(screen.getByText('✓ Approve Action')).toBeInTheDocument();
      expect(screen.getByText('✕ Deny Request')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('✓ Approve Action'));
    await waitFor(() => {
      expect(api.approveHITL).toHaveBeenCalledWith('hitl_test_pending_01');
    });

    fireEvent.click(screen.getByText(/Safety Policy Rules/));
    await waitFor(() => {
      expect(screen.getByText('workspace_file_ops')).toBeInTheDocument();
      expect(screen.getByText('File deletion requires approval.')).toBeInTheDocument();
    });
  });

  it('SmartRouterView renders playground, executes dynamic routing, and inspects call log modal', async () => {
    render(<SmartRouterView models={[{ id: 'ollama/llama3.2:latest' }, { id: 'ollama/qwen2.5-coder:7b' }]} />);

    expect(screen.getByText(/Smart-Router/i)).toBeInTheDocument();
    expect(screen.getByText(/Route & Playground/i)).toBeInTheDocument();

    // Input prompt and route
    const textarea = screen.getByPlaceholderText(/Enter any coding, complex reasoning/i);
    fireEvent.change(textarea, { target: { value: 'Write an async Python function' } });

    const routeBtn = screen.getByText(/Route & Execute Prompt/i);
    fireEvent.click(routeBtn);

    await waitFor(() => {
      expect(api.routeSmartPrompt).toHaveBeenCalledWith(expect.objectContaining({
        prompt: 'Write an async Python function'
      }));
      expect(screen.getByText(/2-Stage Dynamic Routing Trace/i)).toBeInTheDocument();
      expect(screen.getByText(/Reasoning Model Dispatch/i)).toBeInTheDocument();
      expect(screen.getByText(/Target Model Execution/i)).toBeInTheDocument();
      expect(screen.getByText('def test(): pass')).toBeInTheDocument();
    });

    // Switch to Full Call Logs tab
    const logsTabBtn = screen.getByText(/Full Call Logs/i);
    fireEvent.click(logsTabBtn);

    await waitFor(() => {
      expect(screen.getByText('Write a python server')).toBeInTheDocument();
      expect(screen.getByText('Inspect Call Log')).toBeInTheDocument();
    });

    // Open Inspector Modal
    fireEvent.click(screen.getByText('Inspect Call Log'));

    await waitFor(() => {
      expect(screen.getByText(/Smart Router Full Call Log Trace/i)).toBeInTheDocument();
      expect(screen.getByText(/1. Original User Prompt:/i)).toBeInTheDocument();
      expect(screen.getByText(/2. Default Reasoning Model Used:/i)).toBeInTheDocument();
      expect(screen.getByText(/3. Reasoning Response & Model Selection Decision:/i)).toBeInTheDocument();
      expect(screen.getByText(/4. Prompt Sent to This New Model:/i)).toBeInTheDocument();
      expect(screen.getByText(/5. Response from New Model/i)).toBeInTheDocument();
      expect(screen.getByText('import http.server')).toBeInTheDocument();
    });
  });
});
