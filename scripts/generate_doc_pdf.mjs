import { chromium } from 'playwright';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '..');
const INDEX_HTML = path.join(ROOT_DIR, 'index.html');
const OUTPUT_HTML = path.join(ROOT_DIR, 'architecture_document.html');
const OUTPUT_PDF = path.join(ROOT_DIR, 'index.pdf');
const SPEC_SYMLINK = path.join(ROOT_DIR, 'agentic-ai-specification.pdf');

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function parseNodeDesc(desc) {
  if (!desc) return { whatItDoes: '', analogy: '', whyItHelps: '' };
  let whatItDoes = '';
  let analogy = '';
  let whyItHelps = '';
  const lines = desc.split('\n');
  let currentSection = 0;
  for (let line of lines) {
    line = line.trim();
    if (!line) continue;
    if (line.includes('1. What It Does')) {
      currentSection = 1;
      continue;
    } else if (line.includes('2. Why & How It Helps')) {
      currentSection = 2;
      continue;
    } else if (line.startsWith('──────') || line.startsWith('---')) {
      continue;
    }
    if (line.startsWith('│') || line.toLowerCase().startsWith('analogy:')) {
      const cleanAnalogy = line.replace(/^[│\s]+/, '').replace(/^analogy:\s*/i, '');
      analogy = analogy ? analogy + ' ' + cleanAnalogy : cleanAnalogy;
    } else if (currentSection === 1) {
      whatItDoes = whatItDoes ? whatItDoes + ' ' + line : line;
    } else if (currentSection === 2) {
      whyItHelps = whyItHelps ? whyItHelps + ' ' + line : line;
    }
  }
  return { whatItDoes, analogy, whyItHelps };
}

function createSlug(name) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

