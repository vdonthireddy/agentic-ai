import React, { useState, useEffect } from 'react';
import { api } from './api/client';
import Sidebar from './components/Sidebar';
import TopHeader from './components/TopHeader';

import ChatView from './views/ChatView';
import ToolsView from './views/ToolsView';
import SkillsView from './views/SkillsView';
import WorkspaceView from './views/WorkspaceView';
import TelemetryView from './views/TelemetryView';
import AuditLogsView from './views/AuditLogsView';
import EvalsView from './views/EvalsView';
import SettingsView from './views/SettingsView';
import OrchestratorView from './views/OrchestratorView';
import MemoryView from './views/MemoryView';

const VALID_TABS = ['chat', 'tools', 'skills', 'workspace', 'overview', 'logs', 'evals', 'settings', 'orchestrator', 'memory'];

function getTabFromPath() {
  if (typeof window === 'undefined') return 'chat';
  const path = window.location.pathname.replace(/^\/+|\/+$/g, '').toLowerCase();
  if (path === '' || path === 'dashboard' || path === 'chat') return 'chat';
  if (path === 'telemetry') return 'overview';
  if (VALID_TABS.includes(path)) return path;
  return 'chat';
}

export default function App() {
  const [activeTab, setActiveTabState] = useState(getTabFromPath);
  const [models, setModels] = useState([]);
  const [skills, setSkills] = useState([]);
  const [stats, setStats] = useState({});
  const [logs, setLogs] = useState([]);
  const [health, setHealth] = useState(null);
  const [activeSkill, setActiveSkill] = useState('');
  const [logsSearchFilter, setLogsSearchFilter] = useState('');

  const handleNavigateToLogs = (searchQuery) => {
    setLogsSearchFilter(searchQuery || '');
    setActiveTab('logs');
  };

  const setActiveTab = (tabId, pushHistory = true) => {
    setActiveTabState(tabId);
    if (typeof window !== 'undefined') {
      window.scrollTo(0, 0);
      const contentPane = document.querySelector('.content-pane');
      if (contentPane) contentPane.scrollTop = 0;
    }
    if (pushHistory && typeof window !== 'undefined') {
      const newPath = tabId === 'chat' ? '/' : `/${tabId}`;
      if (window.location.pathname !== newPath) {
        window.history.pushState({ tab: tabId }, '', newPath);
      }
    }
  };

  useEffect(() => {
    const onPopState = () => {
      const tab = getTabFromPath();
      setActiveTabState(tab);
    };
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  const refreshData = async () => {
    try {
      const [mRes, sRes, stRes, lRes, hRes] = await Promise.all([
        api.getModels().catch(() => ({ data: [] })),
        api.getSkills().catch(() => ({ skills: [] })),
        api.getStats().catch(() => ({})),
        api.getLogs().catch(() => ({ logs: [] })),
        api.getHealth().catch(() => ({}))
      ]);

      setModels(mRes.data || []);
      setSkills(sRes.skills || []);
      setStats(stRes || {});
      setLogs(lRes.logs || []);
      setHealth(hRes || {});
    } catch (err) {
      console.error('Failed to refresh data', err);
    }
  };

  useEffect(() => {
    refreshData();
  }, [activeTab]);

  const handleActivateSkillInChat = (skillId) => {
    setActiveSkill(skillId);
    setActiveTab('chat');
  };

  return (
    <div className="app-container">
      <Sidebar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        health={health}
      />

      <main className="main-content">
        <TopHeader
          activeTab={activeTab}
          activeModel={models[0]?.id || 'ollama/gemma2:2b'}
          onRefresh={refreshData}
        />

        <div className="content-pane">
          {activeTab === 'chat' && (
            <ChatView
              models={models}
              skills={skills}
              activeSkill={activeSkill}
              onSelectSkill={setActiveSkill}
              onChatFinished={refreshData}
            />
          )}

          {activeTab === 'tools' && <ToolsView />}

          {activeTab === 'skills' && (
            <SkillsView
              skills={skills}
              onRefresh={refreshData}
              onActivateSkill={handleActivateSkillInChat}
            />
          )}

          {activeTab === 'workspace' && <WorkspaceView />}

          {activeTab === 'overview' && <TelemetryView stats={stats} />}

          {activeTab === 'logs' && <AuditLogsView logs={logs} models={models} initialSearch={logsSearchFilter} />}

          {activeTab === 'evals' && (
            <EvalsView
              models={models}
              activeModel={models[0]?.id}
              onNavigateToLogs={handleNavigateToLogs}
            />
          )}

          {activeTab === 'settings' && (
            <SettingsView onRefreshAll={refreshData} />
          )}

          {activeTab === 'orchestrator' && (
            <OrchestratorView models={models} />
          )}

          {activeTab === 'memory' && (
            <MemoryView />
          )}
        </div>
      </main>
    </div>
  );
}
