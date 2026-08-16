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

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [models, setModels] = useState([]);
  const [skills, setSkills] = useState([]);
  const [stats, setStats] = useState({});
  const [logs, setLogs] = useState([]);
  const [health, setHealth] = useState(null);
  const [activeSkill, setActiveSkill] = useState('');

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
          activeModel={models[0]?.id || 'ollama/qwen2.5-coder:7b'}
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

          {activeTab === 'logs' && <AuditLogsView logs={logs} models={models} />}

          {activeTab === 'evals' && (
            <EvalsView
              models={models}
              activeModel={models[0]?.id}
            />
          )}

          {activeTab === 'settings' && (
            <SettingsView onRefreshAll={refreshData} />
          )}
        </div>
      </main>
    </div>
  );
}