function buildDocumentHtml(rootNode) {
  const modules = rootNode.children || [];

  // Table of Contents
  let tocHtml = `
  <div class="toc-container">
    <div class="toc-title">Table of Contents · Architecture Modules</div>
    <div class="toc-grid">
  `;
  for (const mod of modules) {
    const slug = createSlug(mod.name);
    const subCount = mod.children ? mod.children.length : 0;
    tocHtml += `
      <a class="toc-item" href="#${slug}">
        <span class="toc-item-name">${escapeHtml(mod.name)}</span>
        <span class="toc-item-meta" style="color: ${mod.color || '#3b82f6'};">${subCount} Subsystems</span>
      </a>
    `;
  }
  tocHtml += `
    </div>
  </div>
  `;

  function renderNode(node, depth = 0, parentNode = null, parentColor = '#3b82f6') {
    const { whatItDoes, analogy, whyItHelps } = parseNodeDesc(node.desc);
    const color = node.color || parentColor;
    const slug = createSlug(node.name);
    const fileHtml = node.file ? `<span class="file-pill">📁 ${escapeHtml(node.file)}</span>` : '';

    let levelLabel = '';
    let headingTag = 'h5';
    let cardClass = 'feature-card';
    let entryClass = 'feature-entry';

    if (depth === 0) {
      levelLabel = '(Header 1)';
      headingTag = 'h1';
      cardClass = 'root-card';
      entryClass = 'root-entry';
    } else if (depth === 1) {
      levelLabel = 'Sub Header (of Header 1):';
      headingTag = 'h2';
      cardClass = 'module-card';
      entryClass = 'module-entry page-break';
    } else if (depth === 2) {
      levelLabel = parentNode ? `Sub Header (of ${parentNode.name}):` : 'Sub Header:';
      headingTag = 'h3';
      cardClass = 'subsystem-card';
      entryClass = 'subsystem-entry';
    } else if (depth === 3) {
      levelLabel = parentNode ? `Component (under ${parentNode.name}):` : 'Component:';
      headingTag = 'h4';
      cardClass = 'component-card';
      entryClass = 'component-entry';
    } else {
      levelLabel = 'Atomic Feature:';
      headingTag = 'h5';
      cardClass = 'feature-card';
      entryClass = 'feature-entry';
    }

    let html = `<div class="node-entry ${entryClass}" id="${slug}">`;
    html += `<div class="node-card ${cardClass}" style="--node-accent: ${color};">`;

    // Header label & file badge
    html += `<div class="header-meta-row">`;
    html += `<span class="level-label" style="color: ${color};">${levelLabel}</span>`;
    if (fileHtml) html += fileHtml;
    html += `</div>`;

    // Heading Title
    html += `<${headingTag} class="node-heading">${escapeHtml(node.name)}</${headingTag}>`;

    // Pillars
    html += `<div class="pillars-block">`;
    html += `<div class="pillar-header">1. What It Does (Plain English & Analogy)</div>`;
    if (whatItDoes) {
      html += `<p class="pillar-text">${escapeHtml(whatItDoes)}</p>`;
    }
    if (analogy) {
      html += `
        <div class="analogy-callout">
          <span class="analogy-icon">💡</span>
          <div class="analogy-content"><strong>Analogy:</strong> ${escapeHtml(analogy)}</div>
        </div>
      `;
    }

    html += `<div class="pillar-header">2. Why & How It Helps (Value Proposition)</div>`;
    if (whyItHelps) {
      html += `<p class="pillar-text">${escapeHtml(whyItHelps)}</p>`;
    }
    html += `</div>`; // .pillars-block
    html += `</div>`; // .node-card

    // Children rendered outside .node-card so pagination flows naturally
    if (node.children && node.children.length > 0) {
      html += `<div class="children-container depth-${depth + 1}">`;
      for (const child of node.children) {
        html += renderNode(child, depth + 1, node, color);
      }
      html += `</div>`;
    }

    html += `</div>`; // .node-entry
    return html;
  }

  const rootParsed = parseNodeDesc(rootNode.desc);
  const rootColor = rootNode.color || '#3b82f6';

  let fullHtml = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>agentic-ai — Architecture & Feature Specification</title>
<style>
  @page {
    size: A4 portrait;
    margin: 18mm 16mm 20mm 16mm;
  }

  :root {
    --text-primary: #0f172a;
    --text-secondary: #334155;
    --text-muted: #64748b;
    --border-color: #e2e8f0;
    --bg-page: #ffffff;
    --bg-card: #f8fafc;
    --bg-highlight: #f1f5f9;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: var(--text-primary);
    background: var(--bg-page);
    line-height: 1.55;
    font-size: 11pt;
    -webkit-font-smoothing: antialiased;
    padding: 0;
  }

  /* Page breaks for top-level modules */
  .page-break {
    page-break-before: always;
    break-before: page;
    padding-top: 10px;
  }

  /* Node card styling - card breaks avoided, but container can flow */
  .node-card {
    page-break-inside: avoid;
    break-inside: avoid;
    background: #ffffff;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 12px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
  }

  .header-meta-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
    flex-wrap: wrap;
  }

  .level-label {
    font-size: 8.5pt;
    font-weight: 700;
    letter-spacing: 0.02em;
    text-transform: uppercase;
  }

  .file-pill {
    font-size: 8pt;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    color: var(--text-muted);
    padding: 2px 7px;
    border-radius: 4px;
  }

  /* Headings Hierarchy */
  h1.node-heading {
    font-size: 24pt;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -0.02em;
    margin-bottom: 12px;
  }

  h2.node-heading {
    font-size: 18pt;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -0.015em;
    margin-bottom: 10px;
    border-left: 5px solid var(--node-accent);
    padding-left: 10px;
  }

  h3.node-heading {
    font-size: 13.5pt;
    font-weight: 700;
    color: #1e293b;
    margin-bottom: 8px;
    border-left: 4px solid var(--node-accent);
    padding-left: 10px;
  }

  h4.node-heading {
    font-size: 11pt;
    font-weight: 700;
    color: #334155;
    margin-bottom: 6px;
    border-left: 3px solid var(--node-accent);
    padding-left: 8px;
  }

  h5.node-heading {
    font-size: 10pt;
    font-weight: 700;
    color: #475569;
    margin-bottom: 4px;
    border-left: 2px solid var(--node-accent);
    padding-left: 6px;
  }

  /* Depth Indentation */
  .children-container.depth-2 {
    margin-top: 8px;
  }
  .children-container.depth-3 {
    margin-left: 14px;
    border-left: 2px solid #e2e8f0;
    padding-left: 12px;
    margin-top: 6px;
  }
  .children-container.depth-4 {
    margin-left: 12px;
    border-left: 2px dashed #cbd5e1;
    padding-left: 10px;
    margin-top: 6px;
  }
  .children-container.depth-5 {
    margin-left: 10px;
    border-left: 1px dotted #cbd5e1;
    padding-left: 8px;
    margin-top: 4px;
  }

  /* Card Type Variations */
  .root-card {
    background: #ffffff;
    border: 2px solid #3b82f6;
    padding: 16px 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.08);
  }

  .module-card {
    background: #ffffff;
    border: 1.5px solid var(--node-accent);
    padding: 14px 18px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  }

  .subsystem-card {
    background: #ffffff;
    border: 1px solid var(--border-color);
    border-left: 4px solid var(--node-accent);
  }

  .component-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
  }

  .feature-card {
    background: #ffffff;
    border: 1px dashed var(--border-color);
    padding: 8px 12px;
  }

  /* Pillars styling */
  .pillars-block {
    margin-top: 6px;
  }

  .pillar-header {
    font-size: 9.5pt;
    font-weight: 700;
    color: #0f172a;
    margin-top: 8px;
    margin-bottom: 3px;
  }

  .pillar-text {
    font-size: 9.5pt;
    color: var(--text-secondary);
    line-height: 1.45;
    margin-bottom: 6px;
  }

  /* Analogy Box */
  .analogy-callout {
    display: flex;
    gap: 8px;
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-left: 3px solid #f59e0b;
    border-radius: 5px;
    padding: 6px 10px;
    margin: 5px 0 8px 0;
    font-size: 9pt;
    line-height: 1.4;
    color: #78350f;
  }

  .analogy-icon {
    font-size: 11pt;
    flex-shrink: 0;
    line-height: 1.2;
  }

  .analogy-content {
    flex: 1;
  }

  /* Table of Contents */
  .toc-container {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 14px 18px;
    margin: 16px 0 24px 0;
    page-break-inside: avoid;
    break-inside: avoid;
  }

  .toc-title {
    font-size: 11.5pt;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 10px;
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 6px;
  }

  .toc-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px 14px;
  }

  .toc-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    text-decoration: none;
    color: var(--text-secondary);
    font-size: 9pt;
    padding: 5px 8px;
    border-radius: 4px;
    background: #ffffff;
    border: 1px solid var(--border-color);
  }

  .toc-item-name {
    font-weight: 600;
  }

  .toc-item-meta {
    font-size: 8pt;
    font-weight: 600;
  }
