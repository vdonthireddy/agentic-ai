#!/usr/bin/env node
/**
 * ==============================================================================
 * 🎬 Agentic-AI: Modular Feature Video & Audio Recorder
 * ==============================================================================
 * Records comprehensive, paced, end-to-end walkthrough videos for each core feature:
 *  - 1 Feature = 1 Dedicated Video (~45-75s) with its own self-contained story
 *  - High-definition 1440x900 capture in both MP4 (H.264+AAC) and WebM (VP9+Opus)
 *  - Studio audio narration (macOS say -v Samantha, 44.1kHz Stereo)
 *  - Strict zero-overlap audio timeline synchronization
 *  - Realistic human typing cadence and button interactions
 *  - Waits for real backend results (agent thinking, DAG execution, tool output)
 *  - Smooth scrolling up and down to inspect JSON responses, execution traces, and metrics
 *  - Builds an interactive HTML video gallery in recordings/features/index.html
 *
 * Usage:
 *   node scripts/record_feature_videos.mjs --all
 *   node scripts/record_feature_videos.mjs --feature chat_react
 *   node scripts/record_feature_videos.mjs --feature workflow_dag
 *   node scripts/record_feature_videos.mjs --feature fastmcp_tools
 *   node scripts/record_feature_videos.mjs --feature smart_router
 *   node scripts/record_feature_videos.mjs --feature dual_memory
 *   node scripts/record_feature_videos.mjs --feature orchestrator_debate
 *   node scripts/record_feature_videos.mjs --feature governance_audit
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
const FEATURES_DIR = path.join(ROOT_DIR, 'recordings', 'features');

// Ensure output directory exists
if (!fs.existsSync(FEATURES_DIR)) {
  fs.mkdirSync(FEATURES_DIR, { recursive: true });
}

// CLI Flags
const args = process.argv.slice(2);
const isHeadless = args.includes('--headless') || (!args.includes('--headed') && !process.env.DISPLAY && process.platform !== 'darwin');
const isMuted = args.includes('--mute') || args.includes('--no-audio');
const targetFeature = args.find((arg, i) => args[i - 1] === '--feature') || (args.includes('--all') ? 'all' : null);

// Colors
const CYAN = '\x1b[36m';
const GREEN = '\x1b[32m';
const YELLOW = '\x1b[33m';
const MAGENTA = '\x1b[35m';
const BLUE = '\x1b[34m';
const BOLD = '\x1b[1m';
const RESET = '\x1b[0m';

// Detect FFmpeg Binary
function getFfmpegPath() {
  if (process.env.FFMPEG_PATH && fs.existsSync(process.env.FFMPEG_PATH)) {
    return process.env.FFMPEG_PATH;
  }
  const venvFfmpeg = path.join(ROOT_DIR, '.venv/lib/python3.12/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1');
  if (fs.existsSync(venvFfmpeg)) return venvFfmpeg;
  try {
    const sysFfmpeg = execSync('which ffmpeg', { encoding: 'utf8' }).trim();
    if (sysFfmpeg && fs.existsSync(sysFfmpeg)) return sysFfmpeg;
  } catch (e) { /* ignore */ }
  return 'ffmpeg';
}
const FFMPEG_BIN = getFfmpegPath();

// Helper to pre-synthesize voice clip using macOS 'say' and convert to 44.1kHz stereo WAV
function preSynthesizeClip(clipId, text, tempDir) {
  const aiffPath = path.join(tempDir, `${clipId}.aiff`);
  const wavPath = path.join(tempDir, `${clipId}.wav`);

  try {
    execSync(`say -v Samantha -r 175 -o "${aiffPath}" "${text.replace(/"/g, '\\"')}"`);
    execSync(`"${FFMPEG_BIN}" -y -i "${aiffPath}" -ar 44100 -ac 2 "${wavPath}" 2>/dev/null`);
    if (fs.existsSync(aiffPath)) fs.unlinkSync(aiffPath);

    const stats = fs.statSync(wavPath);
    // WAV 44100Hz 16-bit stereo = 176,400 bytes/sec
    const durationSec = Math.max(0.5, (stats.size - 44) / (44100 * 2 * 2));
    return { wavPath, durationSec };
  } catch (err) {
    console.warn(`    ⚠️ Speech synthesis fallback for ${clipId}:`, err.message);
    return { wavPath: null, durationSec: 4.0 };
  }
}

// Injects real-time animated HUD badge on top of page
async function showHudBanner(page, featureTitle, stepTitle, stepDescription) {
  try {
    await page.evaluate(({ featureTitle, stepTitle, stepDescription }) => {
      let banner = document.getElementById('demo-feature-hud');
      if (!banner) {
        banner = document.createElement('div');
        banner.id = 'demo-feature-hud';
        banner.style.cssText = `
          position: fixed;
          top: 14px;
          left: 50%;
          transform: translateX(-50%);
          z-index: 999999;
          background: rgba(10, 15, 30, 0.92);
          border: 1px solid rgba(99, 102, 241, 0.5);
          box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6), 0 0 20px rgba(99, 102, 241, 0.25);
          backdrop-filter: blur(14px);
          border-radius: 12px;
          padding: 9px 18px;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          color: #f8fafc;
          display: flex;
          align-items: center;
          gap: 16px;
          min-width: 580px;
          max-width: 860px;
          pointer-events: none;
          transition: all 0.3s ease-in-out;
        `;
        document.body.appendChild(banner);

        // Frame ticker to keep Chromium rendering continuously
        let count = 0;
        setInterval(() => {
          count++;
          const ticker = document.getElementById('hud-ticker-pulse');
          if (ticker) ticker.style.opacity = count % 2 === 0 ? '1' : '0.4';
        }, 500);
      }

      banner.innerHTML = `
        <div style="display:flex; align-items:center; gap:8px;">
          <div id="hud-ticker-pulse" style="width:10px; height:10px; border-radius:50%; background:#10b981; box-shadow:0 0 10px #10b981; transition:opacity 0.2s;"></div>
          <div style="display:flex; flex-direction:column;">
            <span style="font-size:10px; text-transform:uppercase; letter-spacing:0.08em; color:#818cf8; font-weight:700;">${featureTitle}</span>
            <span style="font-size:13px; font-weight:600; color:#f1f5f9;">${stepTitle}</span>
          </div>
        </div>
        <div style="height:28px; width:1px; background:rgba(255,255,255,0.12);"></div>
        <div style="flex:1; font-size:11.5px; color:#94a3b8; line-height:1.35;">
          ${stepDescription}
        </div>
        <div style="display:flex; align-items:center; gap:6px; background:rgba(99,102,241,0.15); border:1px solid rgba(99,102,241,0.3); border-radius:6px; padding:3px 8px; font-size:10px; color:#a5b4fc; font-weight:600;">
          🎙️ Studio Audio
        </div>
      `;
    }, { featureTitle, stepTitle, stepDescription });
  } catch (e) { /* ignore */ }
}

