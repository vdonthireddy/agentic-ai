import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Sidebar from '../components/Sidebar';
import TopHeader from '../components/TopHeader';
import InspectorModal from '../components/InspectorModal';
import CreateSkillModal from '../components/CreateSkillModal';

import HITLApprovalModal from '../components/HITLApprovalModal';
import ArtifactPanel from '../components/ArtifactPanel';
import EvalTraceModal from '../components/EvalTraceModal';

describe('React WebUI Components Unit Tests', () => {
  it('Sidebar renders all 10 Studio tabs and handles tab selection', () => {
    const onSelectTab = vi.fn();
    render(<Sidebar activeTab="chat" onSelectTab={onSelectTab} health={{}} />);

    expect(screen.getByText('AI Agent Chatbot')).toBeInTheDocument();
    expect(screen.getByText('Safety Approvals (HITL)')).toBeInTheDocument();
    expect(screen.getByText('MCP Tools & Sandbox')).toBeInTheDocument();
    expect(screen.getByText('Domain Skills Hub')).toBeInTheDocument();
    expect(screen.getByText('Workspace Files')).toBeInTheDocument();
    expect(screen.getByText('Telemetry & Metrics')).toBeInTheDocument();
    expect(screen.getByText('Audit Logs')).toBeInTheDocument();
    expect(screen.getByText('Evals & Benchmarks')).toBeInTheDocument();
    expect(screen.getByText('Multi-Agent Orchestrator')).toBeInTheDocument();
    expect(screen.getByText('Memory Explorer')).toBeInTheDocument();
    expect(screen.getByText('Settings & Providers')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Safety Approvals (HITL)'));
    expect(onSelectTab).toHaveBeenCalledWith('approvals');
  });

  it('HITLApprovalModal renders risk badges, arguments, and triggers callbacks', () => {
    const onApprove = vi.fn();
    const onDeny = vi.fn();
    const onClose = vi.fn();
    const request = {
      request_id: 'hitl_test_123',
      tool_name: 'workspace_file_ops',
      arguments: { action: 'delete', filename: 'secret.txt' },
      risk_level: 'high',
      description: 'Deleting secret.txt requires human approval.',
      timeout_seconds: 60
    };

    render(
      <HITLApprovalModal
        request={request}
        pendingCount={8}
        onApprove={onApprove}
        onDeny={onDeny}
        onClose={onClose}
      />
    );

    expect(screen.getByText('Safety Approval Required')).toBeInTheDocument();
    expect(screen.getByText('1 of 8')).toBeInTheDocument();
    expect(screen.getByText('HIGH RISK')).toBeInTheDocument();
    expect(screen.getByText('workspace_file_ops')).toBeInTheDocument();
    expect(screen.getByText(/Deleting secret.txt requires human approval/)).toBeInTheDocument();

    fireEvent.click(screen.getByText('✓ Approve'));
    expect(onApprove).toHaveBeenCalledWith('hitl_test_123');

    fireEvent.click(screen.getByText('✕ Deny'));
    expect(onDeny).toHaveBeenCalledWith('hitl_test_123');

    const closeBtn = screen.getByText('Close');
    expect(closeBtn).toBeInTheDocument();
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalled();

    const dismissBtn = screen.getByLabelText('Close');
    expect(dismissBtn).toBeInTheDocument();
    fireEvent.click(dismissBtn);
    expect(onClose).toHaveBeenCalledTimes(2);

    // Test Esc key triggers onClose
    fireEvent.keyDown(window, { key: 'Escape', code: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(3);
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

  it('TopHeader displays glowing approval required button when pendingHITL is active', () => {
    const onOpenModal = vi.fn();
    const pendingHITL = { request_id: 'hitl_999', tool_name: 'workspace_file_ops' };

    render(
      <TopHeader
        activeTab="canvas"
        activeModel="openai/gpt-4o"
        onRefresh={() => {}}
        pendingHITL={pendingHITL}
        pendingCount={8}
        onOpenHITLModal={onOpenModal}
      />
    );

    const alertBtn = screen.getByTitle(/Action requires human approval/i);
    expect(alertBtn).toBeInTheDocument();
    expect(screen.getByText('🛡️ Approval Required')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();

    fireEvent.click(alertBtn);
    expect(onOpenModal).toHaveBeenCalled();
  });

  it('Sidebar displays notification badges when hasPendingHITL is true', () => {
    render(
      <Sidebar
        activeTab="canvas"
        onSelectTab={() => {}}
        health={{}}
        hasPendingHITL={true}
      />
    );

    const badges = screen.getAllByTitle('Approval Required');
    expect(badges.length).toBeGreaterThanOrEqual(1);
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

  it('ArtifactPanel renders content and closes on Escape key', () => {
    const onClose = vi.fn();
    const artifact = {
      title: 'Sales Chart',
      type: 'html',
      content: '<div>Interactive Report</div>'
    };

    render(<ArtifactPanel artifact={artifact} onClose={onClose} />);

    expect(screen.getByText('Sales Chart')).toBeInTheDocument();
    expect(screen.getByText('HTML')).toBeInTheDocument();

    fireEvent.keyDown(window, { key: 'Escape', code: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });

  it('EvalTraceModal renders deep evals inspector and closes on Escape key', () => {
    const onClose = vi.fn();
    const testCase = {
      id: 'tc_101',
      name: 'Math Verification Test',
      passed: true,
      overall_score: 0.95
    };

    render(<EvalTraceModal testCase={testCase} modelName="gpt-4o" onClose={onClose} />);

    expect(screen.getByText(/Deep Evals Inspector: Math Verification Test/)).toBeInTheDocument();

    fireEvent.keyDown(window, { key: 'Escape', code: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });
});
