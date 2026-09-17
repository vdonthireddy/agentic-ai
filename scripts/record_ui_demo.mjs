#!/usr/bin/env node
/**
 * ==============================================================================
 * 🎬 Agentic-AI: Cinematic Live UI Walkthrough & Video Recorder
 * ==============================================================================
 * Automates an interactive, beautifully choreographed browser walkthrough across
 * all 13 Studio Tabs using Playwright, while recording full HD video (.webm).
 *
 * Usage:
 *   node scripts/record_ui_demo.mjs [--headed] [--headless] [--output <path>]
 * ==============================================================================
 */

import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '..');
const BASE_URL = process.env.GATEWAY_URL || 'http://localhost:8000';
const RECORDINGS_DIR = path.join(ROOT_DIR, 'recordings');

// Parse CLI flags
const args = process.argv.slice(2);
const isHeadless = args.includes('--headless') || (!args.includes('--headed') && !process.env.DISPLAY && process.platform !== 'darwin');
const customOutputArg = args.indexOf('--output') !== -1 ? args[args.indexOf('--output') + 1] : null;

// Ensure recordings directory exists
if (!fs.existsSync(RECORDINGS_DIR)) {
  fs.mkdirSync(RECORDINGS_DIR, { recursive: true });
}

// Temporary directory for Playwright video capture
const tempVideoDir = path.join(RECORDINGS_DIR, `.temp_${Date.now()}`);
fs.mkdirSync(tempVideoDir, { recursive: true });

// Styling colors
const CYAN = '\x1b[36m';
const GREEN = '\x1b[32m';
const YELLOW = '\x1b[33m';
const MAGENTA = '\x1b[35m';
const PURPLE = '\x1b[35m';
const BLUE = '\x1b[34m';
const BOLD = '\x1b[1m';
const RESET = '\x1b[0m';

console.log(`${CYAN}${BOLD}`);
console.log('==========================================================================');
console.log('  🎥 AGENTIC-AI : CINEMATIC LIVE UI DEMO & VIDEO RECORDER');
console.log(`  Mode: ${isHeadless ? 'Headless Video Capture' : 'Headed Live Window & Video Capture'}`);
console.log(`  Target: ${BASE_URL} (All 13 Studio Tabs)`);
console.log('==========================================================================');
console.log(RESET);

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Helper to inject a floating on-screen watermark HUD into the web page
async function showHudBanner(page, stepNum, totalSteps, title, subtitle) {
  await page.evaluate(({ stepNum, totalSteps, title, subtitle }) => {
    let hud = document.getElementById('demo-hud-watermark');
    if (!hud) {
      hud = document.createElement('div');
      hud.id = 'demo-hud-watermark';
      hud.style.position = 'fixed';
      hud.style.bottom = '24px';
      hud.style.right = '24px';
      hud.style.zIndex = '999999';
      hud.style.backgroundColor = 'rgba(15, 23, 42, 0.92)';
      hud.style.backdropFilter = 'blur(12px)';
      hud.style.border = '1px solid rgba(56, 189, 248, 0.4)';
      hud.style.borderRadius = '12px';
      hud.style.padding = '14px 20px';
      hud.style.boxShadow = '0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 0 15px rgba(56, 189, 248, 0.2)';
      hud.style.color = '#fff';
      hud.style.fontFamily = 'Inter, -apple-system, sans-serif';
      hud.style.pointerEvents = 'none';
      hud.style.transition = 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)';
      hud.style.maxWidth = '460px';
      document.body.appendChild(hud);
    }
    hud.innerHTML = `
      <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
        <span style="background: linear-gradient(135deg, #0284c7, #38bdf8); color: #fff; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.5px;">
          Act ${stepNum} of ${totalSteps}
        </span>
        <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">${title}</span>
      </div>
      <div style="font-size: 12px; color: #94a3b8; line-height: 1.4;">${subtitle}</div>
    `;
  }, { stepNum, totalSteps, title, subtitle });
}

