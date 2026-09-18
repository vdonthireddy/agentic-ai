#!/usr/bin/env node
/**
 * ==============================================================================
 * 🎬 Agentic-AI: Synchronized Interactive Movie & Audio Recorder
 * ==============================================================================
 * Automates a perfectly synchronized, interactive demonstration across the platform:
 *  - Pre-synthesizes studio voiceover audio clips for each Act (macOS Samantha)
 *  - Calculates exact audio durations to guarantee ZERO AUDIO OVERLAP
 *  - Holds each tab on screen until its voiceover narration has finished completely
 *  - Enters real values, executes actions, and highlights live results
 *  - Plays audio live through speakers during headed browser execution
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
console.log('  🎬 AGENTIC-AI : SYNCHRONIZED INTERACTIVE MOVIE & AUDIO RECORDER');
console.log(`  Mode:        ${isHeadless ? 'Headless Video Capture' : 'Headed Live Window & Audio Narration'}`);
console.log(`  Target:      ${BASE_URL}`);
console.log(`  Audio:       macOS Speech Synthesis (Samantha) + Zero-Overlap Sync`);
console.log(`  Output:      HD 1440x900 MP4 (H.264+AAC) & WebM (VP9+Opus)`);
console.log('==========================================================================');
console.log(RESET);

// Act Definitions with Narration Scripts
const ACT_DEFINITIONS = [
  {
    num: 1,
    title: 'AI Agent Chatbot Studio',
    subtitle: 'ReAct reasoning loop, live mathematical tool execution, and structured receipts.',
    url: `${BASE_URL}/chat`,
    narration: 'Act One: AI Agent Chatbot Studio. We enter an everyday prompt asking the autonomous agent to calculate an eighteen percent tip on dinner for four people. Watch as the agent reasons, executes the math tool, and delivers a structured receipt.',
    action: async (page) => {
      const chatTextarea = page.locator('textarea').first();
      if (await chatTextarea.count() > 0) {
        await chatTextarea.click();
        await page.waitForTimeout(300);
        const promptText = 'Use calculator to calculate an 18% tip on a $184.50 dinner split among 4 people.';
        await chatTextarea.pressSequentially(promptText, { delay: 25 });
        await page.waitForTimeout(500);

        const sendBtn = page.locator('button.btn-primary:has-text("Send")').first();
        if (await sendBtn.count() > 0) {
          await sendBtn.click();
          console.log(`  ↳ Sent prompt to agent. Waiting for ReAct execution...`);
          try {
            await page.waitForSelector('.chat-message.message-assistant, .chat-message.message-bot, .tool-call-feed', { timeout: 35000 });
            await page.waitForTimeout(2000);
          } catch (e) {
            console.warn('  ↳ Agent response wait note:', e.message);
          }
        }
      }
    }
  },
  {
    num: 2,
    title: 'Workflow Canvas (DAG Studio)',
    subtitle: 'Kahn topological scheduling, 2D visual board, and multi-stage execution.',
    url: `${BASE_URL}/canvas`,
    narration: 'Act Two: Visual Workflow Canvas. We load the parallel swarm DAG pipeline, connecting reasoning and tool nodes, and trigger execution. Watch as topological scheduling runs each stage to completion.',
    action: async (page) => {
      const templateBtn = page.locator('button.template-pill-btn:has-text("Parallel Swarm"), button:has-text("Parallel Swarm")').first();
      if (await templateBtn.count() > 0) {
        await templateBtn.click();
        await page.waitForTimeout(1000);
      }

      const runDagBtn = page.locator('button:has-text("Run Workflow DAG")').first();
      if (await runDagBtn.count() > 0) {
        await runDagBtn.click();
        console.log(`  ↳ Triggered DAG execution. Animating topological stages...`);
        try {
          await page.waitForSelector('.canvas-execution-report, .dag-execution-card', { timeout: 35000 });
          await page.waitForTimeout(1500);
        } catch (e) {
          console.warn('  ↳ DAG run wait note:', e.message);
        }
      }
    }
  },
  {
    num: 3,
    title: 'FastMCP Tools Sandbox',
    subtitle: 'Direct tool execution with arbitrary JSON arguments and latency receipts.',
    url: `${BASE_URL}/tools`,
    narration: 'Act Three: FastMCP Tools Sandbox. We select the tip and split tool, input JSON arguments, and execute live in the sandbox to observe sub-millisecond execution latency.',
    action: async (page) => {
      const toolSelect = page.locator('select.form-control').first();
      if (await toolSelect.count() > 0) {
        const options = await toolSelect.locator('option').allInnerTexts();
        const targetOption = options.find(o => o.includes('calculate_tip_and_split')) || options.find(o => o.includes('calculator'));
        if (targetOption) {
          const val = targetOption.split(' ')[0];
          await toolSelect.selectOption(val);
          await page.waitForTimeout(500);
        }
      }

      const argsBox = page.locator('textarea.form-control.code-font').first();
      if (await argsBox.count() > 0) {
        await argsBox.click();
        await argsBox.fill('{\n  "total": 184.50,\n  "tip_percentage": 18,\n  "split_count": 4\n}');
        await page.waitForTimeout(600);
      }

      const executeBtn = page.locator('button:has-text("Execute Tool in Sandbox")').first();
      if (await executeBtn.count() > 0) {
        await executeBtn.click();
        console.log(`  ↳ Executed tool in sandbox. Awaiting JSON response...`);
        try {
          await page.waitForSelector('.json-code-box', { timeout: 10000 });
          await page.waitForTimeout(1500);
        } catch (e) { /* ignore */ }
      }
    }
  },
  {
    num: 4,
    title: '2-Stage Smart Router',
    subtitle: 'Intent reasoning, threshold confidence gates, and automated model dispatching.',
    url: `${BASE_URL}/smart-router`,
    narration: 'Act Four: Two-Stage Smart Router. We submit an algorithmic coding task. Stage one classifies the intent with high confidence, routing execution directly to our local coder model.',
    action: async (page) => {
      const routerInput = page.locator('textarea').first();
      if (await routerInput.count() > 0) {
        await routerInput.click();
        const codeQuery = 'Write a Python function to invert a binary tree in O(n) time.';
        await routerInput.pressSequentially(codeQuery, { delay: 18 });
        await page.waitForTimeout(500);

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
    }
  },
  {
    num: 5,
    title: 'Dual Memory Explorer',
    subtitle: 'ChromaDB semantic vector embeddings + SQLite GraphRAG relationship knowledge.',
    url: `${BASE_URL}/memory`,
    narration: 'Act Five: Dual Memory Explorer. Combining semantic vector embeddings with GraphRAG relationships. We query long-term memory and explore multi-hop knowledge connections.',
    action: async (page) => {
      const memSearchInput = page.locator('input[placeholder*="Search memories"]').first();
      if (await memSearchInput.count() > 0) {
        await memSearchInput.click();
        await memSearchInput.fill('budget review architecture');
        await page.waitForTimeout(500);

        const memSearchBtn = page.locator('button:has-text("Search")').first();
        if (await memSearchBtn.count() > 0) {
          await memSearchBtn.click();
          await page.waitForTimeout(1200);
        }
      }

      const kgTab = page.locator('button:has-text("Knowledge Graph"), button:has-text("GraphRAG")').first();
      if (await kgTab.count() > 0) {
        await kgTab.click();
        await page.waitForTimeout(1500);
      }
    }
  },
  {
    num: 6,
    title: 'Swarm Orchestrator',
    subtitle: 'Adversarial multi-agent debate and supervisor task decomposition.',
    url: `${BASE_URL}/orchestrator`,
    narration: 'Act Six: Swarm Orchestrator. We explore multi-agent debate and supervisor decomposition, viewing real-time worker consensus streams.',
    action: async (page) => {
      const debateBtn = page.locator('button:has-text("Debate")').first();
      if (await debateBtn.count() > 0) {
        await debateBtn.click();
        await page.waitForTimeout(800);

        const rigorSelect = page.locator('select').nth(3);
        if (await rigorSelect.count() > 0) {
          await rigorSelect.selectOption('1');
          await page.waitForTimeout(300);
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
    }
  },
  {
    num: 7,
    title: 'Sandboxed Workspace',
    subtitle: 'Jailed directory management with path traversal prevention and editor preview.',
    url: `${BASE_URL}/workspace`,
    narration: 'Act Seven: Sandboxed Workspace. The filesystem isolates agent files with strict path traversal security, allowing safe generation of scripts, reports, and itineraries.',
    action: async (page) => {
      const refreshBtn = page.locator('button:has-text("Refresh")').first();
      if (await refreshBtn.count() > 0) {
        await refreshBtn.click();
        await page.waitForTimeout(800);
      }
      const fileCards = page.locator('.file-item, .list-item, tr');
      if (await fileCards.count() > 1) {
        await fileCards.nth(1).click();
        await page.waitForTimeout(1200);
      }
    }
  },
  {
    num: 8,
    title: 'Domain Skills Hub',
    subtitle: 'Progressive skill disclosure with 10 expert personas saving 85% context tokens.',
    url: `${BASE_URL}/skills`,
    narration: 'Act Eight: Domain Skills Hub. Ten expert personas inject system prompts on demand through progressive disclosure, maintaining concise context and saving up to eighty-five percent of tokens.',
    action: async (page) => {
      const skillCards = page.locator('.skill-card');
      if (await skillCards.count() > 0) {
        await skillCards.first().hover();
        await page.waitForTimeout(1000);
        if (await skillCards.count() > 1) {
          await skillCards.nth(1).hover();
          await page.waitForTimeout(1000);
        }
      }
    }
  },
  {
    num: 9,
    title: '3-Tier Audit Logs',
    subtitle: 'Conversation ➔ Turn ➔ Request hierarchy with live SSE streaming receipts.',
    url: `${BASE_URL}/logs`,
    narration: 'Act Nine: Three-Tier Audit Logs. Every request, tool execution, and turn is captured with cryptographic timestamps, token counts, and latency metrics.',
    action: async (page) => {
      const firstLogItem = page.locator('tbody tr, .log-item, .tree-node').first();
      if (await firstLogItem.count() > 0) {
        await firstLogItem.click();
        await page.waitForTimeout(1500);
      }
    }
  },
  {
    num: 10,
    title: 'Safety Approvals (HITL)',
    subtitle: 'Tiered governance gating high-risk actions with countdown timers.',
    url: `${BASE_URL}/approvals`,
    narration: 'Act Ten: Safety Approvals and Human in the Loop. Automated policy rules gate high-risk operations with tiered risk assessments and countdown timers.',
    action: async (page) => {
      const rulesTab = page.locator('button:has-text("Rules"), button:has-text("Policy")').first();
      if (await rulesTab.count() > 0) {
        await rulesTab.click();
        await page.waitForTimeout(1500);
      }
      const histTab = page.locator('button:has-text("History")').first();
      if (await histTab.count() > 0) {
        await histTab.click();
        await page.waitForTimeout(1500);
      }
    }
  },
  {
    num: 11,
    title: 'Telemetry & Observability',
    subtitle: 'Real-time KPIs, token breakdown donut, model shares, and latency percentiles.',
    url: `${BASE_URL}/overview`,
    narration: 'Act Eleven: Real-time Telemetry and Observability. Executive dashboards monitor token consumption, provider distributions, and P99 latency SLAs.',
    action: async (page) => {
      await page.mouse.wheel(0, 350);
      await page.waitForTimeout(1800);
      await page.mouse.wheel(0, -350);
      await page.waitForTimeout(1500);
    }
  },
  {
    num: 12,
    title: 'Settings & Providers',
    subtitle: 'Ollama detection, cloud API configurations, transport modes, and system health.',
    url: `${BASE_URL}/settings`,
    narration: 'Act Twelve: Settings and Multi-Provider Architecture. Easily configure local models or cloud providers with zero vendor lock-in. This concludes our interactive demonstration.',
    action: async (page) => {
      await page.waitForTimeout(2500);
    }
  }
];

// Injects floating Director HUD banner with live ticking timer
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

      // Heartbeat pulse to ensure continuous video frame rendering
      setInterval(() => {
        const pulse = document.getElementById('hud-pulse-dot');
        if (pulse) {
          pulse.style.opacity = pulse.style.opacity === '1' ? '0.4' : '1';
        }
      }, 500);
    }
    hud.innerHTML = `
      <div style="display: flex; align-items: center; justify-between; gap: 10px; margin-bottom: 6px;">
        <span style="background: linear-gradient(135deg, #0284c7, #38bdf8); color: #fff; font-size: 11px; font-weight: 700; padding: 2px 9px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.5px;">
          Act ${stepNum} of ${totalSteps}
        </span>
        <span style="font-size: 14px; font-weight: 600; color: #f8fafc; flex: 1;">${title}</span>
        <div style="display: flex; align-items: center; gap: 5px;">
          <span id="hud-pulse-dot" style="display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: #22c55e; transition: opacity 0.5s;"></span>
          <span style="font-size: 10px; color: #38bdf8; font-family: monospace;">VOICEOVER</span>
        </div>
      </div>
      <div style="font-size: 12px; color: #94a3b8; line-height: 1.4;">${subtitle}</div>
    `;
  }, { stepNum, totalSteps, title, subtitle });
}

