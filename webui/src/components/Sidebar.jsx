import React from 'react';
import { 
  MessageSquare, 
  Wrench, 
  Sparkles, 
  FolderGit2, 
  Activity, 
  FileText, 
  Award, 
  Settings 
} from 'lucide-react';

const TABS = [
  { id: 'chat', label: 'AI Agent Chatbot', icon: MessageSquare },
  { id: 'tools', label: 'MCP Tools & Sandbox', icon: Wrench },
  { id: 'skills', label: 'Domain Skills Hub', icon: Sparkles },
  { id: 'workspace', label: 'Workspace Files', icon: FolderGit2 },
  { id: 'overview', label: 'Telemetry & Metrics', icon: Activity },
  { id: 'logs', label: 'Audit Logs', icon: FileText },
  { id: 'evals', label: 'Evals & Benchmarks', icon: Award },
  { id: 'settings', label: 'Settings & Providers', icon: Settings },
];

export default function Sidebar({ activeTab, onSelectTab, health }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-icon">⚡</div>
        <div className="brand-text">
          <h2>Agentic AI</h2>
          <span>React Studio</span>
        </div>
      </div>

      <nav className="nav-links">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              className={`nav-btn ${isActive ? 'active' : ''}`}
              onClick={() => onSelectTab(tab.id)}
            >
              <Icon size={18} />
              <span>{tab.label}</span>
            </button>
          );
        })}
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