async function runDemo() {
  const browser = await chromium.launch({
    headless: isHeadless,
    slowMo: 40
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: {
      dir: tempVideoDir,
      size: { width: 1440, height: 900 }
    }
  });

  const page = await context.newPage();

  const TOTAL_ACTS = 13;

  try {
    // --------------------------------------------------------------------------
    // ACT 1: AI Agent Chatbot Studio
    // --------------------------------------------------------------------------
    console.log(`${MAGENTA}[Act 1/13] 💬 Demonstrating AI Agent Chatbot Studio...${RESET}`);
    await page.goto(`${BASE_URL}/chat`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);
    await showHudBanner(page, 1, TOTAL_ACTS, 'AI Agent Chatbot Studio', 'ReAct reasoning loop, tool badges, artifact preview, and prompt chips.');
    
    // Highlight Model Selectors
    const modelSelect = page.locator('select').first();
    if (await modelSelect.count() > 0) {
      await modelSelect.click();
      await page.waitForTimeout(600);
      await page.keyboard.press('Escape');
    }

    // Type a sample prompt
    const chatInput = page.locator('textarea, input[type="text"]').last();
    if (await chatInput.count() > 0) {
      await chatInput.focus();
      await chatInput.fill('Calculate an 18% tip on a $184.50 dinner split among 4 people, and check live weather in Paris.');
      await page.waitForTimeout(1200);
    }
    await page.waitForTimeout(1500);

    // --------------------------------------------------------------------------
    // ACT 2: Workflow Canvas (DAG)
    // --------------------------------------------------------------------------
    console.log(`${BLUE}[Act 2/13] 🔲 Demonstrating Workflow Canvas (DAG)...${RESET}`);
    await page.goto(`${BASE_URL}/canvas`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);
    await showHudBanner(page, 2, TOTAL_ACTS, 'Workflow Canvas (DAG)', 'Visual 2D drag-and-drop board, Kahn topological sorting, and durable checkpoints.');
    
    // Click on template to load nodes
    const swarmBtn = page.locator('button.template-pill-btn:has-text("1-to-3 Parallel Swarm Fork"), button:has-text("Parallel Swarm")').first();
    if (await swarmBtn.count() > 0) {
      await swarmBtn.click();
      await page.waitForTimeout(1000);
    }
    await page.waitForTimeout(1800);

    // --------------------------------------------------------------------------
    // ACT 3: Multi-Agent Orchestrator
    // --------------------------------------------------------------------------
    console.log(`${CYAN}[Act 3/13] 🌐 Demonstrating Multi-Agent Orchestrator...${RESET}`);
    await page.goto(`${BASE_URL}/orchestrator`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);
    await showHudBanner(page, 3, TOTAL_ACTS, 'Multi-Agent Orchestrator', 'Supervisor task decomposition and 3-agent adversarial Red-Team Debate.');
    
    const debateTab = page.locator('button:has-text("Multi-Agent Debate"), button:has-text("Debate")').first();
    if (await debateTab.count() > 0) {
      await debateTab.click();
      await page.waitForTimeout(1000);
    }
    await page.waitForTimeout(1600);

    // --------------------------------------------------------------------------
    // ACT 4: FastMCP Tools & Sandbox
    // --------------------------------------------------------------------------
    console.log(`${YELLOW}[Act 4/13] 🔧 Demonstrating 23 FastMCP Tools Sandbox...${RESET}`);
    await page.goto(`${BASE_URL}/tools`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);
    await showHudBanner(page, 4, TOTAL_ACTS, '23 FastMCP Tools Sandbox', 'Math, Jailed Files, DuckDuckGo Search, Weather, Product Catalog, Python AST, and SQL.');
    
    // Click on a tool card
    const toolCard = page.locator('button:has-text("Load"), .tool-card, .list-item').first();
    if (await toolCard.count() > 0) {
      await toolCard.click();
      await page.waitForTimeout(800);
    }
    await page.waitForTimeout(1600);

    // --------------------------------------------------------------------------
    // ACT 5: Domain Skills Hub
    // --------------------------------------------------------------------------
    console.log(`${GREEN}[Act 5/13] 🎭 Demonstrating Domain Skills Hub...${RESET}`);
    await page.goto(`${BASE_URL}/skills`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);
    await showHudBanner(page, 5, TOTAL_ACTS, 'Domain Skills Hub', 'Progressive skill disclosure (85% token savings) and 10 expert personas.');
    
    const skillCards = page.locator('.skill-card');
    if (await skillCards.count() > 0) {
      await skillCards.first().hover();
      await page.waitForTimeout(800);
    }
    await page.waitForTimeout(1600);

    // --------------------------------------------------------------------------
    // ACT 6: Memory Explorer
    // --------------------------------------------------------------------------
    console.log(`${PURPLE}[Act 6/13] 🧠 Demonstrating Dual Memory Explorer...${RESET}`);
    await page.goto(`${BASE_URL}/memory`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);
    await showHudBanner(page, 6, TOTAL_ACTS, 'Dual Memory Explorer', 'Semantic Vector Vault (ChromaDB/SQLite) and GraphRAG multi-hop relationship graph.');
    
    const graphTab = page.locator('button:has-text("GraphRAG"), button:has-text("Knowledge Graph")').first();
    if (await graphTab.count() > 0) {
      await graphTab.click();
      await page.waitForTimeout(1000);
    }
    await page.waitForTimeout(1600);

    // --------------------------------------------------------------------------
    // ACT 7: Workspace Files
    // --------------------------------------------------------------------------
    console.log(`${BLUE}[Act 7/13] 📁 Demonstrating Sandboxed Workspace Files...${RESET}`);
    await page.goto(`${BASE_URL}/workspace`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);
    await showHudBanner(page, 7, TOTAL_ACTS, 'Sandboxed Workspace', 'Jailed filesystem with traversal prevention and built-in code editor.');
    await page.waitForTimeout(1600);

    // --------------------------------------------------------------------------
    // ACT 8: 2-Stage Smart Router
    // --------------------------------------------------------------------------
    console.log(`${CYAN}[Act 8/13] ⚡ Demonstrating 2-Stage Smart Router...${RESET}`);
    await page.goto(`${BASE_URL}/smart-router`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);
    await showHudBanner(page, 8, TOTAL_ACTS, '2-Stage Smart Router', 'Intent classification across 5 categories, threshold tuning, and trace audit logs.');
    
    // Click a preset chip if available
    const chip = page.locator('button:has-text("Python"), button:has-text("Coding"), .chip').first();
    if (await chip.count() > 0) {
      await chip.click();
      await page.waitForTimeout(800);
    }
    await page.waitForTimeout(1600);

    // --------------------------------------------------------------------------
    // ACT 9: Telemetry & Metrics
    // --------------------------------------------------------------------------
    console.log(`${GREEN}[Act 9/13] 📈 Demonstrating Telemetry & Observability Metrics...${RESET}`);
    await page.goto(`${BASE_URL}/overview`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);
    await showHudBanner(page, 9, TOTAL_ACTS, 'Telemetry & Metrics', 'Real-time KPIs, token distribution charts, P50/P90/P99 latency, and spend forecast.');
    await page.mouse.wheel(0, 300);
    await page.waitForTimeout(1600);

    // --------------------------------------------------------------------------
    // ACT 10: 3-Tier Audit Logs
    // --------------------------------------------------------------------------
    console.log(`${YELLOW}[Act 10/13] 📋 Demonstrating 3-Tier Audit Logs...${RESET}`);
    await page.goto(`${BASE_URL}/logs`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);
    await showHudBanner(page, 10, TOTAL_ACTS, '3-Tier Audit Logs', 'Conversation ➔ Turn ➔ Request hierarchy with live SSE streaming and CSV/JSONL export.');
    await page.waitForTimeout(1600);

    // --------------------------------------------------------------------------
    // ACT 11: Safety Approvals (HITL)
    // --------------------------------------------------------------------------
    console.log(`${MAGENTA}[Act 11/13] 🛡️ Demonstrating Human-in-the-Loop Safety Approvals...${RESET}`);
    await page.goto(`${BASE_URL}/approvals`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);
    await showHudBanner(page, 11, TOTAL_ACTS, 'Human-in-the-Loop (HITL)', 'Critical risk gatekeeper with 60-second auto-deny timers and decision auditing.');
    await page.waitForTimeout(1600);

    // --------------------------------------------------------------------------
    // ACT 12: Evals & Benchmarks
    // --------------------------------------------------------------------------
    console.log(`${BLUE}[Act 12/13] 🧪 Demonstrating 9-Grader Evals & Benchmarks...${RESET}`);
    await page.goto(`${BASE_URL}/evals`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);
    await showHudBanner(page, 12, TOTAL_ACTS, '9-Grader Evals Framework', 'Deterministic, efficiency, LLM judge, safety, fact-checker, and 100% composite score.');
    await page.waitForTimeout(1600);

    // --------------------------------------------------------------------------
    // ACT 13: Settings & Multi-Provider System
    // --------------------------------------------------------------------------
    console.log(`${GREEN}[Act 13/13] ⚙️ Demonstrating Settings & Providers...${RESET}`);
    await page.goto(`${BASE_URL}/settings`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);
    await showHudBanner(page, 13, TOTAL_ACTS, 'Settings & Providers', 'Transport mode toggle, local Ollama detection, cloud API keys, and live system gauges.');
    await page.waitForTimeout(2000);

    console.log(`\n${GREEN}${BOLD}✨ Live UI Walkthrough completed successfully! Finalizing video recording...${RESET}\n`);

  } finally {
    // Closing context commits the recorded video
    await page.close();
    await context.close();
    await browser.close();
  }

  // Find the generated video file
  const videoFiles = fs.readdirSync(tempVideoDir).filter(f => f.endsWith('.webm'));
  if (videoFiles.length > 0) {
    const rawVideoPath = path.join(tempVideoDir, videoFiles[0]);
    const finalVideoName = customOutputArg || `agentic_ai_ui_demo_${new Date().toISOString().slice(0, 10)}.webm`;
    const finalVideoPath = path.isAbsolute(finalVideoName) ? finalVideoName : path.join(RECORDINGS_DIR, finalVideoName);

    fs.copyFileSync(rawVideoPath, finalVideoPath);
    fs.rmSync(tempVideoDir, { recursive: true, force: true });

    const stats = fs.statSync(finalVideoPath);
    const sizeMb = (stats.size / (1024 * 1024)).toFixed(2);

    console.log(`${CYAN}${BOLD}==========================================================================${RESET}`);
    console.log(`${GREEN}${BOLD}🎉 DEMO VIDEO RECORDED SUCCESSFULLY!${RESET}`);
    console.log(`  File:     ${BOLD}${finalVideoPath}${RESET}`);
    console.log(`  Size:     ${BOLD}${sizeMb} MB${RESET}`);
    console.log(`  Format:   WebM (1440x900 HD Video)`);
    console.log(`${CYAN}${BOLD}==========================================================================${RESET}`);
    console.log(`\n${YELLOW}To watch the video immediately on macOS:${RESET}`);
    console.log(`  ${BOLD}open "${finalVideoPath}"${RESET}  # Or drag into Chrome / VLC\n`);
  } else {
    console.warn('No video file produced by Playwright.');
  }
}

runDemo().catch(err => {
  console.error('Recording failed:', err);
  process.exit(1);
});