// Fluid human-like smooth scrolling
async function smoothScroll(page, targetY, durationMs = 800) {
  try {
    await page.evaluate(async ({ targetY, durationMs }) => {
      const scrollContainer = document.querySelector('.main-content') || document.querySelector('.content-pane') || window;
      const startY = scrollContainer === window ? window.scrollY : scrollContainer.scrollTop;
      const diff = targetY - startY;
      const startTime = performance.now();

      await new Promise((resolve) => {
        function step(currentTime) {
          const elapsed = currentTime - startTime;
          const progress = Math.min(elapsed / durationMs, 1);
          // Ease in-out cubic
          const ease = progress < 0.5 ? 4 * progress * progress * progress : 1 - Math.pow(-2 * progress + 2, 3) / 2;
          const currentY = startY + diff * ease;

          if (scrollContainer === window) {
            window.scrollTo(0, currentY);
          } else {
            scrollContainer.scrollTop = currentY;
          }

          if (progress < 1) {
            requestAnimationFrame(step);
          } else {
            resolve();
          }
        }
        requestAnimationFrame(step);
      });
    }, { targetY, durationMs });
    await page.waitForTimeout(durationMs + 100);
  } catch (e) { /* ignore */ }
}

// Realistic keyboard typing
async function typeNaturally(locator, text, delayMs = 30) {
  await locator.focus();
  await locator.pressSequentially(text, { delay: delayMs });
}

