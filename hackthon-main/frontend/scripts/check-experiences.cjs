/* eslint-disable @typescript-eslint/no-require-imports */
// Start frontend + backend, then: node scripts/check-experiences.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const output = '.impeccable/review/experiences';
  fs.mkdirSync(output, { recursive: true });
  const origin = process.env.EXPERIENCES_URL || 'http://127.0.0.1:3000';
  const errors = [];
  try {
    for (const [name, width, height] of [['desktop', 1440, 1000], ['tablet', 768, 1024], ['mobile', 390, 844]]) {
      const page = await browser.newPage({ viewport: { width, height } });
      page.on('pageerror', e => errors.push(e.message));
      await page.goto(`${origin}/experiences`, { waitUntil: 'networkidle' });
      await page.getByRole('heading', { name: 'Make room for an experience.' }).waitFor();
      assert.ok(await page.locator('.experience-card').count() > 0, 'Catalog data must render');
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'No horizontal overflow');
      if (width < 1280) assert.ok(await page.getByRole('button', { name: 'Toggle menu' }).isVisible(), 'Navigation collapses before links clip');
      await page.screenshot({ path: `${output}/${name}.png`, fullPage: true });
      await page.getByRole('searchbox', { name: 'Destination or activity' }).fill('Paris');
      await page.getByRole('button', { name: 'Search experiences', exact: true }).click();
      await page.waitForURL('**/experiences?q=Paris');
      await page.locator('.experience-card').first().waitFor();
      const filterRoot = width <= 800 ? page.getByRole('dialog') : page.locator('.experience-sidebar');
      if (width <= 800) await page.getByRole('button', { name: 'Filters', exact: true }).click();
      await filterRoot.getByRole('checkbox', { name: 'Food & drink' }).click();
      await page.waitForURL('**category=FOOD');
      if (width <= 800) {
        await page.keyboard.press('Escape');
        assert.equal(await page.getByRole('dialog').isVisible(), false);
      }
      await page.locator('.experience-card').first().waitFor();
      assert.equal(await page.locator('.experience-card').count(), 1);
      await page.getByRole('combobox', { name: 'Sort by' }).selectOption('price_asc');
      await page.waitForURL('**sort=price_asc');
      await page.locator('.experience-card').first().waitFor();
      await page.locator('.experience-card-link').first().click();
      await page.waitForURL('**/experience/**');
      await page.getByRole('heading', { name: 'About this experience' }).waitFor();
      assert.equal(await page.getByRole('button', { name: 'Online booking unavailable' }).isDisabled(), true);
      await page.getByRole('spinbutton', { name: 'Number of travelers' }).fill('3');
      await page.getByText('for 3 travelers').waitFor();
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await page.screenshot({ path: `${output}/${name}-detail.png`, fullPage: true });
      await page.getByRole('button', { name: 'Back to experiences' }).click();
      await page.waitForURL('**/experiences?**');
      assert.ok(page.url().includes('category=FOOD') && page.url().includes('sort=price_asc'));
      await page.getByRole('button', { name: 'Remove category FOOD' }).click();
      await page.waitForURL(url => !url.searchParams.has('category'));
      await page.locator('.experience-card').first().waitFor();
      assert.ok(await page.locator('.experience-card').count() > 1);
      await page.goto(`${origin}/experiences?q=definitely-no-such-place`, { waitUntil: 'networkidle' });
      await page.getByRole('heading', { name: 'No experiences found' }).waitFor();
      await page.goto(`${origin}/experience/not-a-real-id`, { waitUntil: 'networkidle' });
      await page.getByRole('heading', { name: 'This experience is no longer available.' }).waitFor();
      await page.close();
    }
    const page = await browser.newPage();
    // A fresh tab has no previous entry: the shared BackButton must use its fallback.
    await page.goto(`${origin}/experiences`, { waitUntil: 'networkidle' });
    await page.getByRole('button', { name: 'Back to Discover' }).click();
    await page.waitForURL('**/discover');
    await page.route('**/api/experiences?*', route => route.fulfill({ status: 503, contentType: 'application/json', body: '{"detail":"test outage"}' }));
    await page.goto(`${origin}/experiences`, { waitUntil: 'networkidle' });
    await page.getByRole('heading', { name: 'We couldn’t load experiences.' }).waitFor();
    await page.unroute('**/api/experiences?*');
    await page.getByRole('button', { name: 'Retry', exact: true }).click();
    await page.locator('.experience-card').first().waitFor();
    await page.goto(origin, { waitUntil: 'domcontentloaded' });
    await page.getByRole('link', { name: 'Start Planning', exact: true }).first().waitFor();
    assert.deepEqual(errors, [], 'No runtime errors in experience pages');
    console.log('PASS: desktop/tablet/mobile, live search, categories, sorting, chips, details, travelers, back/fallback, empty/error/retry, landing entry');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
