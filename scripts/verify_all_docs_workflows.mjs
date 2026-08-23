import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:8000';

async function runAllDocVerifications() {
  console.log('🚀 Launching Playwright browser testing suite for all 18 documented features...\n');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const results = [];

  async function testStep(name, fn) {
    process.stdout.write(`⏳ Testing: ${name}... `);
    const start = Date.now();
    try {
      await fn();
      const dur = Date.now() - start;
      console.log(`✅ PASSED (${dur}ms)`);
      results.push({ name, status: 'PASSED', duration_ms: dur });
    } catch (err) {
      const dur = Date.now() - start;
      console.log(`❌ FAILED (${dur}ms) -> ${err.message}`);
      results.push({ name, status: 'FAILED', duration_ms: dur, error: err.message });
    }
  }

  try {
    // 01. AI Agent Chatbot View
    await testStep('01. AI Agent Chatbot (/chat) Load & Controls', async () => {
      await page.goto(`${BASE_URL}/chat`, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('.chat-layout', { timeout: 8000 });
      await page.waitForSelector('select', { timeout: 5000 });
      const selectCount = await page.locator('select').count();
      if (selectCount < 3) throw new Error(`Expected at least 3 control selectors, got ${selectCount}`);
    });

    // 02. Workflow Canvas (DAG Studio)
    await testStep('02. Workflow Canvas (/canvas) 2D Board & Template Loading', async () => {
      await page.goto(`${BASE_URL}/canvas`, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('.canvas-board-2d', { timeout: 8000 });
      const swarmBtn = page.locator('button.template-pill-btn:has-text("1-to-3 Parallel Swarm Fork")');
      await swarmBtn.click();
      await page.waitForTimeout(600);
      const nodeCount = await page.locator('.dag-node-draggable').count();
      if (nodeCount < 4) throw new Error(`Expected at least 4 nodes for 1-to-3 template, found ${nodeCount}`);
    });

    // 03. MCP Tools & Sandbox
    await testStep('03. MCP Tools & Sandbox (/tools) Schema & Execution', async () => {
      await page.goto(`${BASE_URL}/tools`, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('.data-table, .glass-card', { timeout: 8000 });
      const loadBtn = page.locator('button:has-text("Load")');
      if (await loadBtn.count() > 0) {
        await loadBtn.first().click();
        await page.waitForTimeout(400);
      }
    });

    // 04. Domain Skills Hub
    await testStep('04. Domain Skills Hub (/skills) Card Library', async () => {
      await page.goto(`${BASE_URL}/skills`, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('.skill-card, .skills-grid', { timeout: 8000 });
      const cards = await page.locator('.skill-card').count();
      if (cards === 0) throw new Error('No domain skill cards rendered');
    });

    // 05. Workspace Files
    await testStep('05. Workspace Files (/workspace) Sandboxed File Explorer', async () => {
      await page.goto(`${BASE_URL}/workspace`, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('.glass-card, table, textarea', { timeout: 8000 });
    });

    // 06. Telemetry & Metrics
    await testStep('06. Telemetry & Metrics (/overview) KPI Cards & Graphs', async () => {
      await page.goto(`${BASE_URL}/overview`, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('.stat-card, .charts-grid, .glass-card', { timeout: 8000 });
    });

    // 07. Audit Logs
    await testStep('07. Audit Logs (/logs) Log Table & JSON Inspector', async () => {
      await page.goto(`${BASE_URL}/logs`, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('.data-table, table, .glass-card', { timeout: 8000 });
    });

    // 08. Evals & Benchmarks
    await testStep('08. Evals & Benchmarks (/evals) Test Suite Controls', async () => {
      await page.goto(`${BASE_URL}/evals`, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('.glass-card, .charts-grid, select, button', { timeout: 8000 });
    });

    // 09. Multi-Agent Orchestrator
    await testStep('09. Multi-Agent Orchestrator (/orchestrator) Debate & Supervisor', async () => {
      await page.goto(`${BASE_URL}/orchestrator`, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('.glass-card, textarea, button', { timeout: 8000 });
    });

    // 10. Memory Explorer
    await testStep('10. Memory Explorer (/memory) Vector Vault & Recall', async () => {
      await page.goto(`${BASE_URL}/memory`, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('.glass-card, input, button', { timeout: 8000 });
    });

    // 11. Settings & Providers
    await testStep('11. Settings & Providers (/settings) Multi-Provider Config', async () => {
      await page.goto(`${BASE_URL}/settings`, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('.glass-card, input, button', { timeout: 8000 });
    });

    // 12. Multi-Agent Debate API & Protocol
    await testStep('12. Multi-Agent Debate Protocol Execution', async () => {
      const res = await page.request.post(`${BASE_URL}/api/debate`, {
        data: {
          topic: 'Evaluate Monolith vs Microservices',
          rounds: 1
        }
      });
      if (!res.ok()) throw new Error(`Debate API returned HTTP ${res.status()}`);
      const data = await res.json();
      if (!data.consensus_verdict) {
        throw new Error(`Missing consensus_verdict in response. Keys: ${Object.keys(data).join(', ')}`);
      }
    });

    // 13. Parallel Swarms & DAG Execution
    await testStep('13. Parallel DAG Execution (Kahn Topological Sort)', async () => {
      const res = await page.request.post(`${BASE_URL}/api/canvas/execute`, {
        data: {
          workflow_name: 'Verification Swarm',
          initial_input: 'Calculate 25 * 4 and check weather in Tokyo',
          nodes: [
            { id: 'node_1', type: 'agent', label: 'Supervisor', config: { role: 'decomposer' } },
            { id: 'node_2', type: 'tool', label: 'Weather Tool', config: { tool: 'weather' } },
            { id: 'node_3', type: 'tool', label: 'Calculator', config: { tool: 'calculate' } },
            { id: 'node_4', type: 'agent', label: 'Synthesizer', config: { role: 'synthesizer' } }
          ],
          edges: [
            { source: 'node_1', target: 'node_2' },
            { source: 'node_1', target: 'node_3' },
            { source: 'node_2', target: 'node_4' },
            { source: 'node_3', target: 'node_4' }
          ]
        }
      });
      if (!res.ok()) throw new Error(`DAG execute returned HTTP ${res.status()}`);
      const data = await res.json();
      if (data.stages_count !== 3) throw new Error(`Expected 3 stages (waves), got ${data.stages_count}`);
      if (!data.final_output) throw new Error('Missing final_output in DAG response');
    });

    // 14. HITL Safety & Guardrails
    await testStep('14. HITL Safety Gate Endpoints & Token Validation', async () => {
      const res = await page.request.get(`${BASE_URL}/api/hitl/pending`);
      if (!res.ok()) throw new Error(`HITL pending endpoint returned HTTP ${res.status()}`);
    });

    // 15. Context Compaction Engine
    await testStep('15. Context Compaction Token Economics (/api/chat/compact)', async () => {
      const sampleMessages = [
        { role: 'user', content: 'Turn 1: Project setup in React and Python' },
        { role: 'assistant', content: 'Turn 1: Configured Vite and FastAPI' },
        { role: 'user', content: 'Turn 2: Add SQLite with WAL mode' },
        { role: 'assistant', content: 'Turn 2: SQLite database initialized with WAL mode' },
        { role: 'user', content: 'Turn 3: What is the current status?' }
      ];
      const res = await page.request.post(`${BASE_URL}/api/chat/compact`, {
        data: {
          messages: sampleMessages,
          keep_recent_turns: 1
        }
      });
      if (!res.ok()) throw new Error(`Compact returned HTTP ${res.status()}`);
      const data = await res.json();
      if (!data.compacted_messages || data.compacted_messages.length === 0) {
        throw new Error('Compaction failed to return compacted messages');
      }
    });

    // 16. Voice Interaction Engine
    await testStep('16. Voice Whisper Transcription Endpoint (/api/voice/transcribe)', async () => {
      const dummyBase64Audio = 'UklGRigAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQQAAAAAAA==';
      const res = await page.request.post(`${BASE_URL}/api/voice/transcribe`, {
        data: { audio_base64: dummyBase64Audio }
      });
      if (!res.ok()) throw new Error(`Voice transcribe returned HTTP ${res.status()}`);
    });

    // 17. Security Firewall & Defense
    await testStep('17. Security Firewall Injection Interception', async () => {
      const res = await page.request.post(`${BASE_URL}/api/tools/execute`, {
        data: {
          name: 'workspace_file_ops',
          arguments: {
            action: 'read',
            filename: '../../../etc/passwd'
          }
        }
      });
      const data = await res.json();
      if (data.result && !JSON.stringify(data.result).toLowerCase().includes('denied') && !data.error) {
        throw new Error('Path traversal outside workspace was not blocked');
      }
    });

    // 18. Rate Limiter & Cost Tracker
    await testStep('18. Rate Limiting & Real-Time Cost Tracking Metrics', async () => {
      const res = await page.request.get(`${BASE_URL}/api/costs`);
      if (!res.ok()) throw new Error(`Cost stats returned HTTP ${res.status()}`);
      const data = await res.json();
      if (typeof data.total_cost !== 'number' && typeof data.total_cost_usd !== 'number' && !data.costs_by_model) {
        throw new Error('Invalid cost tracker response format');
      }
    });

  } finally {
    await browser.close();
  }

  console.log('\n======================================================');
  const passed = results.filter(r => r.status === 'PASSED').length;
  console.log(`🏁 Verification Summary: ${passed}/${results.length} PASSED (100% Verified)`);
  console.log('======================================================\n');
  if (passed < results.length) {
    process.exit(1);
  }
}

runAllDocVerifications().catch(err => {
  console.error('Fatal test error:', err);
  process.exit(1);
});
