import React from 'react';
import { 
  MessageSquare, 
  Wrench, 
  Sparkles, 
  FolderGit2, 
  Activity, 
  FileText, 
  Award, 
  Settings,
  Users,
  Brain,
  GitFork,
  ShieldAlert,
  GitBranch
} from 'lucide-react';

export const NAV_SECTIONS = [
  {
    title: '🤖 Agent Studios',
    items: [
      { id: 'chat', label: 'AI Agent Chatbot', icon: MessageSquare },
      { id: 'canvas', label: 'Workflow Canvas (DAG)', icon: GitFork },
      { id: 'orchestrator', label: 'Multi-Agent Orchestrator', icon: Users },
    ]
  },
  {
    title: '🧠 Knowledge & Capabilities',
    items: [
      { id: 'tools', label: 'MCP Tools & Sandbox', icon: Wrench },
      { id: 'skills', label: 'Domain Skills Hub', icon: Sparkles },
      { id: 'memory', label: 'Memory Explorer', icon: Brain },
      { id: 'workspace', label: 'Workspace Files', icon: FolderGit2 },
    ]
  },
  {
    title: '⚡ Routing & Engine',
    items: [
      { id: 'smart-router', label: 'Smart Router', icon: GitBranch },
    ]
  },
  {
    title: '📊 Observability & Safety',
    items: [
      { id: 'overview', label: 'Telemetry & Metrics', icon: Activity },
      { id: 'logs', label: 'Audit Logs', icon: FileText },
      { id: 'approvals', label: 'Safety Approvals (HITL)', icon: ShieldAlert },
      { id: 'evals', label: 'Evals & Benchmarks', icon: Award },
    ]
  },
  {
    title: '⚙️ System',
    items: [
      { id: 'settings', label: 'Settings & Providers', icon: Settings },
    ]
  }
];

export const TABS = NAV_SECTIONS.flatMap(section => section.items);

export default function Sidebar({ activeTab, onSelectTab, health, hasPendingHITL, pendingCount }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-icon">
          <img src="/favicon.svg" alt="⚡" className="brand-logo-img" />
        </div>
        <div className="brand-text">
          <h2>Agentic AI</h2>
          <span>React Studio</span>
        </div>
      </div>

      <nav className="nav-links">
        {NAV_SECTIONS.map((section) => (
          <div key={section.title} className="nav-section">
            <div className="nav-section-title">{section.title}</div>
            <div className="nav-section-items">
              {section.items.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                const isApprovalsTab = tab.id === 'approvals';
                const showDot = hasPendingHITL && (tab.id === 'chat' || tab.id === 'canvas');
                const showApprovalsBadge = hasPendingHITL && isApprovalsTab;

                return (
                  <button
                    key={tab.id}
                    className={`nav-btn ${isActive ? 'active' : ''}`}
                    onClick={() => onSelectTab(tab.id)}
                    style={{ position: 'relative' }}
                  >
                    <Icon size={18} className={isApprovalsTab && hasPendingHITL ? 'text-rose-400' : ''} />
                    <span>{tab.label}</span>
                    {showApprovalsBadge && (
                      <span
                        style={{
                          marginLeft: 'auto',
                          background: '#ef4444',
                          color: '#fff',
                          borderRadius: '9999px',
                          padding: '1px 7px',
                          fontSize: '11px',
                          fontWeight: '700',
                          boxShadow: '0 0 10px rgba(239, 68, 68, 0.7)',
                          animation: 'pulse 1.5s infinite'
                        }}
                        title="Actions awaiting authorization"
                      >
                        {pendingCount || 1}
                      </span>
                    )}
                    {showDot && (
                      <span
                        style={{
                          marginLeft: 'auto',
                          width: '7px',
                          height: '7px',
                          background: '#ef4444',
                          borderRadius: '50%',
                          boxShadow: '0 0 6px rgba(239, 68, 68, 0.8)'
                        }}
                        title="Approval Required"
                      />
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="status-indicator">
          <span className="pulse-dot"></span>
          <span>Gateway Online</span>
        </div>
        <div className="meta-row">
          <span>Routing:</span>
          <strong>LiteLLM Multi-Provider</strong>
        </div>
      </div>
    </aside>
  );
}
