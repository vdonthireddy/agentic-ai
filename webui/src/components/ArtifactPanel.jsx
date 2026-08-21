import React, { useState } from 'react';
import { 
  X, Code, Eye, Download, Copy, Check, BarChart3, FileText, 
  Sparkles, ExternalLink, RefreshCw, Layers 
} from 'lucide-react';

export default function ArtifactPanel({ artifact, onClose }) {
  const [activeTab, setActiveTab] = useState('preview');
  const [copied, setCopied] = useState(false);

  if (!artifact) return null;

  const { title, type, content, plotlySpec, language = 'javascript' } = artifact;

  const handleCopy = () => {
    navigator.clipboard.writeText(typeof content === 'string' ? content : JSON.stringify(content, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([typeof content === 'string' ? content : JSON.stringify(content, null, 2)], {
      type: 'text/plain;charset=utf-8'
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${(title || 'artifact').toLowerCase().replace(/\s+/g, '_')}.${type === 'html' ? 'html' : type === 'json' ? 'json' : 'txt'}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="artifact-panel animate-slide-in">
      {/* Header */}
      <div className="artifact-header">
        <div className="artifact-title-group">
          <div className="artifact-badge">
            {type === 'plotly' ? <BarChart3 size={14} /> : type === 'html' ? <Eye size={14} /> : <Code size={14} />}
            <span>{type ? type.toUpperCase() : 'ARTIFACT'}</span>
          </div>
          <h3 className="artifact-title">{title || 'Interactive Artifact'}</h3>
        </div>

        <div className="artifact-actions">
          <button 
            className="action-btn"
            onClick={handleCopy}
            title="Copy Content"
          >
            {copied ? <Check size={16} className="text-emerald-400" /> : <Copy size={16} />}
          </button>
          <button 
            className="action-btn"
            onClick={handleDownload}
            title="Download Artifact"
          >
            <Download size={16} />
          </button>
          <button 
            className="action-btn close-btn"
            onClick={onClose}
            title="Close Panel"
          >
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="artifact-nav-tabs">
        <button 
          className={`artifact-nav-btn ${activeTab === 'preview' ? 'active' : ''}`}
          onClick={() => setActiveTab('preview')}
        >
          <Eye size={14} /> Preview
        </button>
        <button 
          className={`artifact-nav-btn ${activeTab === 'code' ? 'active' : ''}`}
          onClick={() => setActiveTab('code')}
        >
          <Code size={14} /> Source Code
        </button>
      </div>

      {/* Body Content */}
      <div className="artifact-body">
        {activeTab === 'preview' ? (
          type === 'html' ? (
            <iframe 
              srcDoc={content}
              title={title}
              className="artifact-iframe"
              sandbox="allow-scripts allow-modals"
            />
          ) : type === 'plotly' && plotlySpec ? (
            <div className="artifact-chart-wrapper">
              <div className="chart-info-banner">
                <BarChart3 size={16} className="text-indigo-400" />
                <span>Interactive Plotly Spec: {plotlySpec.data?.length || 0} series rendered</span>
              </div>
              <div className="chart-preview-card">
                <pre className="plotly-json-preview">
                  {JSON.stringify(plotlySpec, null, 2)}
                </pre>
              </div>
            </div>
          ) : (
            <div className="artifact-doc-preview">
              <div className="doc-content">
                {content}
              </div>
            </div>
          )
        ) : (
          <div className="artifact-code-view">
            <pre className="code-block">
              <code>{typeof content === 'string' ? content : JSON.stringify(content, null, 2)}</code>
            </pre>
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="artifact-footer">
        <div className="footer-meta">
          <Sparkles size={13} className="text-indigo-400" />
          <span>Rendered by Agentic AI Platform Studio • Real-Time Interactive Canvas</span>
        </div>
      </div>
    </div>
  );
}