</style>
</head>
<body>

<div class="cover-section">
  <div class="node-card root-card" style="--node-accent: ${rootColor};">
    <div class="header-meta-row">
      <span class="level-label" style="color: ${rootColor};">(Header 1)</span>
      <span class="file-pill">📁 ${escapeHtml(rootNode.file || '')}</span>
    </div>
    <h1 class="node-heading">${escapeHtml(rootNode.name)}:</h1>
    
    <div class="pillars-block">
      <div class="pillar-header">1. What It Does (Plain English & Analogy)</div>
      <p class="pillar-text">${escapeHtml(rootParsed.whatItDoes)}</p>
      <div class="analogy-callout">
        <span class="analogy-icon">💡</span>
        <div class="analogy-content"><strong>Analogy:</strong> ${escapeHtml(rootParsed.analogy)}</div>
      </div>

      <div class="pillar-header">2. Why & How It Helps (Value Proposition)</div>
      <p class="pillar-text">${escapeHtml(rootParsed.whyItHelps)}</p>
    </div>
  </div>

  ${tocHtml}
</div>

<!-- All Modules (Sub Header of Header 1) -->
`;

  for (const moduleNode of modules) {
    fullHtml += renderNode(moduleNode, 1, rootNode, moduleNode.color);
  }

  fullHtml += `
</body>
</html>
`;
  return fullHtml;
}

async function run() {
  console.log('🚀 Generating structured Architecture Specification PDF from index.html data...');

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  console.log(`📄 Loading RAW_DATA from ${INDEX_HTML}...`);
  await page.goto(`file://${INDEX_HTML}`, { waitUntil: 'networkidle' });
  const rawData = await page.evaluate(() => RAW_DATA);

  console.log(`🔨 Building structured HTML documentation...`);
  const docHtml = buildDocumentHtml(rawData);
  fs.writeFileSync(OUTPUT_HTML, docHtml, 'utf8');
  console.log(`💾 Saved intermediate document HTML to ${OUTPUT_HTML} (${(docHtml.length / 1024).toFixed(0)} KB)`);

  console.log(`🖨️ Rendering to PDF via Playwright...`);
  await page.setContent(docHtml, { waitUntil: 'load' });
  await page.emulateMedia({ media: 'print' });

  // Generate the formatted PDF document
  await page.pdf({
    path: OUTPUT_PDF,
    format: 'A4',
    margin: {
      top: '18mm',
      bottom: '20mm',
      left: '16mm',
      right: '16mm'
    },
    displayHeaderFooter: true,
    headerTemplate: `
      <div style="font-family: -apple-system, sans-serif; font-size: 8pt; color: #94a3b8; width: 100%; padding: 0 16mm; display: flex; justify-content: space-between;">
        <span>🧠 agentic-ai — Architecture & Feature Specification</span>
        <span>503 Atomic Features · 8 Modules</span>
      </div>
    `,
    footerTemplate: `
      <div style="font-family: -apple-system, sans-serif; font-size: 8pt; color: #94a3b8; width: 100%; padding: 0 16mm; display: flex; justify-content: space-between;">
        <span>Autonomous Agent Platform & Enterprise AI Hub</span>
        <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
      </div>
    `,
    printBackground: true
  });

  // Create symlink for alternative document name if not exists
  if (fs.existsSync(SPEC_SYMLINK)) fs.unlinkSync(SPEC_SYMLINK);
  try {
    fs.symlinkSync('index.pdf', SPEC_SYMLINK);
  } catch (_) {}

  await browser.close();

  const stat = fs.statSync(OUTPUT_PDF);
  console.log(`✅ Success! Created ${OUTPUT_PDF} (${(stat.size / 1024 / 1024).toFixed(2)} MB)`);
}

run().catch(err => {
  console.error('❌ Generation error:', err);
  process.exit(1);
});
