import React, { useState } from 'react';
import { api } from '../api/client';
import { MessageSquare, Trash2, Plus } from 'lucide-react';
import CreateSkillModal from '../components/CreateSkillModal';

export default function SkillsView({ skills, onRefresh, onActivateSkill }) {
  const [modalOpen, setModalOpen] = useState(false);

  const handleCreate = async (skillData) => {
    await api.createCustomSkill(skillData);
    if (onRefresh) onRefresh();
  };

  const handleDelete = async (skillId) => {
    if (!confirm(`Delete custom skill '${skillId}'?`)) return;
    try {
      await api.deleteCustomSkill(skillId);
      if (onRefresh) onRefresh();
    } catch (e) {
      alert(e.message);
    }
  };

  return (
    <div>
      <div className="flex-between mb-6">
        <div>
          <h2>⚡ Domain Skills Hub & Persona Crafter</h2>
          <p className="text-muted">Explore, customize, and create specialized agent personas with custom prompt injections</p>
        </div>
        <button className="btn btn-primary btn-sm" onClick={() => setModalOpen(true)}>
          <Plus size={16} />
          <span>Create Custom Skill</span>
        </button>
      </div>

      <div className="skills-showcase-grid">
        {skills.map((s) => {
          const iconMatch = s.name.match(/^(\S+)/);
          const icon = iconMatch ? iconMatch[1] : '⚡';
          const cleanName = s.name.replace(/^(\S+)\s*/, '');

          return (
            <div key={s.id} className="skill-card">
              <div>
                <div className="skill-header">
                  <div className="skill-icon">{icon}</div>
                  <div className="skill-info">
                    <div className="skill-category">{s.category || 'Domain Skill'}</div>
                    <h3>{cleanName}</h3>
                  </div>
                </div>
                <div className="skill-desc">{s.description}</div>
                {s.recommended_tools && s.recommended_tools.length > 0 && (
                  <div className="skill-tools-tags">
                    {s.recommended_tools.map((t, idx) => (
                      <span key={idx} className="skill-tool-tag">
                        🛠️ {t}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div className="skill-actions">
                <button
                  className="btn btn-primary btn-sm w-full"
                  onClick={() => onActivateSkill(s.id)}
                >
                  <MessageSquare size={14} />
                  <span>Activate in Chat</span>
                </button>
                {s.is_custom && (
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => handleDelete(s.id)}
                    title="Delete custom skill"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <CreateSkillModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onCreated={handleCreate}
      />
    </div>
  );
}