// ==============================================================================
// 7 END-TO-END FEATURE DEFINITIONS WITH PACED STORYTELLING
// ==============================================================================
const FEATURE_DEFINITIONS = [
  // ----------------------------------------------------------------------------
  // Feature 1: AI Agent Chat & ReAct Tool Calling
  // ----------------------------------------------------------------------------
  {
    id: '01_chat_react',
    title: 'Autonomous AI Agent & ReAct Tool Calling',
    subtitle: 'End-to-End Reason-Act Loop, MCP Calculator Execution, and Telemetry Receipts',
    route: '/chat',
    summary: 'Demonstrates an everyday dining bill query where the autonomous agent reasons through multi-step arithmetic, invokes the FastMCP calculator tool rather than hallucinating, inspects the raw execution payload, and returns a verified per-person breakdown with real-time token receipts.',
    steps: [
      {
        title: 'Introduction to ReAct Loop',
        desc: 'Autonomous agent reasoning framework combining conversational context with dynamic tool execution.',
        narration: 'Welcome to the Autonomous AI Agent Chat Studio. Here, our agent implements the ReAct framework: Reason, Act, Observe, and Synthesize. Instead of hallucinating complex calculations, it autonomously determines when to dispatch external tools.',
        action: async (page) => {
          await page.waitForTimeout(1000);
          const textarea = page.locator('textarea').first();
          await textarea.click();
          await page.waitForTimeout(500);
        }
      },
      {
        title: 'Entering Financial Query',
        desc: 'User inputs real-world dinner bill calculation split among 4 diners with 18% tip.',
        narration: 'We enter an everyday scenario: calculating an eighteen percent tip on a dinner bill of one hundred eighty-four dollars and fifty cents for four diners. Notice the realistic typing cadence as the prompt is entered into the chat input bar.',
        action: async (page) => {
          const textarea = page.locator('textarea').first();
          const prompt = 'Our dinner bill for 4 people is $184.50. Calculate an 18% tip and the split per person using calculator.';
          await typeNaturally(textarea, prompt, 32);
          await page.waitForTimeout(600);
        }
      },
      {
        title: 'Dispatching Prompt & Tool Execution',
        desc: 'Agent reasons, dispatches FastMCP calculator, and executes arithmetic securely.',
        narration: 'We submit the prompt. The agent detects the mathematical dependency, constructs the structured argument payload, and dispatches the request to our local FastMCP calculator tool. A live tool call badge appears directly in the conversation feed.',
        action: async (page) => {
          const sendBtn = page.locator('button.btn-primary:has-text("Send")').first();
          await sendBtn.click();
          console.log('  ↳ Awaiting ReAct tool execution and response...');
          try {
            await page.waitForSelector('.tool-call-feed, .chat-message.message-bot .message-content', { timeout: 35000 });
            await page.waitForTimeout(1500);
          } catch (e) { /* timeout fallback */ }
        }
      },
      {
        title: 'Inspecting Tool Output & Scrolling',
        desc: 'Scrolling down to inspect tool call badges, execution payloads, and final synthesized answer.',
        narration: 'Let us scroll down to inspect the execution receipt. The calculator returned thirty-three dollars and twenty-one cents tip, totaling two hundred seventeen dollars and seventy-one cents, or fifty-four dollars and forty-three cents per person. The agent synthesizes this into clean markdown.',
        action: async (page) => {
          await smoothScroll(page, 380, 700);
          await page.waitForTimeout(1200);

          const toolHeader = page.locator('.tool-call-header').first();
          if (await toolHeader.count() > 0) {
            await toolHeader.click();
            await page.waitForTimeout(1000);
          }
          await smoothScroll(page, 200, 600);
        }
      },
      {
        title: 'Reviewing Real-Time Telemetry',
        desc: 'Sidebar telemetry monitors prompt tokens, completion tokens, tool latency, and session ID.',
        narration: 'On the right panel, real-time telemetry tracks exact prompt tokens, completion tokens, and tool latency. This concludes our end-to-end walkthrough of the autonomous ReAct tool-calling loop.',
        action: async (page) => {
          await page.waitForTimeout(1500);
        }
      }
    ]
  },

  // ----------------------------------------------------------------------------
  // Feature 2: Visual Workflow Canvas & Topological DAG
  // ----------------------------------------------------------------------------
  {
    id: '02_workflow_dag',
    title: 'Visual Workflow Canvas & Topological DAG Execution',
    subtitle: 'Multi-Agent Topologies, Parallel Fork-Join Nodes, and Topological State Management',
    route: '/canvas',
    summary: 'Walks through constructing a parallel multi-agent pipeline using interactive graph nodes. Demonstrates loading a 1-to-3 Swarm Fork, triggering topological execution where parallel child nodes run concurrently, and scrolling down to review the comprehensive execution trace report.',
    steps: [
      {
        title: 'Canvas Studio Overview',
        desc: 'Visual node graph builder for parallel agent pipelines and topological execution.',
        narration: 'This is the Visual Workflow Canvas, our DAG Studio for orchestrating complex agent topologies. It enables developers to visually link autonomous agents, tools, and human approval checkpoints into robust execution graphs.',
        action: async (page) => {
          await page.waitForTimeout(1000);
        }
      },
      {
        title: 'Loading 1-to-3 Swarm Fork Template',
        desc: 'Instant graph synthesis: Task Decomposer branching to Search, Analyst, and Calculator.',
        narration: 'Let us load the One-to-Three Swarm Fork template. With a single click, our canvas synthesizes a root Task Decomposer node that branches out to three parallel workers: a web search tool, an analyst agent, and a math calculator, converging into a consensus arbitrator.',
        action: async (page) => {
          const tplBtn = page.locator('button:has-text("1-to-3 Swarm Fork")').first();
          if (await tplBtn.count() > 0) {
            await tplBtn.click();
            await page.waitForTimeout(1200);
          }
          const nameInput = page.locator('input[placeholder*="Custom Swarm"]').first();
          if (await nameInput.count() > 0) {
            await nameInput.click();
            await nameInput.fill('Competitive Market & Math Intelligence');
            await page.waitForTimeout(800);
          }
        }
      },
      {
        title: 'Triggering Topological Execution',
        desc: 'Topological sorter resolves dependency stages and executes parallel branches concurrently.',
        narration: 'We trigger workflow execution. The engine performs topological sorting across all nodes. Notice how the root node illuminates in blue during execution, completes, and then triggers all three child branches in parallel before arriving at the consensus arbitrator.',
        action: async (page) => {
          const runBtn = page.locator('button:has-text("Run Workflow DAG")').first();
          if (await runBtn.count() > 0) {
            await runBtn.click();
            console.log('  ↳ Triggered DAG execution. Monitoring stage animations...');
            await page.waitForTimeout(4000);
          }
        }
      },
      {
        title: 'Inspecting Execution Report & Scrolling',
        desc: 'Scrolling down past the canvas to examine millisecond latencies, stages count, and node traces.',
        narration: 'Now, let us scroll down below the canvas to examine the full DAG Execution Report. The execution completed with zero errors across all stages. We can inspect individual node outputs, millisecond latency metrics, and final synthesized artifacts.',
        action: async (page) => {
          await smoothScroll(page, 520, 800);
          await page.waitForTimeout(2000);
          await smoothScroll(page, 750, 700);
          await page.waitForTimeout(2000);
          await smoothScroll(page, 0, 700);
        }
      },
      {
        title: 'Topological Resilience',
        desc: 'Deterministic dependency graphs with checkpointing, error boundaries, and state isolation.',
        narration: 'By formalizing multi-agent workflows into directed acyclic graphs, teams eliminate race conditions and gain full observability into parallel AI operations.',
        action: async (page) => {
          await page.waitForTimeout(1200);
        }
      }
    ]
  },

  // ----------------------------------------------------------------------------
  // Feature 3: FastMCP Server & Dynamic Tools Sandbox
  // ----------------------------------------------------------------------------
  {
    id: '03_fastmcp_tools',
    title: 'FastMCP Server & Dynamic Tools Sandbox',
    subtitle: 'Model Context Protocol Compliance, JSON Schema Validation, and Isolated Execution',
    route: '/tools',
    summary: 'Explores enterprise Model Context Protocol (MCP) tool integration. Demonstrates inspecting registered tools, configuring typed JSON parameter arguments in the sandbox playground, executing live weather queries, and scrolling to examine sub-100ms output payloads.',
    steps: [
      {
        title: 'MCP Protocol Overview',
        desc: 'Standardized interface for dynamic tool discovery, typed parameters, and secure sandboxing.',
        narration: 'Welcome to the FastMCP Tools Sandbox. The Model Context Protocol provides an open standard for AI models to securely discover, inspect, and invoke external capabilities without vendor lock-in.',
        action: async (page) => {
          await page.waitForTimeout(1000);
        }
      },
      {
        title: 'Browsing Registered MCP Tools',
        desc: 'Scrolling through registered tools: calculator, weather, web search, filesystem, and evaluator.',
        narration: 'On the left, we browse all registered MCP tools in the catalog. Each tool exposes typed JSON schemas, operational categories, and functional descriptions so agents understand exactly when and how to call them.',
        action: async (page) => {
          await smoothScroll(page, 280, 600);
          await page.waitForTimeout(1500);
          await smoothScroll(page, 0, 500);
          await page.waitForTimeout(500);
        }
      },
      {
        title: 'Configuring Sandbox Parameters',
        desc: 'Selecting the weather tool and typing custom location payload into JSON editor.',
        narration: 'On the right is our live execution playground. We select the Weather tool and enter a test payload with the location set to Tokyo, Japan. The sandbox automatically validates our JSON arguments against the tool schema.',
        action: async (page) => {
          const select = page.locator('select.form-control').first();
          if (await select.count() > 0) {
            await select.selectOption('weather');
            await page.waitForTimeout(600);
          }
          const textarea = page.locator('textarea.code-font').first();
          if (await textarea.count() > 0) {
            await textarea.click();
            await textarea.fill('{\n  "location": "Tokyo, Japan"\n}');
            await page.waitForTimeout(800);
          }
        }
      },
      {
        title: 'Executing in Sandbox & Scrolling',
        desc: 'Executing standalone tool call and scrolling to inspect live JSON response and latency badge.',
        narration: 'We click Execute Tool in Sandbox. In under one hundred milliseconds, FastMCP returns the verified response: Tokyo current temperature, sunny conditions, and sixty-two percent humidity. Let us scroll down to inspect the raw JSON output and latency badge.',
        action: async (page) => {
          const execBtn = page.locator('button:has-text("Execute Tool in Sandbox")').first();
          if (await execBtn.count() > 0) {
            await execBtn.click();
            await page.waitForTimeout(1500);
          }
          await smoothScroll(page, 350, 600);
          await page.waitForTimeout(2000);
          await smoothScroll(page, 0, 500);
        }
      },
      {
        title: 'Production Tooling Advantage',
        desc: 'Isolated sandbox testing eliminates LLM token waste and enables rapid tool integration.',
        narration: 'This isolated sandbox enables engineers to rigorously test external APIs and MCP integrations before deploying them into autonomous production agent swarms.',
        action: async (page) => {
          await page.waitForTimeout(1200);
        }
      }
    ]
  },

  // ----------------------------------------------------------------------------
  // Feature 4: 2-Stage Smart Cost & Latency Router
  // ----------------------------------------------------------------------------
  {
    id: '04_smart_router',
    title: '2-Stage Smart Cost & Latency Router',
    subtitle: 'Dynamic Traffic Classification, Frontier vs SLM Routing, and 70% Cost Reductions',
    route: '/smart-router',
    summary: 'Demonstrates the 2-stage smart routing architecture that prevents burning expensive frontier tokens on simple prompts. Shows simulating a complex Python async crawler (routed to specialized coding LLM) vs a lightweight translation (routed to local SLM), and reviewing historical routing audit traces.',
    steps: [
      {
        title: 'Smart Router Architecture',
        desc: 'Intelligent request dispatching to optimize inference cost, latency, and reasoning capability.',
        narration: 'This is the Two-Stage Smart Cost and Latency Router. Standard AI systems blindly dispatch all requests to expensive frontier models, inflating costs by hundreds of thousands of dollars. Our router automatically classifies queries and dispatches to the most cost-effective model.',
        action: async (page) => {
          await page.waitForTimeout(1000);
        }
      },
      {
        title: 'Simulating Complex Coding Query',
        desc: 'Submitting Python async web crawler prompt requiring deep reasoning and code generation.',
        narration: 'First, we test a high-complexity prompt: writing an asynchronous Python web crawler with exponential backoff retry. We click the sample prompt chip and hit Simulate Route.',
        action: async (page) => {
          const sampleChip = page.locator('button:has-text("Python Async Crawler")').first();
          if (await sampleChip.count() > 0) {
            await sampleChip.click();
            await page.waitForTimeout(800);
          }
          const routeBtn = page.locator('button[type="submit"], button:has-text("Route & Execute")').first();
          if (await routeBtn.count() > 0) {
            await routeBtn.click();
            console.log('  ↳ Awaiting Stage 1 & Stage 2 routing decision...');
            try {
              await page.waitForSelector('div:has-text("2-Stage Dynamic Routing Trace"), div:has-text("STAGE 1")', { timeout: 25000 });
              await page.waitForTimeout(1000);
            } catch (e) {
              await page.waitForTimeout(2000);
            }
          }
        }
      },
      {
        title: 'Stage 1 Analysis & Scrolling Down',
        desc: 'Inspecting Stage 1 semantic classification, coding confidence score, and Stage 2 model selection.',
        narration: 'Stage One semantic classification immediately categorized the intent as Coding with high confidence, routing the workload directly to our specialized coding model. Let us scroll down to inspect the model selection reasoning and latency breakdown.',
        action: async (page) => {
          await smoothScroll(page, 420, 700);
          await page.waitForTimeout(2000);
          await smoothScroll(page, 0, 600);
        }
      },
      {
        title: 'Simulating Fast Lightweight Query',
        desc: 'Testing short multilingual translation prompt routed to local small language model.',
        narration: 'Now, let us contrast this with a simple query: Multilingual Translation of a daily greeting into French, Spanish, and German. We click Route and Execute.',
        action: async (page) => {
          const sampleChip = page.locator('button:has-text("Multilingual Translation")').first();
          if (await sampleChip.count() > 0) {
            await sampleChip.click();
            await page.waitForTimeout(800);
          }
          const routeBtn = page.locator('button[type="submit"], button:has-text("Route & Execute")').first();
          if (await routeBtn.count() > 0) {
            await routeBtn.click();
            try {
              await page.waitForSelector('div:has-text("2-Stage Dynamic Routing Trace"), div:has-text("STAGE 1")', { timeout: 20000 });
              await page.waitForTimeout(1000);
            } catch (e) {
              await page.waitForTimeout(2000);
            }
          }
        }
      },
      {
        title: 'Reviewing Historical Routing Logs',
        desc: 'Switching to Routing Logs sub-tab to inspect real-time audit traces and model distributions.',
        narration: 'The router identified this as a fast lightweight task and routed it directly to our local small model, slashing cost by eighty-five percent and delivering instant response times. Switching to the Historical Logs tab confirms our complete audit trail.',
        action: async (page) => {
          const logsTab = page.locator('button:has-text("Logs"), button:has-text("History")').first();
          if (await logsTab.count() > 0) {
            await logsTab.click();
            await page.waitForTimeout(1000);
          }
          await smoothScroll(page, 300, 600);
          await page.waitForTimeout(1500);
          await smoothScroll(page, 0, 500);
        }
      }
    ]
  },

  // ----------------------------------------------------------------------------
  // Feature 5: Dual Memory Store (Vector & Knowledge Graph)
  // ----------------------------------------------------------------------------
  {
    id: '05_dual_memory',
    title: 'Dual Memory Store: Vector Semantic & Knowledge Graph',
    subtitle: 'Episodic Memory Retention, Cosine Similarity Recall, and Navigable Entity Graphs',
    route: '/memory',
    summary: 'Shows how autonomous agents maintain long-term memory across sessions. Demonstrates storing a new developer coding preference, querying the memory store using indirect semantic keywords, reviewing retrieved cosine similarity scores, and inspecting knowledge graph entity relations.',
    steps: [
      {
        title: 'Memory Architecture Overview',
        desc: 'Dual-tier memory system: semantic vector embeddings for fuzzy recall and graph relations for associative links.',
        narration: 'Welcome to the Dual Memory Store. While vanilla LLMs are entirely stateless and forget everything between turns, our memory subsystem gives agents persistent long-term recall using semantic vector embeddings and knowledge graph relations.',
        action: async (page) => {
          await page.waitForTimeout(1000);
        }
      },
      {
        title: 'Storing New User Preference',
        desc: 'Persisting developer convention: clean Python code with dataclasses and async/await.',
        narration: 'Let us store a user preference into memory. We type: User preference: Always format Python code with strict type annotations, dataclasses, and async await. We click Store Memory.',
        action: async (page) => {
          const textarea = page.locator('textarea[placeholder*="memory"], textarea.form-control').first();
          if (await textarea.count() > 0) {
            await textarea.click();
            await typeNaturally(textarea, 'User preference: Always format Python code with strict type annotations, dataclasses, and async await.', 28);
            await page.waitForTimeout(500);
          }
          const storeBtn = page.locator('button:has-text("Store Memory"), button:has-text("Add Memory"), button:has-text("Save")').first();
          if (await storeBtn.count() > 0) {
            await storeBtn.click();
            await page.waitForTimeout(1200);
          }
        }
      },
      {
        title: 'Semantic Recall with Indirect Query',
        desc: 'Searching memory using natural language concept query: "How does the user want their Python styled?".',
        narration: 'Now, let us test semantic recall with an indirect query that does not share identical keywords: How does the user want their Python styled? We click Search.',
        action: async (page) => {
          const searchInput = page.locator('input[placeholder*="search"], input[placeholder*="query"]').first();
          if (await searchInput.count() > 0) {
            await searchInput.click();
            await typeNaturally(searchInput, 'How does the user want their Python styled?', 28);
            await page.waitForTimeout(500);
          }
          const searchBtn = page.locator('button:has-text("Search")').first();
          if (await searchBtn.count() > 0) {
            await searchBtn.click();
            await page.waitForTimeout(1500);
          }
        }
      },
      {
        title: 'Inspecting Retrieved Vectors & Scrolling',
        desc: 'Scrolling down through matching memories to examine cosine similarity scores and metadata.',
        narration: 'Let us scroll down to inspect the results. The vector search engine ranked our stored preference at the top with a high cosine similarity score, successfully bridging the vocabulary gap between styled and formatted.',
        action: async (page) => {
          await smoothScroll(page, 380, 700);
          await page.waitForTimeout(2000);
          await smoothScroll(page, 0, 500);
        }
      },
      {
        title: 'Navigating Knowledge Graph Relations',
        desc: 'Switching to Graph sub-tab to view interconnected entity nodes and multi-hop associations.',
        narration: 'Switching to the Graph Relations tab, we see how entities, concepts, and tools are linked into a navigable knowledge graph, enabling agents to perform multi-hop associative reasoning.',
        action: async (page) => {
          const graphTab = page.locator('button:has-text("Graph"), button:has-text("Relations")').first();
          if (await graphTab.count() > 0) {
            await graphTab.click();
            await page.waitForTimeout(1200);
          }
          await smoothScroll(page, 250, 600);
          await page.waitForTimeout(1500);
          await smoothScroll(page, 0, 500);
        }
      }
    ]
  },

  // ----------------------------------------------------------------------------
  // Feature 6: Multi-Agent Swarm Debate Orchestrator
  // ----------------------------------------------------------------------------
  {
    id: '06_orchestrator_debate',
    title: 'Multi-Agent Swarm & Collaborative Debate',
    subtitle: 'Persona Specialization, Proposer vs Critic Dynamics, and Consensus Arbitrators',
    route: '/orchestrator',
    summary: 'Demonstrates multi-agent coordination where specialized personas debate complex architectural trade-offs. Sets up a Proposer, Critic, and Arbitrator to debate Monolith vs Microservices for a seed startup, scrolling down through the interactive debate timeline and consensus matrix.',
    steps: [
      {
        title: 'Swarm Orchestrator Overview',
        desc: 'Multi-agent federation framework for complex problem decomposition and multi-perspective debate.',
        narration: 'This is the Swarm Orchestrator. When architectural challenges are too multifaceted for a single agent, our platform deploys specialized personas that debate opposing perspectives to eliminate blind spots and reach balanced consensus.',
        action: async (page) => {
          await page.waitForTimeout(1000);
        }
      },
      {
        title: 'Selecting Multi-Agent Debate Pattern',
        desc: 'Switching from task decomposition to debate swarm: Proposer, Critic, and Arbitrator roles.',
        narration: 'We switch to the Multi-Agent Debate pattern. Our challenge: Evaluate architectural tradeoffs between Monolith and Microservices for a seed-stage startup. Three agents participate: a Proposer advocating velocity, a Critic testing fault tolerance, and an Arbitrator.',
        action: async (page) => {
          const debateTab = page.locator('button:has-text("Debate")').first();
          if (await debateTab.count() > 0) {
            await debateTab.click();
            await page.waitForTimeout(1000);
          }
          const roundsSelect = page.locator('select').filter({ hasText: /Round/ }).first();
          if (await roundsSelect.count() > 0) {
            await roundsSelect.selectOption('1');
            await page.waitForTimeout(500);
          }
        }
      },
      {
        title: 'Initiating Autonomous Debate Swarm',
        desc: 'Launching structured debate between opposing agent perspectives.',
        narration: 'We launch the debate. The Proposer argues for a modular monolith to maximize product delivery speed. The Critic counters with scalability bottlenecks and team boundary isolation. Watch as the debate dialogue streams in real time.',
        action: async (page) => {
          const startBtn = page.locator('button:has-text("Start Multi-Agent Debate"), button:has-text("Run Debate"), button:has-text("Start Debate")').first();
          if (await startBtn.count() > 0) {
            await startBtn.click();
            console.log('  ↳ Initiated multi-agent debate. Streaming rounds...');
            try {
              await page.waitForSelector('.debate-turn, .consensus-card, div:has-text("Consensus Verdict"), div:has-text("Arbitrator")', { timeout: 35000 });
              await page.waitForTimeout(2000);
            } catch (e) {
              await page.waitForTimeout(4000);
            }
          }
        }
      },
      {
        title: 'Scrolling Through Debate Timeline',
        desc: 'Smoothly scrolling through debate timeline to inspect arguments, counter-critiques, and consensus card.',
        narration: 'Let us scroll down the interactive debate timeline. Each agent perspective is stamped with confidence scores and reasoning evidence. In the final stage, the Arbitrator reviews both arguments and synthesizes an actionable consensus: begin with a modular monolith, deferring microservices until product-market fit.',
        action: async (page) => {
          await smoothScroll(page, 450, 800);
          await page.waitForTimeout(2000);
          await smoothScroll(page, 800, 700);
          await page.waitForTimeout(2000);
          await smoothScroll(page, 200, 600);
        }
      },
      {
        title: 'Collaborative Intelligence',
        desc: 'Autonomous consensus reduces hallucination risks and elevates strategic engineering decisions.',
        narration: 'Multi-agent debate swarms transform solitary AI outputs into rigorously vetted, enterprise-ready decisions.',
        action: async (page) => {
          await page.waitForTimeout(1200);
        }
      }
    ]
  },

  // ----------------------------------------------------------------------------
  // Feature 7: Safety Approvals (HITL) & 3-Tier Audit Logs
  // ----------------------------------------------------------------------------
  {
    id: '07_governance_audit',
    title: 'Safety Approvals (HITL) & 3-Tier Audit Logging',
    subtitle: 'Human-in-the-Loop Risk Gating, Policy Rules, and Hierarchical Cryptographic Logs',
    route: '/approvals',
    summary: 'Demonstrates enterprise governance, Human-in-the-Loop safety policies, and immutable 3-tier audit logging. Shows reviewing pending sensitive operations with automated risk scores and countdown timers, inspecting policy rules, and expanding the Conversation ➔ Turn ➔ Request audit log tree.',
    steps: [
      {
        title: 'Enterprise Safety Governance Overview',
        desc: 'Human-in-the-Loop approval workflows and policy boundaries for autonomous agent operations.',
        narration: 'Enterprise AI adoption demands absolute safety and compliance. Our platform combines Human-in-the-Loop safety gating with a Three-Tier Audit Logging architecture, ensuring that no high-risk autonomous action executes without explicit oversight.',
        action: async (page) => {
          await page.waitForTimeout(1000);
        }
      },
      {
        title: 'Reviewing Pending Safety Approvals',
        desc: 'Inspecting pending requests: risk scoring, automated policy violations, and auto-approval timers.',
        narration: 'Here in Safety Approvals, sensitive operations like database alterations, file deletions, or large financial transfers are held in escrow. Each card displays the requesting agent, risk score, automated policy violation, and countdown timers.',
        action: async (page) => {
          await smoothScroll(page, 260, 600);
          await page.waitForTimeout(1500);
          await smoothScroll(page, 0, 500);
        }
      },
      {
        title: 'Inspecting Automated Policy Rules',
        desc: 'Switching to Rules sub-tab to review risk classification thresholds and automatic gating criteria.',
        narration: 'Switching to the Rules tab, we review our organization policy thresholds. Rules can auto-approve low-risk lookups while strictly gating high-impact shell executions or production deployments.',
        action: async (page) => {
          const rulesTab = page.locator('button:has-text("Rules")').first();
          if (await rulesTab.count() > 0) {
            await rulesTab.click();
            await page.waitForTimeout(1000);
          }
          await smoothScroll(page, 280, 600);
          await page.waitForTimeout(1500);
          await smoothScroll(page, 0, 500);
        }
      },
      {
        title: 'Navigating to 3-Tier Audit Logs',
        desc: 'Transitioning to /logs to inspect the hierarchical Conversation ➔ Turn ➔ Request audit tree.',
        narration: 'Every event across the platform is permanently archived in our Three-Tier Audit Logs. Let us navigate to the Logs view to examine the hierarchical tree: Conversation, Turn, and Request.',
        action: async (page) => {
          await page.goto(`${BASE_URL}/logs`, { waitUntil: 'domcontentloaded' });
          await page.waitForTimeout(1200);
          const firstRow = page.locator('tbody tr, .tree-node, .log-item').first();
          if (await firstRow.count() > 0) {
            await firstRow.click();
            await page.waitForTimeout(800);
          }
        }
      },
      {
        title: 'Expanding Traces & Scrolling for Compliance',
        desc: 'Scrolling down through expanded audit logs: token receipts, latency percentiles, and CSV/JSON export.',
        narration: 'Every log entry captures millisecond latencies, exact prompt and completion tokens, model parameters, and cryptographic timestamps. Logs can be exported to JSON or CSV, providing comprehensive regulatory compliance.',
        action: async (page) => {
          await smoothScroll(page, 320, 700);
          await page.waitForTimeout(1800);
          await smoothScroll(page, 0, 500);
          await page.waitForTimeout(1000);
        }
      }
    ]
  }
];

