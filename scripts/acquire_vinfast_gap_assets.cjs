// Public official assets only. Acquisition never marks a source as reviewed.
// Run from the repo root after npm install in frontend.
const { chromium } = require('../frontend/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assets = [
  ['vf5-schedule.png', 'https://static-cms-prod.vinfastauto.com/lich-bao-duong-vf5_2.PNG'],
  ['vf8-schedule.png', 'https://static-cms-prod.vinfastauto.com/lich-bao-duong-vf6-7-8-e34_2.PNG'],
  ['vf3-brochure.pdf', 'https://static-cms-prod.vinfastauto.com/statics/shared/16062026-Brochure-VF-3.pdf'],
];
(async () => {
  const dir = path.resolve('data/acquired/vinfast-browser-2026-10-19');
  fs.mkdirSync(dir, { recursive: true });
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const manifest = [];
  try {
    const context = await browser.newContext();
    for (const [name, url] of assets) {
      const response = await context.request.get(url, { timeout: 20000 });
      const entry = { name, url, final_url: response.url(), status: response.status(), acquired_at: new Date().toISOString() };
      if (response.ok()) {
        if (new URL(response.url()).hostname !== 'static-cms-prod.vinfastauto.com') throw new Error('Unexpected asset redirect');
        const bytes = await response.body();
        entry.sha256 = crypto.createHash('sha256').update(bytes).digest('hex');
        const target = path.join(dir, name);
        if (fs.existsSync(target) && !fs.readFileSync(target).equals(bytes)) throw new Error('Asset changed: preserve and review as a new revision');
        fs.writeFileSync(target, bytes);
      }
      manifest.push(entry);
      console.log(name, entry.status, entry.sha256 || 'not downloaded');
    }
    fs.writeFileSync(path.join(dir, 'asset-acquisition.json'), JSON.stringify(manifest, null, 2));
    if (manifest.some(row => row.status !== 200)) process.exitCode = 1;
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