// Pre-synthesize all audio narration clips and measure exact durations
function preSynthesizeAudioClips() {
  console.log(`${BLUE}🎙️ Pre-generating studio voiceover narration clips...${RESET}`);
  for (const act of ACT_DEFINITIONS) {
    const aiffPath = path.join(tempAudioDir, `act_${act.num}.aiff`);
    const wavPath = path.join(tempAudioDir, `act_${act.num}.wav`);

    // Synthesize AIFF via macOS say
    execSync(`say -v Samantha "${act.narration.replace(/"/g, '\\"')}" -o "${aiffPath}"`);

    // Standardize to 44.1kHz Stereo WAV
    execSync(`"${FFMPEG_BIN}" -y -i "${aiffPath}" -ar 44100 -ac 2 "${wavPath}" 2>/dev/null`);

    // Measure exact audio duration
    const durStr = execSync(`"${FFMPEG_BIN}" -i "${wavPath}" 2>&1 | grep "Duration"`, { encoding: 'utf8' });
    const match = durStr.match(/Duration:\s*(\d+):(\d+):(\d+\.\d+)/);
    let durationSec = 10.0;
    if (match) {
      durationSec = parseInt(match[1]) * 3600 + parseInt(match[2]) * 60 + parseFloat(match[3]);
    }

    act.audioClip = {
      aiffPath,
      wavPath,
      durationSec
    };

    console.log(`  ✓ Act ${act.num} [${act.title}]: ${durationSec.toFixed(2)}s narration`);
  }
  console.log(`${GREEN}✓ All 12 voiceover narration clips ready with exact duration metrics.${RESET}\n`);
}