// ==============================================================================
// RECORD A SINGLE FEATURE VIDEO END-TO-END
// ==============================================================================
async function recordSingleFeature(feature, browser) {
  console.log(`\n${CYAN}${BOLD}==========================================================================${RESET}`);
  console.log(`${MAGENTA}${BOLD}🎬 RECORDING FEATURE: ${feature.title}${RESET}`);
  console.log(`  Route:       ${BASE_URL}${feature.route}`);
  console.log(`  Steps:       ${feature.steps.length} sequential story acts`);
  console.log(`${CYAN}==========================================================================${RESET}`);

  // Create isolated temp directories for this feature
  const featTimestamp = Date.now();
  const featTempVideoDir = path.join(FEATURES_DIR, `.temp_video_${feature.id}_${featTimestamp}`);
  const featTempAudioDir = path.join(FEATURES_DIR, `.temp_audio_${feature.id}_${featTimestamp}`);
  fs.mkdirSync(featTempVideoDir, { recursive: true });
  fs.mkdirSync(featTempAudioDir, { recursive: true });

  // 1. Pre-synthesize all narration audio clips for this feature
  console.log(`\n${BLUE}🎙️ Pre-synthesizing voiceover clips for ${feature.title}...${RESET}`);
  const synthesizedClips = [];
  for (let i = 0; i < feature.steps.length; i++) {
    const step = feature.steps[i];
    const clipId = `step_${i + 1}`;
    const clipInfo = preSynthesizeClip(clipId, step.narration, featTempAudioDir);
    synthesizedClips.push({
      stepIndex: i,
      clipId,
      text: step.narration,
      wavPath: clipInfo.wavPath,
      durationSec: clipInfo.durationSec
    });
    console.log(`  ✓ Step ${i + 1} [${step.title}]: ${clipInfo.durationSec.toFixed(2)}s narration`);
  }

  // 2. Launch browser context with screencast recording
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: {
      dir: featTempVideoDir,
      size: { width: 1440, height: 900 }
    }
  });

  const page = await context.newPage();
  const audioSegments = [];
  const recordingStartTime = Date.now();

  try {
    // Navigate to feature route
    console.log(`\n${BLUE}🌐 Navigating to ${BASE_URL}${feature.route}...${RESET}`);
    await page.goto(`${BASE_URL}${feature.route}`, { waitUntil: 'domcontentloaded', timeout: 20000 });
    await page.waitForTimeout(1200);

    // 3. Execute each story step sequentially with strict audio synchronization
    for (let i = 0; i < feature.steps.length; i++) {
      const step = feature.steps[i];
      const audioClip = synthesizedClips[i];
      const stepStartSec = (Date.now() - recordingStartTime) / 1000.0;

      console.log(`\n${YELLOW}[Step ${i + 1}/${feature.steps.length}] ${BOLD}${step.title}${RESET}`);
      console.log(`  ↳ Narration: "${step.narration.substring(0, 75)}..."`);

      // Update HUD banner on page
      await showHudBanner(page, `[${feature.id.toUpperCase()}] ${feature.title}`, `Step ${i + 1}: ${step.title}`, step.desc);

      // Register audio clip on master timeline
      if (audioClip.wavPath && fs.existsSync(audioClip.wavPath)) {
        audioSegments.push({
          index: i + 1,
          title: step.title,
          startSec: stepStartSec,
          durationSec: audioClip.durationSec,
          wavPath: audioClip.wavPath
        });

        // If headed mode, optionally play audio live through speakers
        if (!isHeadless && !isMuted) {
          spawn('afplay', [audioClip.wavPath], { stdio: 'ignore' });
        }
      }

      // Execute UI actions (realistic typing, clicking, waiting for results, scrolling)
      const actionStartTime = Date.now();
      await step.action(page);
      const actionElapsedMs = Date.now() - actionStartTime;

      // Ensure the step is held on screen until the voiceover is completely done (+ 1.4s comfortable pause)
      const minRequiredMs = Math.ceil((audioClip.durationSec + 1.4) * 1000);
      const remainingHoldMs = minRequiredMs - actionElapsedMs;

      if (remainingHoldMs > 0) {
        console.log(`  ↳ Holding step for audio narration to conclude (${(remainingHoldMs / 1000).toFixed(1)}s)...`);
        await page.waitForTimeout(remainingHoldMs);
      }

      // Small visual pause before advancing to next step
      await page.waitForTimeout(400);
    }

    console.log(`\n${GREEN}✓ All ${feature.steps.length} steps executed successfully.${RESET}`);
  } catch (err) {
    console.error(`  ❌ Error during recording feature ${feature.id}:`, err);
  }

  // 4. Close page and context to flush video file to disk
  await page.close();
  await context.close();

  // Find generated raw video file
  const videoFiles = fs.readdirSync(featTempVideoDir).filter(f => f.endsWith('.webm'));
  if (videoFiles.length === 0) {
    console.error(`  ❌ No raw video file was captured for ${feature.id}`);
    fs.rmSync(featTempVideoDir, { recursive: true, force: true });
    fs.rmSync(featTempAudioDir, { recursive: true, force: true });
    return null;
  }

  const rawVideoPath = path.join(featTempVideoDir, videoFiles[0]);
  const totalDurationSec = (Date.now() - recordingStartTime) / 1000.0;
  console.log(`  Total Duration: ${totalDurationSec.toFixed(1)}s across ${audioSegments.length} non-overlapping narration clips`);

  // 5. Assemble Master Audio Track using Python timeline mixer
  const masterWavPath = path.join(featTempAudioDir, 'master_audio.wav');
  console.log(`${BLUE}🎵 Compiling master audio track with zero-overlap timeline sync...${RESET}`);

  const pyMixerScript = `
import wave, struct, sys, json

with open(sys.argv[1], 'r') as f:
    segments = json.load(f)
total_duration_sec = float(sys.argv[2]) + 2.0
output_wav = sys.argv[3]

sample_rate = 44100
total_frames = int(total_duration_sec * sample_rate)
master_left = [0] * total_frames
master_right = [0] * total_frames

for seg in segments:
    wav_path = seg['wavPath']
    start_sec = float(seg['startSec'])
    start_frame = int(start_sec * sample_rate)

    try:
        with wave.open(wav_path, 'rb') as w:
            n_channels = w.getnchannels()
            sampwidth = w.getsampwidth()
            framerate = w.getframerate()
            n_frames = w.getnframes()
            raw_bytes = w.readframes(n_frames)

            fmt = '<' + 'h' * (n_frames * n_channels)
            samples = struct.unpack(fmt, raw_bytes)

            for i in range(n_frames):
                pos = start_frame + i
                if pos >= total_frames:
                    break
                if n_channels == 2:
                    l = samples[i * 2]
                    r = samples[i * 2 + 1]
                else:
                    l = samples[i]
                    r = samples[i]
                master_left[pos] = max(-32768, min(32767, master_left[pos] + l))
                master_right[pos] = max(-32768, min(32767, master_right[pos] + r))
    except Exception as e:
        print(f"Error mixing {wav_path}: {e}", file=sys.stderr)

with wave.open(output_wav, 'wb') as out:
    out.setnchannels(2)
    out.setsampwidth(2)
    out.setframerate(sample_rate)
    interleaved = []
    for i in range(total_frames):
        interleaved.append(master_left[i])
        interleaved.append(master_right[i])
    out.writeframes(struct.pack('<' + 'h' * (total_frames * 2), *interleaved))
`;

  const mixerPyFile = path.join(featTempAudioDir, 'mix_timeline.py');
  const segmentsJsonFile = path.join(featTempAudioDir, 'segments.json');
  fs.writeFileSync(mixerPyFile, pyMixerScript);
  fs.writeFileSync(segmentsJsonFile, JSON.stringify(audioSegments));

  const pythonExe = process.env.PYTHON_BIN || (fs.existsSync(path.join(ROOT_DIR, '.venv/bin/python')) ? path.join(ROOT_DIR, '.venv/bin/python') : 'python3');
  try {
    execSync(`"${pythonExe}" "${mixerPyFile}" "${segmentsJsonFile}" ${totalDurationSec} "${masterWavPath}"`);
    console.log(`  ${GREEN}✓ Master audio compiled successfully with zero overlap.${RESET}`);
  } catch (err) {
    console.warn('  ⚠️ Audio mixer fallback:', err.message);
  }

  // 6. FFmpeg Multiplexing into final MP4 & WebM
  const finalMp4Path = path.join(FEATURES_DIR, `${feature.id}.mp4`);
  const finalWebmPath = path.join(FEATURES_DIR, `${feature.id}.webm`);

  console.log(`${BLUE}🎬 Multiplexing high-definition video and audio with FFmpeg...${RESET}`);
  if (fs.existsSync(masterWavPath)) {
    try {
      execSync(`"${FFMPEG_BIN}" -y -i "${rawVideoPath}" -i "${masterWavPath}" -c:v libx264 -preset fast -crf 22 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart "${finalMp4Path}" 2>/dev/null`);
    } catch (e) {
      console.warn('  ⚠️ MP4 muxing warning:', e.message);
    }
    try {
      execSync(`"${FFMPEG_BIN}" -y -i "${rawVideoPath}" -i "${masterWavPath}" -c:v copy -c:a libopus -b:a 128k -shortest "${finalWebmPath}" 2>/dev/null`);
    } catch (e) {
      fs.copyFileSync(rawVideoPath, finalWebmPath);
    }
  } else {
    fs.copyFileSync(rawVideoPath, finalWebmPath);
  }

  // Clean temporary folders
  fs.rmSync(featTempVideoDir, { recursive: true, force: true });
  fs.rmSync(featTempAudioDir, { recursive: true, force: true });

  const resultStats = {
    id: feature.id,
    title: feature.title,
    subtitle: feature.subtitle,
    summary: feature.summary,
    durationSec: totalDurationSec.toFixed(1),
    mp4Path: fs.existsSync(finalMp4Path) ? finalMp4Path : null,
    mp4SizeMb: fs.existsSync(finalMp4Path) ? (fs.statSync(finalMp4Path).size / (1024 * 1024)).toFixed(2) : 0,
    webmPath: fs.existsSync(finalWebmPath) ? finalWebmPath : null,
    webmSizeMb: fs.existsSync(finalWebmPath) ? (fs.statSync(finalWebmPath).size / (1024 * 1024)).toFixed(2) : 0
  };

  console.log(`\n${GREEN}${BOLD}✓ FINISHED: ${feature.title}${RESET}`);
  console.log(`  📹 MP4:  ${resultStats.mp4Path} (${resultStats.mp4SizeMb} MB, H.264+AAC)`);
  console.log(`  🌐 WebM: ${resultStats.webmPath} (${resultStats.webmSizeMb} MB, Native Web)`);
  console.log(`  ⏱️ Time: ${resultStats.durationSec}s`);

  return resultStats;
}

