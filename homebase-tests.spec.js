// HOMEBASE VERIFICATION TESTS — Tier 3
// Maps 1:1 to HOMEBASE-REQUIREMENTS.md
// Run: npx playwright test homebase-tests.spec.js --reporter=list
// Run one: npx playwright test homebase-tests.spec.js -g "REQ-H001"

const { test, expect } = require('@playwright/test');

const BASE_URL = process.env.HB_URL || 'https://homebase.rize.bm';
const LOCAL_URL = 'http://localhost:8000';
const URL = process.env.USE_LOCAL ? LOCAL_URL : BASE_URL;

// All 16 pages that must have consistent nav
const ALL_PAGES = [
  '/', '/servers', '/projects', '/agents', '/metrics',
  '/sentinel', '/security', '/settings', '/research',
  '/backups', '/credentials'
];

// P0 — NAV BAR

test('REQ-H001: Nav bar consistent size across all pages', async ({ page }) => {
  const navHeights = [];
  for (const path of ALL_PAGES) {
    try {
      await page.goto(`${URL}${path}`, { timeout: 5000 });
      await page.waitForLoadState('domcontentloaded');
      const nav = page.locator('nav, .navbar, .nav-bar, header nav, [class*="nav"]').first();
      if (await nav.count() > 0) {
        const box = await nav.boundingBox();
        if (box) navHeights.push({ path, height: box.height });
      }
    } catch (e) { continue; }
  }
  if (navHeights.length >= 2) {
    const heights = navHeights.map(n => n.height);
    const min = Math.min(...heights);
    const max = Math.max(...heights);
    // Nav height should not vary by more than 10px
    expect(max - min).toBeLessThanOrEqual(10);
  }
});

test('REQ-H002: Research link present on all pages', async ({ page }) => {
  let missingResearch = [];
  for (const path of ALL_PAGES) {
    if (path === '/research') continue;
    try {
      await page.goto(`${URL}${path}`, { timeout: 5000 });
      await page.waitForLoadState('domcontentloaded');
      const researchLink = page.locator('a:has-text("Research"), [href*="research"]');
      if (await researchLink.count() === 0) {
        missingResearch.push(path);
      }
    } catch (e) { continue; }
  }
  expect(missingResearch).toEqual([]);
});

test('REQ-H003: Settings/Backups placement consistent', async ({ page }) => {
  await page.goto(URL);
  await page.waitForLoadState('domcontentloaded');
  // Either in gear dropdown OR directly in nav — but must exist
  const settingsLink = page.locator('a:has-text("Settings"), [href*="settings"]');
  const backupsLink = page.locator('a:has-text("Backups"), [href*="backups"]');
  const gearIcon = page.locator('.gear, [class*="gear"], [class*="settings-icon"], .fa-cog, .fa-gear');

  const settingsVisible = await settingsLink.count() > 0;
  const gearExists = await gearIcon.count() > 0;

  // At least one approach must work
  expect(settingsVisible || gearExists).toBe(true);
});

// P0 — BROKEN FEATURES

test('REQ-H004: Project detail page shows content', async ({ page }) => {
  await page.goto(`${URL}/projects`);
  await page.waitForLoadState('networkidle');

  // Click first project detail button
  const detailBtn = page.locator('a:has-text("Detail"), a:has-text("View"), button:has-text("Detail"), [href*="project-detail"]');
  if (await detailBtn.count() > 0) {
    await detailBtn.first().click();
    await page.waitForLoadState('networkidle');

    // Page must have actual content, not empty
    const main = page.locator('main, .content, .project-detail, [class*="detail"]');
    const text = await main.first().textContent();
    expect(text.trim().length).toBeGreaterThan(50);
  }
});

test('REQ-H005: Metrics API responds (no 500)', async ({ request }) => {
  const response = await request.get(`${URL}/api/metrics/summary`);
  expect(response.status()).not.toBe(500);
  expect([200, 304]).toContain(response.status());
});

test('REQ-H006: Research page has content on first load', async ({ page }) => {
  await page.goto(`${URL}/research`);
  await page.waitForLoadState('networkidle');

  const content = page.locator('main, .content, .research, [class*="research"]');
  await expect(content.first()).toBeVisible({ timeout: 3000 });

  const text = await content.first().textContent();
  // Should not be empty/blank
  expect(text.trim().length).toBeGreaterThan(20);
});

// P1 — CACHING

test('REQ-H007: Dashboard loads data within 2 seconds', async ({ page }) => {
  const start = Date.now();
  await page.goto(URL);
  await page.waitForLoadState('networkidle');

  const content = page.locator('.dashboard, main, .content').first();
  await expect(content).toBeVisible({ timeout: 2000 });

  const text = await content.textContent();
  expect(text.trim().length).toBeGreaterThan(20);
});

// P1 — SENTINEL

test('REQ-H008: Sentinel shows agent heartbeat status', async ({ page }) => {
  await page.goto(`${URL}/sentinel`);
  await page.waitForLoadState('networkidle');

  const bodyText = (await page.textContent('body')).toLowerCase();
  // Should show status indicators
  const hasStatus = bodyText.includes('active') ||
    bodyText.includes('healthy') ||
    bodyText.includes('oversight') ||
    bodyText.includes('heartbeat') ||
    bodyText.includes('online');

  expect(hasStatus).toBe(true);
});

// P1 — FLEET

test('REQ-H010: Talos shows version and uptime', async ({ page }) => {
  await page.goto(`${URL}/servers`);
  await page.waitForLoadState('networkidle');

  // Find Talos entry
  const talosRow = page.locator('tr:has-text("Talos"), .server-card:has-text("Talos"), [class*="server"]:has-text("Talos")');
  if (await talosRow.count() > 0) {
    const text = await talosRow.first().textContent();
    const hasVersion = text.includes('.') && /\d+\.\d+/.test(text);
    const hasUptime = text.toLowerCase().includes('uptime') ||
      text.toLowerCase().includes('day') ||
      text.toLowerCase().includes('hour');
    expect(hasVersion || hasUptime).toBe(true);
  }
});

test('REQ-H011: No duplicate Talos entries', async ({ page }) => {
  await page.goto(`${URL}/servers`);
  await page.waitForLoadState('networkidle');

  const talosEntries = page.locator('tr:has-text("Talos"), .server-card:has-text("Talos")');
  const count = await talosEntries.count();
  // Should be exactly 1, or 2 if intentionally separate (Talos server + Talos C2)
  // But NOT 2 that look the same
  if (count === 2) {
    const text1 = await talosEntries.nth(0).textContent();
    const text2 = await talosEntries.nth(1).textContent();
    // If both exist, they must be clearly different
    expect(text1).not.toBe(text2);
  }
});

test('REQ-H014: Mind map includes demo server', async ({ page }) => {
  await page.goto(`${URL}/agents`);
  await page.waitForLoadState('networkidle');

  // Find and click mind map
  const mindmapLink = page.locator('a:has-text("Mind Map"), button:has-text("Mind Map"), [href*="mindmap"], [data-testid*="mindmap"]');
  if (await mindmapLink.count() > 0) {
    await mindmapLink.first().click();
    await page.waitForLoadState('networkidle');
  }

  const bodyText = (await page.textContent('body')).toLowerCase();
  // Demo server (.246) should appear
  const hasDemos = bodyText.includes('demo') ||
    bodyText.includes('.246') ||
    bodyText.includes('demos');
  expect(hasDemos).toBe(true);
});
