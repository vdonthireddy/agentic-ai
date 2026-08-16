import React, { useState, useEffect } from 'react';

export default function CreateSkillModal({ isOpen, onClose, onCreated }) {
  const [id, setId] = useState('');
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose?.();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!id.trim() || !name.trim() || !prompt.trim()) {
      alert('Please fill out Skill Identifier, Name, and Persona Prompt.');
      return;
    }

    setLoading(true);
    try {
      await onCreated({
        id: id.trim(),
        name: name.trim(),
        description: desc.trim(),
        system_prompt: prompt.trim(),
        category: 'Custom User Skills'
      });
      setId('');
      setName('');
      setDesc('');
      setPrompt('');
      onClose();
    } catch (err) {
      alert('Failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header flex-between">
          <h3>➕ Create New Domain Skill</h3>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit} className="modal-body">
          <div className="form-group mb-3">
            <label>Skill Identifier (e.g. fitness_coach_skill)</label>
            <input
              type="text"
              className="form-control"
              placeholder="fitness_coach_skill"
              value={id}
              onChange={(e) => setId(e.target.value)}
              required
            />
          </div>
          <div className="form-group mb-3">
            <label>Skill Name & Icon (e.g. 🏋️ Personal Fitness Coach)</label>
            <input
              type="text"
              className="form-control"
              placeholder="🏋️ Personal Fitness Coach"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
          <div className="form-group mb-3">
            <label>Description</label>
            <input
              type="text"
              className="form-control"
              placeholder="Designs tailored workout routines, calculates macro splits, and tracks progress."
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
            />
          </div>
          <div className="form-group mb-3">
            <label>System Instructions / Persona Prompt</label>
            <textarea
              className="form-control"
              rows="5"
              placeholder="You are an energetic, certified personal fitness coach. Always calculate calorie requirements and break down workout splits clearly..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              required
            ></textarea>
          </div>
          <button type="submit" className="btn btn-primary w-full mt-3" disabled={loading}>
            <span>{loading ? 'Creating...' : '✓ Register Custom Skill'}</span>
          </button>
        </form>
      </div>
    </div>
  );
}
