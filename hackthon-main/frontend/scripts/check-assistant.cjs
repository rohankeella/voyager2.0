/* eslint-disable @typescript-eslint/no-require-imports */
// Backend + frontend must run. LIVE_GROQ=1 opts into one real inference request.
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    const origin = process.env.APP_URL || 'http://127.0.0.1:3000';
    if (process.env.LIVE_GROQ !== '1') {
      await page.route('**/api/assistant', route => route.fulfill({ json: { reply: 'Try a free museum garden walk.', configured: true } }));
    }
    await page.goto(`${origin}/dashboard/assistant`, { waitUntil: 'networkidle' });
    await page.getByRole('textbox', { name: 'Message the travel assistant' }).fill('Suggest one free outdoor activity in Paris. Answer in one sentence.');
    const request = page.waitForRequest(r => r.url().endsWith('/api/assistant'));
    const response = page.waitForResponse(r => r.url().endsWith('/api/assistant'), { timeout: 60000 });
    await page.getByRole('button', { name: 'Send', exact: true }).click();
    const sent = await request;
    assert.equal(sent.headers().authorization, undefined);
    assert.deepEqual(sent.postDataJSON().history, []);
    const received = await response;
    const answer = await received.json();
    assert.equal(received.status(), 200, JSON.stringify(answer));
    assert.equal(answer.configured, true);
    assert.ok(typeof answer.reply === 'string' && answer.reply.length > 10);
    await page.getByText(answer.reply, { exact: true }).waitFor();
    assert.ok(!JSON.stringify(answer).includes('gsk_'));

    await page.unroute('**/api/assistant');
    await page.route('**/api/assistant', route => route.fulfill({ status: 429, json: { reply: 'Usage limit reached. Please try again later.', configured: true, error: true } }));
    await page.getByRole('textbox', { name: 'Message the travel assistant' }).fill('Another idea?');
    await page.getByRole('button', { name: 'Send', exact: true }).click();
    await page.getByText('Usage limit reached. Please try again later.', { exact: true }).waitFor();
    assert.ok(await page.getByRole('button', { name: 'Send', exact: true }).isEnabled());
    await page.unroute('**/api/assistant');
    const invalid = await page.request.post(`${origin}/api/assistant`, { data: { message: 12 } });
    assert.equal(invalid.status(), 422);
    assert.equal((await invalid.json()).error, true);
    assert.deepEqual(errors, []);
    console.log(`PASS: ${process.env.LIVE_GROQ === '1' ? 'live Groq reply' : 'mock reply'}, browser rendering, single message/history, quota recovery, validation, no browser key or runtime errors`);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
