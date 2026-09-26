// Run with a dev server: node scripts/check-landing.cjs
// A temporary Playwright install may be supplied through PLAYWRIGHT_MODULE.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const browser = await chromium.launch({
    channel: 'msedge', headless: true,
    args: ['--enable-unsafe-swiftshader'],
  });
  const errors = [];
  const output = '.impeccable/review';
  fs.mkdirSync(output, { recursive: true });
  try {
    for (const [name, width, height] of [['desktop', 1440, 1000], ['tablet', 768, 1024], ['mobile', 390, 844]]) {
      const page = await browser.newPage({ viewport: { width, height } });
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(process.env.LANDING_URL || 'http://localhost:3000', { waitUntil: 'networkidle' });
      await page.getByRole('heading', { level: 1 }).waitFor();
      await page.waitForFunction(() => !document.querySelector('.orbit-loading'), { timeout: 60000 });
      assert.equal(await page.locator('.orbit-fallback').count(), 0, 'Globe must load');
      assert.ok((await page.locator('canvas').boundingBox()).height >= 350, 'Globe canvas must fill its stage');
      if (width < 1024) {
        const copy = await page.locator('[class*="heroCopy"]').boundingBox();
        const globe = await page.locator('.orbit-stage').boundingBox();
        assert.ok(globe.y >= copy.y + copy.height - 10, 'Tablet/mobile globe must sit below the hero copy');
      }
      assert.equal(await page.getByRole('heading', { level: 1 }).count(), 1);
      assert.equal(await page.getByRole('link', { name: 'Start Planning', exact: true }).first().getAttribute('href'), '/register');
      await page.getByRole('button', { name: 'Pause globe' }).click();
      assert.equal(await page.getByRole('button', { name: 'Play globe' }).getAttribute('aria-pressed'), 'true');
      await page.getByRole('button', { name: 'Pause destination animation' }).click();
      const images = page.locator('#destinations img');
      assert.equal(await images.count(), 18);
      const sources = await images.evaluateAll(nodes => nodes.map(img => img.getAttribute('src')));
      assert.equal(new Set(sources).size, 18, 'All 18 destination photos must be distinct across both rails');
      await page.locator('#destinations').scrollIntoViewIfNeeded();
      await page.waitForFunction(() => [...document.querySelectorAll('#destinations img')].every(img => img.complete && img.naturalWidth > 0));
      assert.equal(await images.first().evaluate(img => getComputedStyle(img.parentElement).animationPlayState), 'paused');
      assert.equal(await page.getByRole('navigation', { name: 'Featured destinations' }).getByRole('link').count(), 6);
      if (width < 1024) {
        await page.getByRole('button', { name: 'Toggle menu' }).click();
        assert.equal(await page.getByRole('button', { name: 'Toggle menu' }).getAttribute('aria-expanded'), 'true');
        await page.locator('#mobile-navigation').getByRole('link', { name: 'Destinations', exact: true }).click();
        assert.equal(await page.getByRole('button', { name: 'Toggle menu' }).getAttribute('aria-expanded'), 'false');
        await page.locator('#mobile-navigation').waitFor({ state: 'detached' });
      }
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `${name} must not overflow`);
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await page.getByRole('button', { name: 'Play destination animation' }).click();
      assert.equal(await images.first().evaluate(img => getComputedStyle(img.parentElement).animationPlayState), 'paused', 'Reduced motion must pause the corridor');
      await page.evaluate(() => scrollTo({ top: 0, behavior: 'instant' }));
      await page.screenshot({ path: `${output}/${name}.png`, fullPage: true });
      await page.screenshot({ path: `${output}/${name}-hero.png` });
      console.log(`${name}: globe, images, links, pause controls, reduced motion and layout passed`);
      await page.close();
    }
    assert.deepEqual(errors, [], 'No browser runtime errors');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
