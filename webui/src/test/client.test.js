import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from '../api/client';

describe('API Client Unit Tests', () => {
  beforeEach(() => {
    global.fetch = vi.fn();
  });

  it('sendChat sends POST request to /api/chat with proper payload', async () => {
    const mockResponse = {
      response: 'Hello from agent',
      tool_calls: [],
      tokens: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 }
    };

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    const result = await api.sendChat({
      message: 'Hello',
      model: 'openai/gpt-4o',
      session_id: 'test_sess'
    });

    expect(global.fetch).toHaveBeenCalledWith('/api/chat', expect.objectContaining({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: 'Hello', model: 'openai/gpt-4o', session_id: 'test_sess', conversation_id: 'test_sess' })
    }));

    expect(result.response).toBe('Hello from agent');
  });

  it('getTools fetches /api/tools', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ tools: [{ name: 'calculator' }] }),
    });

    const result = await api.getTools();
    expect(global.fetch).toHaveBeenCalledWith('/api/tools');
    expect(result.tools.length).toBe(1);
  });

  it('executeTool calls /api/tools/execute with args', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, result: '42' }),
    });

    const result = await api.executeTool('calculator', { expression: '6 * 7' });
    expect(global.fetch).toHaveBeenCalledWith('/api/tools/execute', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ tool: 'calculator', args: { expression: '6 * 7' } })
    }));
    expect(result.result).toBe('42');
  });

  it('getWorkspaceFiles fetches /api/workspace/files', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ files: [{ filename: 'notes.txt' }] }),
    });

    const result = await api.getWorkspaceFiles();
    expect(global.fetch).toHaveBeenCalledWith('/api/workspace/files');
    expect(result.files[0].filename).toBe('notes.txt');
  });

  it('getSystemMetrics fetches /api/system/metrics', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ cpu: { usage_percent: 12.5 } }),
    });

    const result = await api.getSystemMetrics();
    expect(global.fetch).toHaveBeenCalledWith('/api/system/metrics');
    expect(result.cpu.usage_percent).toBe(12.5);
  });
});
