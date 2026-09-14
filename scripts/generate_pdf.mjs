import { chromium } from 'playwright';
import path from 'path';
import fs from 'fs';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '..');
const INDEX_HTML = path.join(ROOT_DIR, 'index.html');
const TMP_DIR = path.join(ROOT_DIR, '.tmp_pdf_pages');

const MODULE_CHIPS = [
  { name: 'AI Agent', label: '🤖 AI Agent' },
  { name: 'Gateway', label: '🚪 LLM Gateway' },
  { name: 'MCP', label: '🔌 MCP Server' },
  { name: 'Memory', label: '💾 Memory Store' },
  { name: 'Evals', label: '📊 Evals Framework' },
  { name: 'Web UI', label: '🖥️ Web UI Studio' },
  { name: 'Scripts', label: '📜 Scripts & Tools' },
  { name: 'Workspace', label: '📂 Workspace' }
];

async function generatePdfs() {
  console.log('🚀 Starting PDF generation from index.html...');

  if (!fs.existsSync(TMP_DIR)) {
    fs.mkdirSync(TMP_DIR, { recursive: true });
  }

  let browser;
  try {
    browser = await chromium.launch({ headless: true });
  } catch (err) {
    console.log('⚠️ Playwright chromium launch fallback to local Chrome binary...');
    browser = await chromium.launch({
      executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
      headless: true
    });
  }

  const page = await browser.newPage({
    viewport: { width: 1920, height: 1080 }
  });

  console.log(`📄 Loading file://${INDEX_HTML}...`);
  await page.goto(`file://${INDEX_HTML}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);

  const pageFiles = [];

  // Page 1: L1 Executive Overview (8 Modules)
  console.log('📸 Rendering Page 1: L1 Platform Overview...');
  const page1Path = path.join(TMP_DIR, 'page_01_overview.pdf');
  await page.pdf({
    path: page1Path,
    width: '1920px',
    height: '1080px',
    printBackground: true,
    pageRanges: '1'
  });
  pageFiles.push(page1Path);

  // Also save the single-page overview as index-overview.pdf
  fs.copyFileSync(page1Path, path.join(ROOT_DIR, 'index-overview.pdf'));

  // Page 2: L2 Subsystems (All 23 Subsystems)
  console.log('📸 Rendering Page 2: L2 Subsystems Map...');
  await page.evaluate(() => setLevelPreset(2));
  await page.waitForTimeout(900);
  const page2Path = path.join(TMP_DIR, 'page_02_subsystems.pdf');
  await page.pdf({
    path: page2Path,
    width: '1920px',
    height: '1080px',
    printBackground: true,
    pageRanges: '1'
  });
  pageFiles.push(page2Path);

  // Pages 3-10: Module Deep-Dives
  for (let i = 0; i < MODULE_CHIPS.length; i++) {
    const mod = MODULE_CHIPS[i];
    const pageNum = i + 3;
    console.log(`📸 Rendering Page ${pageNum}: ${mod.label} Module Deep-Dive...`);

    // Click module filter chip
    const chips = await page.$$('.chip');
    let clicked = false;
    for (const chip of chips) {
      const text = await chip.innerText();
      if (text.includes(mod.name)) {
        await chip.click();
        clicked = true;
        break;
      }
    }
    if (!clicked && chips[i + 1]) {
      await chips[i + 1].click();
    }

    await page.waitForTimeout(800);
    const modPath = path.join(TMP_DIR, `page_${String(pageNum).padStart(2, '0')}_${mod.name.toLowerCase().replace(/\s+/g, '_')}.pdf`);
    await page.pdf({
      path: modPath,
      width: '1920px',
      height: '1080px',
      printBackground: true,
      pageRanges: '1'
    });
    pageFiles.push(modPath);
  }

  await browser.close();
  console.log(`✅ All ${pageFiles.length} pages rendered successfully.`);

  // Merge with Python pypdf
  const outputPdfPath = path.join(ROOT_DIR, 'index.pdf');
  console.log(`📑 Merging ${pageFiles.length} pages into ${outputPdfPath}...`);

  const pythonScript = `
import pypdf, sys

writer = pypdf.PdfWriter()
files = sys.argv[1:]
for f in files:
    writer.append(f)

writer.write('${outputPdfPath}')
writer.close()
print(f"Merged {len(files)} pages into index.pdf successfully.")
`;

  execSync(`python3 -c "${pythonScript.replace(/"/g, '\\"')}" ${pageFiles.map(f => `"${f}"`).join(' ')}`);

  // Clean up temporary files
  for (const f of pageFiles) {
    if (fs.existsSync(f)) fs.unlinkSync(f);
  }
  if (fs.existsSync(TMP_DIR)) {
    fs.rmSync(TMP_DIR, { recursive: true, force: true });
  }

  const stat = fs.statSync(outputPdfPath);
  const statOverview = fs.statSync(path.join(ROOT_DIR, 'index-overview.pdf'));
  console.log(`🎉 PDF Generation Complete!`);
  console.log(`   - Complete Deck (10 pages): index.pdf (${(stat.size / 1024 / 1024).toFixed(2)} MB)`);
  console.log(`   - Executive Overview (1 page): index-overview.pdf (${(statOverview.size / 1024).toFixed(0)} KB)`);
}

generatePdfs().catch(err => {
  console.error('❌ Failed to generate PDF:', err);
  process.exit(1);
});
