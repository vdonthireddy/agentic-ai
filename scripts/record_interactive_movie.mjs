#!/usr/bin/env node
/**
 * ==============================================================================
 * 🎬 Agentic-AI: Interactive Movie Recorder with Live Audio & Real Execution
 * ==============================================================================
 * Automates an interactive, choreographed browser demonstration across the platform:
 *  - Enters real values into inputs and executes actions (Chat, Canvas DAG, Tools,
 *    Smart Router, Memory, Orchestrator, etc.)
 *  - Waits for live results to arrive and visually highlights them on screen
 *  - Generates synchronized studio voiceover narration using macOS text-to-speech
 *  - Plays audio live through speakers during headed browser playback
 *  - Multiplexes video and master audio into high-definition .mp4 and .webm movies
 *
 * Usage:
 *   node scripts/record_interactive_movie.mjs [--headed] [--headless] [--output <filename>]
 * ==============================================================================
 */

import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { execSync, spawn } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '..');
const BASE_URL = process.env.GATEWAY_URL || 'http://localhost:8000';
const RECORDINGS_DIR = path.join(ROOT_DIR, 'recordings');

// CLI Flags
const args = process.argv.slice(2);
const isHeadless = args.includes('--headless') || (!args.includes('--headed') && !process.env.DISPLAY && process.platform !== 'darwin');
const customOutputArg = args.indexOf('--output') !== -1 ? args[args.indexOf('--output') + 1] : null;
const isMuted = args.includes('--mute') || args.includes('--no-audio');

// Ensure recordings directory exists
if (!fs.existsSync(RECORDINGS_DIR)) {
  fs.mkdirSync(RECORDINGS_DIR, { recursive: true });
}

// Temporary directories for raw captures
const timestamp = Date.now();
const tempVideoDir = path.join(RECORDINGS_DIR, `.temp_video_${timestamp}`);
const tempAudioDir = path.join(RECORDINGS_DIR, `.temp_audio_${timestamp}`);
fs.mkdirSync(tempVideoDir, { recursive: true });
fs.mkdirSync(tempAudioDir, { recursive: true });

// Styling Colors
const CYAN = '\x1b[36m';
const GREEN = '\x1b[32m';
const YELLOW = '\x1b[33m';
const MAGENTA = '\x1b[35m';
const PURPLE = '\x1b[35m';
const BLUE = '\x1b[34m';
const RED = '\x1b[31m';
const BOLD = '\x1b[1m';
const RESET = '\x1b[0m';

// Detect FFmpeg Binary
function getFfmpegPath() {
  if (process.env.FFMPEG_PATH && fs.existsSync(process.env.FFMPEG_PATH)) {
    return process.env.FFMPEG_PATH;
  }
  const venvFfmpeg = path.join(ROOT_DIR, '.venv/lib/python3.12/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1');
  if (fs.existsSync(venvFfmpeg)) {
    return venvFfmpeg;
  }
  try {
    const sysFfmpeg = execSync('which ffmpeg', { encoding: 'utf8' }).trim();
    if (sysFfmpeg && fs.existsSync(sysFfmpeg)) return sysFfmpeg;
  } catch (e) { /* ignore */ }
  return 'ffmpeg';
}

const FFMPEG_BIN = getFfmpegPath();

console.log(`${CYAN}${BOLD}`);
console.log('==========================================================================');
console.log('  🎬 AGENTIC-AI : INTERACTIVE MOVIE & AUDIO RECORDER');
console.log(`  Mode:        ${isHeadless ? 'Headless Video Capture' : 'Headed Live Window & Audio Narration'}`);
console.log(`  Target:      ${BASE_URL}`);
console.log(`  Audio:       macOS Speech Synthesis (Samantha) + FFmpeg Muxing`);
console.log(`  Output:      HD 1440x900 MP4 (H.264+AAC) & WebM (VP9+Opus)`);
console.log('==========================================================================');
console.log(RESET);

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Injects floating Director HUD banner
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
      hud.style.backgroundColor = 'rgba(15, 23, 42, 0.94)';
      hud.style.backdropFilter = 'blur(14px)';
      hud.style.border = '1px solid rgba(56, 189, 248, 0.45)';
      hud.style.borderRadius = '14px';
      hud.style.padding = '14px 22px';
      hud.style.boxShadow = '0 10px 30px -5px rgba(0, 0, 0, 0.6), 0 0 20px rgba(56, 189, 248, 0.25)';
      hud.style.color = '#fff';
      hud.style.fontFamily = 'Inter, -apple-system, sans-serif';
      hud.style.pointerEvents = 'none';
      hud.style.transition = 'all 0.35s cubic-bezier(0.16, 1, 0.3, 1)';
      hud.style.maxWidth = '480px';
      document.body.appendChild(hud);
    }
    hud.innerHTML = `
      <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
        <span style="background: linear-gradient(135deg, #0284c7, #38bdf8); color: #fff; font-size: 11px; font-weight: 700; padding: 2px 9px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.5px;">
          Act ${stepNum} of ${totalSteps}
        </span>
        <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">${title}</span>
      </div>
      <div style="font-size: 12px; color: #94a3b8; line-height: 1.4;">${subtitle}</div>
    `;
  }, { stepNum, totalSteps, title, subtitle });
}

