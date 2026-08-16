import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Sidebar from '../components/Sidebar';
import TopHeader from '../components/TopHeader';
import InspectorModal from '../components/InspectorModal';
import CreateSkillModal from '../components/CreateSkillModal';

describe('React WebUI Components Unit Tests', () => {
  it('Sidebar renders all 8 Studio tabs and handles tab selection', () => {
    const onSelectTab = vi.fn();
    render(<Sidebar activeTab="chat" onSelectTab={onSelectTab} health={{}} />);

    expect(screen.getByText('AI Agent Chatbot')).toBeInTheDocument();
    expect(screen.getByText('MCP Tools & Sandbox')).toBeInTheDocument();
    expect(screen.getByText('Domain Skills Hub')).toBeInTheDocument();
    expect(screen.getByText('Workspace Files')).toBeInTheDocument();
    expect(screen.getByText('Telemetry & Metrics')).toBeInTheDocument();
    expect(screen.getByText('Audit Logs')).toBeInTheDocument();
    expect(screen.getByText('Evals & Benchmarks')).toBeInTheDocument();
    expect(screen.getByText('Settings & Providers')).toBeInTheDocument();

    fireEvent.click(screen.getByText('MCP Tools & Sandbox'));
    expect(onSelectTab).toHaveBeenCalledWith('tools');
  });

  it('TopHeader displays active title and model badge', () => {
    const onRefresh = vi.fn();
    render(
      <TopHeader
        activeTab="chat"
        activeModel="openai/gpt-4o"
        onRefresh={onRefresh}
      />
    );

    expect(screen.getByText('AI Agent Chatbot')).toBeInTheDocument();
    expect(screen.getByText('openai/gpt-4o')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Refresh'));
    expect(onRefresh).toHaveBeenCalled();
  });

  it('InspectorModal displays interaction details and raw JSON', () => {
    const log = {
      id: 'call_test_123',
      agent_name: 'Travel Concierge',
      model: 'openai/gpt-4o',
      status: 'SUCCESS',
      latency_ms: 120,
      total_tokens: 45
    };
    const onClose = vi.fn();

    render(<InspectorModal log={log} onClose={onClose} />);

    expect(screen.getByText(/Interaction Trace: Travel Concierge/)).toBeInTheDocument();
    expect(screen.getAllByText(/call_test_123/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('SUCCESS')).toBeInTheDocument();
    expect(screen.getByText('120 ms')).toBeInTheDocument();

    fireEvent.click(screen.getByText('✕'));
    expect(onClose).toHaveBeenCalled();

    // Test Esc key down
    onClose.mockClear();
    fireEvent.keyDown(window, { key: 'Escape', code: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });

  it('CreateSkillModal submits custom skill parameters and closes on Escape', async () => {
    const onCreated = vi.fn().mockResolvedValue();
    const onClose = vi.fn();

    render(<CreateSkillModal isOpen={true} onClose={onClose} onCreated={onCreated} />);

    // Test Esc key
    fireEvent.keyDown(window, { key: 'Escape', code: 'Escape' });
    expect(onClose).toHaveBeenCalled();

    fireEvent.change(screen.getByPlaceholderText('fitness_coach_skill'), {
      target: { value: 'fitness_coach_skill' }
    });
    fireEvent.change(screen.getByPlaceholderText('🏋️ Personal Fitness Coach'), {
      target: { value: '🏋️ Personal Fitness Coach' }
    });
    fireEvent.change(screen.getByPlaceholderText(/You are an energetic/), {
      target: { value: 'Fitness prompt' }
    });

    fireEvent.click(screen.getByText('✓ Register Custom Skill'));

    expect(onCreated).toHaveBeenCalledWith(expect.objectContaining({
      id: 'fitness_coach_skill',
      name: '🏋️ Personal Fitness Coach',
      system_prompt: 'Fitness prompt'
    }));
  });
});