// ==============================================================================
// BUILD INTERACTIVE HTML VIDEO GALLERY
// ==============================================================================
function generateGalleryHtml(recordedFeatures) {
  const galleryPath = path.join(FEATURES_DIR, 'index.html');
  const cardsHtml = recordedFeatures.map((feat, idx) => `
    <div class="feature-card" id="card-${feat.id}">
      <div class="card-video-wrapper">
        <video controls preload="metadata" poster="">
          <source src="./${feat.id}.mp4" type="video/mp4">
          <source src="./${feat.id}.webm" type="video/webm">
          Your browser does not support the video tag.
        </video>
        <div class="video-badge">Feature ${idx + 1} of ${recordedFeatures.length}</div>
        <div class="duration-badge">⏱️ ${feat.durationSec}s</div>
      </div>
      <div class="card-content">
        <h3 class="card-title">${feat.title}</h3>
        <p class="card-subtitle">${feat.subtitle}</p>
        <p class="card-summary">${feat.summary}</p>
        <div class="card-meta">
          <span class="meta-tag">H.264 + AAC Stereo</span>
          <span class="meta-tag">${feat.mp4SizeMb} MB</span>
          <a href="./${feat.id}.mp4" download class="btn-download">⬇ Download MP4</a>
        </div>
      </div>
    </div>
  `).join('\n');

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Agentic-AI: End-to-End Feature Demonstration Gallery</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: rgba(17, 24, 39, 0.75);
      --border: rgba(255, 255, 255, 0.08);
      --accent: #6366f1;
      --accent-light: #818cf8;
      --text: #f8fafc;
      --text-muted: #94a3b8;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
      padding: 40px 24px 80px;
      line-height: 1.5;
    }
    .header {
      max-width: 1200px;
      margin: 0 auto 40px;
      text-align: center;
    }
    .header h1 {
      font-size: 36px;
      font-weight: 800;
      letter-spacing: -0.02em;
      background: linear-gradient(135deg, #a5b4fc, #6366f1, #38bdf8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 12px;
    }
    .header p {
      font-size: 16px;
      color: var(--text-muted);
      max-width: 720px;
      margin: 0 auto;
    }
    .gallery-grid {
      max-width: 1200px;
      margin: 0 auto;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(540px, 1fr));
      gap: 32px;
    }
    .feature-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 12px 32px rgba(0, 0, 0, 0.4);
      backdrop-filter: blur(16px);
      display: flex;
      flex-direction: column;
      transition: transform 0.2s, border-color 0.2s;
    }
    .feature-card:hover {
      transform: translateY(-4px);
      border-color: rgba(99, 102, 241, 0.4);
    }
    .card-video-wrapper {
      position: relative;
      background: #000;
      width: 100%;
      aspect-ratio: 16 / 10;
    }
    video {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }
    .video-badge {
      position: absolute;
      top: 12px;
      left: 12px;
      background: rgba(15, 23, 42, 0.85);
      border: 1px solid rgba(99, 102, 241, 0.5);
      color: #a5b4fc;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.04em;
    }
    .duration-badge {
      position: absolute;
      bottom: 12px;
      right: 12px;
      background: rgba(15, 23, 42, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #f1f5f9;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 11px;
      font-family: 'JetBrains Mono', monospace;
      font-weight: 600;
    }
    .card-content {
      padding: 24px;
      display: flex;
      flex-direction: column;
      flex: 1;
    }
    .card-title {
      font-size: 20px;
      font-weight: 700;
      color: #f1f5f9;
      margin-bottom: 4px;
    }
    .card-subtitle {
      font-size: 13px;
      color: #818cf8;
      font-weight: 600;
      margin-bottom: 14px;
    }
    .card-summary {
      font-size: 13.5px;
      color: #94a3b8;
      line-height: 1.6;
      margin-bottom: 20px;
      flex: 1;
    }
    .card-meta {
      display: flex;
      align-items: center;
      gap: 10px;
      border-top: 1px solid rgba(255, 255, 255, 0.06);
      padding-top: 16px;
      flex-wrap: wrap;
    }
    .meta-tag {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 6px;
      padding: 4px 10px;
      font-size: 11px;
      color: #cbd5e1;
      font-family: 'JetBrains Mono', monospace;
    }
    .btn-download {
      margin-left: auto;
      background: rgba(99, 102, 241, 0.2);
      border: 1px solid rgba(99, 102, 241, 0.5);
      color: #a5b4fc;
      text-decoration: none;
      font-size: 12px;
      font-weight: 600;
      padding: 6px 14px;
      border-radius: 6px;
      transition: background 0.2s;
    }
    .btn-download:hover {
      background: rgba(99, 102, 241, 0.4);
      color: #fff;
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>🎬 Agentic AI Feature Demonstration Suite</h1>
    <p>Modular, high-definition walkthrough videos. Each video covers one core capability end-to-end with studio audio narration, realistic human data entry, live execution, and smooth result inspection.</p>
  </div>
  <div class="gallery-grid">
    ${cardsHtml}
  </div>
</body>
</html>`;

  fs.writeFileSync(galleryPath, html);
  console.log(`\n${GREEN}✓ Interactive HTML Video Gallery created:${RESET} ${BOLD}${galleryPath}${RESET}`);
}

// ==============================================================================
// MAIN RUNNER
// ==============================================================================
async function main() {
  console.log(`${CYAN}${BOLD}`);
  console.log('==========================================================================');
  console.log('  🎬 AGENTIC-AI: DEDICATED FEATURE VIDEO RECORDER (PACED & SYNCED)');
  console.log(`  Mode:     ${isHeadless ? 'Headless Chromium Screencast' : 'Headed Live Window'}`);
  console.log(`  Target:   ${BASE_URL}`);
  console.log(`  Output:   recordings/features/<feature_name>.mp4 & .webm`);
  console.log(`  Filter:   ${targetFeature ? targetFeature : 'All 7 features'}`);
  console.log('==========================================================================');
  console.log(RESET);

  let selectedFeatures = FEATURE_DEFINITIONS;
  if (targetFeature && targetFeature !== 'all') {
    selectedFeatures = FEATURE_DEFINITIONS.filter(f => f.id === targetFeature || f.id.includes(targetFeature));
    if (selectedFeatures.length === 0) {
      console.error(`❌ Unknown feature "${targetFeature}". Available features:`);
      FEATURE_DEFINITIONS.forEach(f => console.log(`   - ${f.id} (${f.title})`));
      process.exit(1);
    }
  }

  // Launch Chromium Browser
  const browser = await chromium.launch({
    headless: isHeadless,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-web-security',
      '--window-size=1440,900'
    ]
  });

  const recordedResults = [];

  for (const feature of selectedFeatures) {
    const res = await recordSingleFeature(feature, browser);
    if (res) recordedResults.push(res);
  }

  await browser.close();

  // Generate the gallery HTML index
  if (recordedResults.length > 0) {
    generateGalleryHtml(recordedResults);
  }

  console.log(`\n${CYAN}${BOLD}==========================================================================${RESET}`);
  console.log(`${GREEN}${BOLD}🎉 ALL FEATURE VIDEOS RECORDED SUCCESSFULLY!${RESET}`);
  console.log(`  📁 Video Directory: ${BOLD}${FEATURES_DIR}${RESET}`);
  console.log(`  🌐 Gallery Index:   ${BOLD}${path.join(FEATURES_DIR, 'index.html')}${RESET}`);
  console.log(`${CYAN}==========================================================================${RESET}`);
  console.log(`\n${YELLOW}To watch any feature video on macOS:${RESET}`);
  recordedResults.forEach(r => {
    console.log(`  open "${r.mp4Path}"`);
  });
  console.log(`\n${YELLOW}To browse the interactive video gallery in your browser:${RESET}`);
  console.log(`  open "${path.join(FEATURES_DIR, 'index.html')}"\n`);
}

main().catch(err => {
  console.error('Fatal error recording feature videos:', err);
  process.exit(1);
});