// Generate narration audio and play live if headed
function generateAndPlayAudio(actIndex, narrationText, startTimeSec, audioSegments) {
  const aiffPath = path.join(tempAudioDir, `act_${actIndex}.aiff`);
  const wavPath = path.join(tempAudioDir, `act_${actIndex}.wav`);

  try {
    // Generate AIFF using macOS say
    execSync(`say -v Samantha "${narrationText.replace(/"/g, '\\"')}" -o "${aiffPath}"`);

    // Convert to standardized 44.1kHz Stereo WAV
    execSync(`"${FFMPEG_BIN}" -y -i "${aiffPath}" -ar 44100 -ac 2 "${wavPath}" 2>/dev/null`);

    audioSegments.push({
      startSec: startTimeSec,
      wavPath: wavPath
    });

    // If running headed on macOS, play out loud through speakers
    if (!isHeadless && !isMuted && process.platform === 'darwin') {
      spawn('afplay', [aiffPath], { stdio: 'ignore', detached: true });
    }
  } catch (err) {
    console.warn(`[Audio] Warning: Failed to generate audio for Act ${actIndex}:`, err.message);
  }
}

// Interactive Movie Flow
async function recordInteractiveMovie() {
  const browser = await chromium.launch({
    headless: isHeadless,
    slowMo: 30
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: {
      dir: tempVideoDir,
      size: { width: 1440, height: 900 }
    }
  });

  const page = await context.newPage();
  const TOTAL_ACTS = 12;
  const audioSegments = [];
  const recordingStartTime = Date.now();

  const getElapsedSec = () => (Date.now() - recordingStartTime) / 1000.0;

  try {
    // ==========================================================================
    // ACT 1: AI Agent Chatbot Studio (Enter Prompt -> Send -> Wait for Result)
    // ==========================================================================
    console.log(`${MAGENTA}[Act 1/12] 💬 Interactive AI Agent Chatbot Studio...${RESET}`);
    await page.goto(`${BASE_URL}/chat`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    const act1Start = getElapsedSec();
    const act1Narration = "Act One: AI Agent Chatbot Studio. We enter an everyday prompt asking the autonomous agent to calculate an eighteen percent tip on dinner for four people. Watch as the agent reasons, executes the math tool, and delivers a structured receipt.";
    generateAndPlayAudio(1, act1Narration, act1Start, audioSegments);
    await showHudBanner(page, 1, TOTAL_ACTS, 'AI Agent Chatbot Studio', 'Submitting live prompt, ReAct reasoning, and awaiting tool result.');

    const chatTextarea = page.locator('textarea').first();
    if (await chatTextarea.count() > 0) {
      await chatTextarea.click();
      await page.waitForTimeout(400);
      const promptText = 'Use calculator to calculate an 18% tip on a $184.50 dinner split among 4 people.';
      await chatTextarea.pressSequentially(promptText, { delay: 25 });
      await page.waitForTimeout(600);

      const sendBtn = page.locator('button.btn-primary:has-text("Send")').first();
      if (await sendBtn.count() > 0) {
        await sendBtn.click();
        console.log(`  ↳ Sent prompt to agent. Waiting for ReAct execution...`);

        // Wait for agent response to complete
        try {
          await page.waitForSelector('.chat-message.message-assistant, .chat-message.message-bot, .tool-call-feed', { timeout: 35000 });
          await page.waitForTimeout(2000);
        } catch (e) {
          console.warn('  ↳ Agent response wait timed out, continuing...');
        }
      }
    }
    await page.waitForTimeout(2500);

    // ==========================================================================
    // ACT 2: Visual Workflow Canvas (Load Template -> Run DAG -> Wait for Result)
    // ==========================================================================
    console.log(`${BLUE}[Act 2/12] 🔲 Interactive Visual Workflow Canvas (DAG)...${RESET}`);
    await page.goto(`${BASE_URL}/canvas`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    const act2Start = getElapsedSec();
    const act2Narration = "Act Two: Visual Workflow Canvas. We load the parallel swarm DAG pipeline, connecting reasoning and tool nodes, and trigger execution. Watch as topological scheduling runs each stage to completion.";
    generateAndPlayAudio(2, act2Narration, act2Start, audioSegments);
    await showHudBanner(page, 2, TOTAL_ACTS, 'Workflow Canvas (DAG)', 'Loading pre-built swarm pipeline and triggering topological DAG execution.');

    // Load Parallel Swarm template
    const templateBtn = page.locator('button.template-pill-btn:has-text("Parallel Swarm"), button:has-text("Parallel Swarm")').first();
    if (await templateBtn.count() > 0) {
      await templateBtn.click();
      await page.waitForTimeout(1200);
    }

    // Click Run Workflow DAG
    const runDagBtn = page.locator('button:has-text("Run Workflow DAG")').first();
    if (await runDagBtn.count() > 0) {
      await runDagBtn.click();
      console.log(`  ↳ Triggered DAG execution. Animating topological stages...`);

      // Wait for execution to finish
      try {
        await page.waitForSelector('.canvas-execution-report, .dag-execution-card', { timeout: 40000 });
        await page.waitForTimeout(1500);
      } catch (e) {
        console.warn('  ↳ DAG run wait timed out, continuing...');
      }
    }
    await page.waitForTimeout(2500);

    // ==========================================================================
    // ACT 3: FastMCP Tools Sandbox (Select Tool -> Enter JSON -> Execute -> View Output)
    // ==========================================================================
    console.log(`${YELLOW}[Act 3/12] 🔧 Interactive FastMCP Tools Sandbox...${RESET}`);
    await page.goto(`${BASE_URL}/tools`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    const act3Start = getElapsedSec();
    const act3Narration = "Act Three: FastMCP Tools Sandbox. We select the tip and split tool, input JSON arguments, and execute live in the sandbox to observe sub-millisecond execution latency.";
    generateAndPlayAudio(3, act3Narration, act3Start, audioSegments);
    await showHudBanner(page, 3, TOTAL_ACTS, 'FastMCP Tools Sandbox', 'Selecting tool, entering JSON arguments, and executing live in the sandbox.');

    const toolSelect = page.locator('select.form-control').first();
    if (await toolSelect.count() > 0) {
      // Choose calculate_tip_and_split if available, else calculator
      const options = await toolSelect.locator('option').allInnerTexts();
      const targetOption = options.find(o => o.includes('calculate_tip_and_split')) || options.find(o => o.includes('calculator'));
      if (targetOption) {
        const val = targetOption.split(' ')[0];
        await toolSelect.selectOption(val);
        await page.waitForTimeout(600);
      }
    }

    // Fill JSON arguments
    const argsBox = page.locator('textarea.form-control.code-font').first();
    if (await argsBox.count() > 0) {
      await argsBox.click();
      await argsBox.fill('{\n  "total": 184.50,\n  "tip_percentage": 18,\n  "split_count": 4\n}');
      await page.waitForTimeout(800);
    }

    // Click Execute Tool in Sandbox
    const executeBtn = page.locator('button:has-text("Execute Tool in Sandbox")').first();
    if (await executeBtn.count() > 0) {
      await executeBtn.click();
      console.log(`  ↳ Executed tool in sandbox. Awaiting JSON response...`);
      try {
        await page.waitForSelector('.json-code-box', { timeout: 10000 });
        await page.waitForTimeout(1200);
      } catch (e) { /* ignore */ }
    }
    await page.waitForTimeout(2500);

    // ==========================================================================
    // ACT 4: 2-Stage Smart Router (Enter Prompt -> Route & Execute -> View Result)
    // ==========================================================================
    console.log(`${CYAN}[Act 4/12] ⚡ Interactive 2-Stage Smart Router...${RESET}`);
    await page.goto(`${BASE_URL}/smart-router`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    const act4Start = getElapsedSec();
    const act4Narration = "Act Four: Two-Stage Smart Router. We submit an algorithmic coding task. Stage one classifies the intent with high confidence, routing execution directly to our local coder model.";
    generateAndPlayAudio(4, act4Narration, act4Start, audioSegments);
    await showHudBanner(page, 4, TOTAL_ACTS, '2-Stage Smart Router', 'Reasoning intent classification, applying thresholds, and dispatching to model tier.');

    const routerInput = page.locator('textarea').first();
    if (await routerInput.count() > 0) {
      await routerInput.click();
      const codeQuery = 'Write a Python function to invert a binary tree in O(n) time.';
      await routerInput.pressSequentially(codeQuery, { delay: 20 });
      await page.waitForTimeout(600);

      const routeBtn = page.locator('button:has-text("Route & Execute Prompt")').first();
      if (await routeBtn.count() > 0) {
        await routeBtn.click();
        console.log(`  ↳ Submitted routing request. Waiting for Stage 1 & Stage 2 results...`);
        try {
          await page.waitForSelector('text="2-Stage Dynamic Routing Trace", .routing-flow-card, button:has-text("Route & Execute Prompt"):not([disabled])', { timeout: 35000 });
          await page.waitForTimeout(1500);
        } catch (e) { /* ignore */ }
      }
    }
    await page.waitForTimeout(2500);

    // ==========================================================================
    // ACT 5: Dual Memory Explorer (Search Semantic Memory & GraphRAG)
    // ==========================================================================
    console.log(`${PURPLE}[Act 5/12] 🧠 Interactive Dual Memory Explorer...${RESET}`);
    await page.goto(`${BASE_URL}/memory`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    const act5Start = getElapsedSec();
    const act5Narration = "Act Five: Dual Memory Explorer. Combining semantic vector embeddings with GraphRAG relationships. We query long-term memory and explore multi-hop knowledge connections.";
    generateAndPlayAudio(5, act5Narration, act5Start, audioSegments);
    await showHudBanner(page, 5, TOTAL_ACTS, 'Dual Memory Explorer', 'Querying semantic vector vault and inspecting GraphRAG entity relationships.');

    // Perform vector search
    const memSearchInput = page.locator('input[placeholder*="Search memories"]').first();
    if (await memSearchInput.count() > 0) {
      await memSearchInput.click();
      await memSearchInput.fill('budget review architecture');
      await page.waitForTimeout(600);

      const memSearchBtn = page.locator('button:has-text("Search")').first();
      if (await memSearchBtn.count() > 0) {
        await memSearchBtn.click();
        await page.waitForTimeout(1200);
      }
    }

    // Switch to Knowledge Graph tab
    const kgTab = page.locator('button:has-text("Knowledge Graph"), button:has-text("GraphRAG")').first();
    if (await kgTab.count() > 0) {
      await kgTab.click();
      await page.waitForTimeout(1500);
    }
    await page.waitForTimeout(2000);

    // ==========================================================================
    // ACT 6: Multi-Agent Swarm Orchestrator (Debate Pattern)
    // ==========================================================================
    console.log(`${GREEN}[Act 6/12] 🌐 Interactive Multi-Agent Swarm Orchestrator...${RESET}`);
    await page.goto(`${BASE_URL}/orchestrator`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    const act6Start = getElapsedSec();
    const act6Narration = "Act Six: Swarm Orchestrator. We explore multi-agent debate and supervisor decomposition, viewing real-time worker consensus streams.";
    generateAndPlayAudio(6, act6Narration, act6Start, audioSegments);
    await showHudBanner(page, 6, TOTAL_ACTS, 'Swarm Orchestrator', 'Adversarial Red-Team debate and supervisor task decomposition.');

    const debateBtn = page.locator('button:has-text("Debate")').first();
    if (await debateBtn.count() > 0) {
      await debateBtn.click();
      await page.waitForTimeout(1000);

      // Set rigor to 1 round for rapid demonstration
      const rigorSelect = page.locator('select').nth(3);
      if (await rigorSelect.count() > 0) {
        await rigorSelect.selectOption('1');
        await page.waitForTimeout(400);
      }

      const startDebateBtn = page.locator('button:has-text("Start Multi-Agent Debate")').first();
      if (await startDebateBtn.count() > 0) {
        await startDebateBtn.click();
        console.log(`  ↳ Started multi-agent debate stream...`);
        try {
          await page.waitForSelector('button:has-text("Start Multi-Agent Debate"):not([disabled])', { timeout: 25000 });
          await page.waitForTimeout(1500);
        } catch (e) { /* ignore */ }
      }
    }
    await page.waitForTimeout(2000);

    // ==========================================================================
    // ACT 7: Sandboxed Workspace Files
    // ==========================================================================
    console.log(`${BLUE}[Act 7/12] 📁 Sandboxed Workspace Files...${RESET}`);
    await page.goto(`${BASE_URL}/workspace`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    const act7Start = getElapsedSec();
    const act7Narration = "Act Seven: Sandboxed Workspace. The filesystem isolates agent files with strict path traversal security, allowing safe generation of scripts, reports, and itineraries.";
    generateAndPlayAudio(7, act7Narration, act7Start, audioSegments);
    await showHudBanner(page, 7, TOTAL_ACTS, 'Sandboxed Workspace', 'Jailed directory management with path traversal guard and editor preview.');

    const refreshBtn = page.locator('button:has-text("Refresh")').first();
    if (await refreshBtn.count() > 0) {
      await refreshBtn.click();
      await page.waitForTimeout(1000);
    }
    await page.waitForTimeout(2000);

    // ==========================================================================
    // ACT 8: Domain Skills Hub
    // ==========================================================================
    console.log(`${YELLOW}[Act 8/12] 🎭 Domain Skills Hub...${RESET}`);
    await page.goto(`${BASE_URL}/skills`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    const act8Start = getElapsedSec();
    const act8Narration = "Act Eight: Domain Skills Hub. Ten expert personas inject system prompts on demand through progressive disclosure, maintaining concise context and saving up to eighty-five percent of tokens.";
    generateAndPlayAudio(8, act8Narration, act8Start, audioSegments);
    await showHudBanner(page, 8, TOTAL_ACTS, 'Domain Skills Hub', 'Progressive skill disclosure with 10 expert personas saving 85% context tokens.');

    const skillCards = page.locator('.skill-card');
    if (await skillCards.count() > 0) {
      await skillCards.first().hover();
      await page.waitForTimeout(800);
      if (await skillCards.count() > 1) {
        await skillCards.nth(1).hover();
        await page.waitForTimeout(800);
      }
    }
    await page.waitForTimeout(1500);

    // ==========================================================================
    // ACT 9: 3-Tier Audit Logs (Expand Row -> Inspect Payload)
    // ==========================================================================
    console.log(`${MAGENTA}[Act 9/12] 📋 3-Tier Audit Logs...${RESET}`);
    await page.goto(`${BASE_URL}/logs`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    const act9Start = getElapsedSec();
    const act9Narration = "Act Nine: Three-Tier Audit Logs. Every LLM request, tool execution, and turn is captured with cryptographic timestamps, token counts, and latency metrics.";
    generateAndPlayAudio(9, act9Narration, act9Start, audioSegments);
    await showHudBanner(page, 9, TOTAL_ACTS, '3-Tier Audit Logs', 'Conversation ➔ Turn ➔ Request hierarchical tree with real-time token receipts.');

    const firstLogItem = page.locator('tbody tr, .log-item, .tree-node').first();
    if (await firstLogItem.count() > 0) {
      await firstLogItem.click();
      await page.waitForTimeout(1200);
    }
    await page.waitForTimeout(2000);

    // ==========================================================================
    // ACT 10: Human-in-the-Loop Safety Approvals (Rules & History)
    // ==========================================================================
    console.log(`${CYAN}[Act 10/12] 🛡️ Safety Approvals (HITL)...${RESET}`);
    await page.goto(`${BASE_URL}/approvals`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    const act10Start = getElapsedSec();
    const act10Narration = "Act Ten: Safety Approvals and Human in the Loop. Automated policy rules gate high-risk operations with tiered risk assessments and countdown timers.";
    generateAndPlayAudio(10, act10Narration, act10Start, audioSegments);
    await showHudBanner(page, 10, TOTAL_ACTS, 'Human-in-the-Loop (HITL)', 'Tiered safety gating with countdown timers and automated policy rules.');

    const rulesTab = page.locator('button:has-text("Rules"), button:has-text("Policy")').first();
    if (await rulesTab.count() > 0) {
      await rulesTab.click();
      await page.waitForTimeout(1200);
    }

    const histTab = page.locator('button:has-text("History")').first();
    if (await histTab.count() > 0) {
      await histTab.click();
      await page.waitForTimeout(1200);
    }
    await page.waitForTimeout(1500);

    // ==========================================================================
    // ACT 11: Telemetry & Observability Dashboard
    // ==========================================================================
    console.log(`${GREEN}[Act 11/12] 📈 Telemetry & Observability Dashboard...${RESET}`);
    await page.goto(`${BASE_URL}/overview`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    const act11Start = getElapsedSec();
    const act11Narration = "Act Eleven: Real-time Telemetry and Observability. Executive dashboards monitor token consumption, provider distributions, and P99 latency SLAs.";
    generateAndPlayAudio(11, act11Narration, act11Start, audioSegments);
    await showHudBanner(page, 11, TOTAL_ACTS, 'Telemetry & Metrics', 'Real-time KPIs, token breakdown donut, model shares, and latency percentiles.');

    await page.mouse.wheel(0, 350);
    await page.waitForTimeout(1500);
    await page.mouse.wheel(0, -350);
    await page.waitForTimeout(1500);

    // ==========================================================================
    // ACT 12: Provider Settings & Gateway Health
    // ==========================================================================
    console.log(`${BLUE}[Act 12/12] ⚙️ Provider Settings & Gateway Health...${RESET}`);
    await page.goto(`${BASE_URL}/settings`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    const act12Start = getElapsedSec();
    const act12Narration = "Act Twelve: Settings and Multi-Provider Architecture. Easily configure local models or cloud providers with zero vendor lock-in. This concludes our interactive demonstration.";
    generateAndPlayAudio(12, act12Narration, act12Start, audioSegments);
    await showHudBanner(page, 12, TOTAL_ACTS, 'Settings & Providers', 'Ollama detection, cloud API configurations, transport modes, and system health.');

    await page.waitForTimeout(3000);

    console.log(`\n${GREEN}${BOLD}✨ Interactive Walkthrough completed! Finalizing video & audio tracks...${RESET}\n`);

  } finally {
    // Commit raw video recording
    await page.close();
    await context.close();
    await browser.close();
  }

  // Calculate total recording duration
  const totalDurationSec = getElapsedSec();
  console.log(`  Duration:   ${totalDurationSec.toFixed(1)}s`);
  console.log(`  Segments:   ${audioSegments.length} timed audio voiceover clips`);

  // Assemble Master Audio Track using Python timeline mixer
  const masterWavPath = path.join(tempAudioDir, 'master_audio.wav');
  console.log(`${BLUE}🎵 Assembling master audio narration track with exact timeline sync...${RESET}`);

  const pyMixerScript = `
import wave, struct, sys, json

with open(sys.argv[1], 'r') as f:
    segments = json.load(f)
total_duration_sec = float(sys.argv[2]) + 1.5
output_wav = sys.argv[3]

sample_rate = 44100
num_channels = 2
sample_width = 2
bytes_per_sample = sample_width * num_channels
total_frames = int(total_duration_sec * sample_rate)
master_buffer = bytearray(total_frames * bytes_per_sample)

for item in segments:
    start_time_sec = float(item['startSec'])
    wav_file = item['wavPath']
    try:
        with wave.open(wav_file, 'rb') as w:
            frames = w.readframes(w.getnframes())
            start_byte = int(start_time_sec * sample_rate) * bytes_per_sample
            for i in range(0, len(frames), 2):
                idx = start_byte + i
                if idx + 1 < len(master_buffer):
                    val_orig = struct.unpack_from('<h', master_buffer, idx)[0]
                    val_new = struct.unpack_from('<h', frames, i)[0]
                    val_mixed = max(-32768, min(32767, val_orig + val_new))
                    struct.pack_into('<h', master_buffer, idx, val_mixed)
    except Exception as e:
        print(f"Error mixing {wav_file}: {e}", file=sys.stderr)

with wave.open(output_wav, 'wb') as out:
    out.setnchannels(num_channels)
    out.setsampwidth(sample_width)
    out.setframerate(sample_rate)
    out.writeframes(master_buffer)
`;

  try {
    const pythonExe = fs.existsSync(path.join(ROOT_DIR, '.venv/bin/python3'))
      ? path.join(ROOT_DIR, '.venv/bin/python3')
      : 'python3';

    const mixerPyFile = path.join(tempAudioDir, 'mixer.py');
    const segmentsJsonFile = path.join(tempAudioDir, 'segments.json');
    fs.writeFileSync(mixerPyFile, pyMixerScript.trim());
    fs.writeFileSync(segmentsJsonFile, JSON.stringify(audioSegments));

    execSync(`"${pythonExe}" "${mixerPyFile}" "${segmentsJsonFile}" ${totalDurationSec} "${masterWavPath}"`);
    console.log(`  ${GREEN}✓ Master audio narration compiled successfully.${RESET}`);
  } catch (err) {
    console.error(`  ${YELLOW}Audio assembly note:${RESET}`, err.message);
  }

  // Find Playwright's raw recorded video file
  const videoFiles = fs.readdirSync(tempVideoDir).filter(f => f.endsWith('.webm'));
  if (videoFiles.length === 0) {
    console.error('No raw video captured by Playwright.');
    return;
  }
  const rawVideoPath = path.join(tempVideoDir, videoFiles[0]);

  // Destination File Paths
  const dateStr = new Date().toISOString().slice(0, 10);
  const baseName = customOutputArg
    ? path.basename(customOutputArg, path.extname(customOutputArg))
    : `agentic_ai_interactive_movie_${dateStr}`;

  const finalMp4Path = path.join(RECORDINGS_DIR, `${baseName}.mp4`);
  const finalWebmPath = path.join(RECORDINGS_DIR, `${baseName}.webm`);

  console.log(`${MAGENTA}🎬 Multiplexing video and audio with FFmpeg into MP4 & WebM...${RESET}`);

  // 1. Generate MP4 (H.264 + AAC) with FastStart
  if (fs.existsSync(masterWavPath)) {
    try {
      execSync(`"${FFMPEG_BIN}" -y -i "${rawVideoPath}" -i "${masterWavPath}" -c:v libx264 -preset veryfast -crf 22 -c:a aac -b:a 192k -movflags +faststart -shortest "${finalMp4Path}" 2>/dev/null`);
    } catch (e) {
      console.warn('MP4 encoding failed, falling back to copy:', e.message);
    }

    // 2. Generate WebM (VP9/VP8 + Opus)
    try {
      execSync(`"${FFMPEG_BIN}" -y -i "${rawVideoPath}" -i "${masterWavPath}" -c:v copy -c:a libopus -b:a 128k -shortest "${finalWebmPath}" 2>/dev/null`);
    } catch (e) {
      // Direct copy fallback
      fs.copyFileSync(rawVideoPath, finalWebmPath);
    }
  } else {
    // If audio failed, copy raw video
    fs.copyFileSync(rawVideoPath, finalWebmPath);
  }

  // Cleanup temporary working directories
  fs.rmSync(tempVideoDir, { recursive: true, force: true });
  fs.rmSync(tempAudioDir, { recursive: true, force: true });

  console.log(`\n${CYAN}${BOLD}==========================================================================${RESET}`);
  console.log(`${GREEN}${BOLD}🎉 INTERACTIVE MOVIE WITH AUDIO RECORDED SUCCESSFULLY!${RESET}`);

  if (fs.existsSync(finalMp4Path)) {
    const statsMp4 = fs.statSync(finalMp4Path);
    console.log(`  📹 MP4 Video:  ${BOLD}${finalMp4Path}${RESET} (${(statsMp4.size / (1024 * 1024)).toFixed(2)} MB, H.264 + AAC Audio)`);
  }
  if (fs.existsSync(finalWebmPath)) {
    const statsWebm = fs.statSync(finalWebmPath);
    console.log(`  🌐 WebM Video: ${BOLD}${finalWebmPath}${RESET} (${(statsWebm.size / (1024 * 1024)).toFixed(2)} MB, Web Browser Native)`);
  }
  console.log(`  ⏱️ Duration:   ~${totalDurationSec.toFixed(0)} seconds (12 Interactive Acts with Voiceover)`);
  console.log(`${CYAN}${BOLD}==========================================================================${RESET}`);
  console.log(`\n${YELLOW}To watch the movie with audio narration on macOS:${RESET}`);
  console.log(`  ${BOLD}open "${finalMp4Path}"${RESET}   # Opens in QuickTime Player with full sound\n`);
}

recordInteractiveMovie().catch(err => {
  console.error('Interactive movie recording failed:', err);
  process.exit(1);
});