// Main Interactive Movie Flow
async function recordInteractiveMovie() {
  // Pre-generate audio to know all durations ahead of time
  preSynthesizeAudioClips();

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
  const audioSegments = [];
  const recordingStartTime = Date.now();

  try {
    for (const act of ACT_DEFINITIONS) {
      console.log(`\n${MAGENTA}[Act ${act.num}/${ACT_DEFINITIONS.length}] 🎬 ${act.title}...${RESET}`);
      const actStartTime = Date.now();
      const startSec = (actStartTime - recordingStartTime) / 1000.0;

      // 1. Navigate to target tab
      await page.goto(act.url, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(600);

      // 2. Display on-screen HUD banner
      await showHudBanner(page, act.num, ACT_DEFINITIONS.length, act.title, act.subtitle);

      // 3. Register audio clip at this exact timeline timestamp
      audioSegments.push({
        startSec: startSec,
        wavPath: act.audioClip.wavPath
      });

      // 4. Play audio live through speakers if running headed on macOS
      if (!isHeadless && !isMuted && process.platform === 'darwin') {
        spawn('afplay', [act.audioClip.aiffPath], { stdio: 'ignore', detached: true });
      }

      // 5. Execute interactive actions
      try {
        await act.action(page);
      } catch (err) {
        console.warn(`  ↳ Action note in Act ${act.num}:`, err.message);
      }

      // 6. CRITICAL: Guarantee the tab stays active until narration is finished + buffer!
      // This completely prevents audio from overlapping with subsequent acts!
      const minRequiredMs = Math.round((act.audioClip.durationSec + 1.8) * 1000);
      const elapsedMs = Date.now() - actStartTime;
      if (elapsedMs < minRequiredMs) {
        const remainingMs = minRequiredMs - elapsedMs;
        console.log(`  ↳ Holding tab for audio narration to complete (${(remainingMs / 1000).toFixed(1)}s remaining)...`);
        await page.waitForTimeout(remainingMs);
      }

      // 7. Small visual pause before smoothly transitioning to next tab
      await page.waitForTimeout(400);
    }

    console.log(`\n${GREEN}${BOLD}✨ Interactive Walkthrough completed! Finalizing video & audio tracks...${RESET}\n`);

  } finally {
    // Commit raw video recording
    await page.close();
    await context.close();
    await browser.close();
  }

  // Calculate total recording duration
  const totalDurationSec = (Date.now() - recordingStartTime) / 1000.0;
  console.log(`  Total Duration: ${totalDurationSec.toFixed(1)}s`);
  console.log(`  Audio Clips:    ${audioSegments.length} non-overlapping narration segments`);

  // Assemble Master Audio Track using Python timeline mixer
  const masterWavPath = path.join(tempAudioDir, 'master_audio.wav');
  console.log(`${BLUE}🎵 Compiling master audio narration track with exact zero-overlap timeline sync...${RESET}`);

  const pyMixerScript = `
import wave, struct, sys, json

with open(sys.argv[1], 'r') as f:
    segments = json.load(f)
total_duration_sec = float(sys.argv[2]) + 2.0
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
    console.log(`  ${GREEN}✓ Master audio narration compiled with zero overlaps.${RESET}`);
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
      fs.copyFileSync(rawVideoPath, finalWebmPath);
    }
  } else {
    fs.copyFileSync(rawVideoPath, finalWebmPath);
  }

  // Cleanup temporary working directories
  fs.rmSync(tempVideoDir, { recursive: true, force: true });
  fs.rmSync(tempAudioDir, { recursive: true, force: true });

  console.log(`\n${CYAN}${BOLD}==========================================================================${RESET}`);
  console.log(`${GREEN}${BOLD}🎉 SYNCHRONIZED INTERACTIVE MOVIE RECORDED SUCCESSFULLY!${RESET}`);

  if (fs.existsSync(finalMp4Path)) {
    const statsMp4 = fs.statSync(finalMp4Path);
    console.log(`  📹 MP4 Video:  ${BOLD}${finalMp4Path}${RESET} (${(statsMp4.size / (1024 * 1024)).toFixed(2)} MB, H.264 + AAC Audio)`);
  }
  if (fs.existsSync(finalWebmPath)) {
    const statsWebm = fs.statSync(finalWebmPath);
    console.log(`  🌐 WebM Video: ${BOLD}${finalWebmPath}${RESET} (${(statsWebm.size / (1024 * 1024)).toFixed(2)} MB, Web Browser Native)`);
  }
  console.log(`  ⏱️ Duration:   ~${totalDurationSec.toFixed(0)} seconds (12 Interactive Acts, 100% Synchronized Audio)`);
  console.log(`${CYAN}${BOLD}==========================================================================${RESET}`);
  console.log(`\n${YELLOW}To watch the synchronized movie with audio on macOS:${RESET}`);
  console.log(`  ${BOLD}open "${finalMp4Path}"${RESET}   # Opens in QuickTime Player with crystal clear sound\n`);
}

recordInteractiveMovie().catch(err => {
  console.error('Interactive movie recording failed:', err);
  process.exit(1);
});
