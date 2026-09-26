/* eslint-disable @typescript-eslint/no-require-imports */
// Run against npm run dev or npm start. Planner is mocked; the map style is local; no API keys needed.
const assert = require("node:assert/strict");
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");

(async () => {
  const browser = await chromium.launch({ channel: "msedge", headless: true, args: ["--enable-unsafe-swiftshader"] });
  try {
    const page = await browser.newPage();
    const errors = [];
    const workers = [];
    page.on("pageerror", error => errors.push(error.message));
    page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
    page.on("worker", worker => workers.push(worker));
    await page.route("**/api/agents/status", route => route.fulfill({ json: { groq_configured: true } }));
    await page.route("**/api/agents/plan-trip", route => route.fulfill({ json: {
      trip: {
        super_trip_id: "worker-check", traveler_id: "test", status: "draft",
        global_constraints: { max_budget_usd: 100, start_date: "2026-10-01", end_date: "2026-10-02", home_location: "Paris" },
        nodes: [{ node_id: "museum", type: "activity", status: "pending", title: "Museum", depends_on: [],
          execution_data: { lat: 48.86, lng: 2.34 }, financials: { cost_usd: 0, payment_status: "unpaid" } }],
      },
      errors: [], warnings: [], trace: [], iterations: 1, hitl_required: false, hitl_reason: null, persisted_id: null,
    } }));
    await page.goto(`${process.env.APP_URL || "http://localhost:3000"}/copilot`);
    await page.getByText("Planner · Executor · Supervisor ready", { exact: true }).waitFor();
    await page.getByRole("button", { name: "5-day Paris trip from Bangalore, $2500 budget, love art and food", exact: true }).click();
    // The globe mounts with the page (empty state), so its worker may start before the plan arrives.
    await page.locator(".maplibregl-canvas").waitFor();
    await page.getByRole("heading", { name: /days$/ }).waitFor();
    // Worker evaluation waits for its module (including the sibling import) to execute.
    for (const worker of workers) {
      assert.equal(new URL(worker.url()).pathname, "/maplibre/maplibre-gl-worker.mjs");
      assert.equal(await worker.evaluate(() => typeof self.worker), "object");
    }
    assert.ok(workers.length > 0);
    await page.waitForTimeout(1500);
    assert.deepEqual(errors, []);
    console.log(`PASS: ${workers.length} local MapLibre workers initialized, globe mounted, no console errors`);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
