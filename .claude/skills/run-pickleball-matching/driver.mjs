// Drives the PickleBall Matching prototype (Expo web app + FastAPI backend)
// in headless Chrome via playwright-core. See SKILL.md next to this file.
//
//   node driver.mjs smoke                         API-only check (no browser)
//   node driver.mjs flow                          full record -> upload -> analysis walk + debug variants
//   node driver.mjs shot <route> [--desktop] [--wait "<text>"]
//                                                 screenshot one route, e.g. /session/abc/results
//
// Env: APP_URL (default http://localhost:8081), API_URL (default http://localhost:8000),
//      SHOTS_DIR (default ./shots next to this file), CHROME_CHANNEL (default "chrome"; try "msedge").

import { mkdirSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const APP = process.env.APP_URL ?? 'http://localhost:8081';
const API = process.env.API_URL ?? 'http://localhost:8000';
const SHOTS = process.env.SHOTS_DIR ?? join(HERE, 'shots');
const MOBILE = { width: 390, height: 844 }; // narrow: app fills the window, DEBUG pill top-right
const DESKTOP = { width: 1280, height: 900 }; // wide: phone frame + docked debug panel

const [mode = 'flow', ...rest] = process.argv.slice(2);

async function api(path, method = 'GET', body) {
  const res = await fetch(API + path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  return { status: res.status, body: text ? JSON.parse(text) : null };
}

// ---- smoke: exercise the API the way the app does --------------------------
async function smoke() {
  const ok = (cond, msg) => {
    console.log(`${cond ? 'PASS' : 'FAIL'}  ${msg}`);
    if (!cond) process.exitCode = 1;
  };
  await api('/api/debug/reset', 'POST');
  ok((await api('/api/health')).body?.ok, 'GET /api/health');
  const drills = (await api('/api/drills')).body;
  ok(drills.length === 3, `GET /api/drills -> ${drills.map((d) => d.id).join(', ')}`);
  ok((await api('/api/models')).body.some((m) => m.id === 'simulated'), 'GET /api/models includes simulated');
  const now = new Date().toISOString();
  const s = (
    await api('/api/sessions', 'POST', {
      drill_id: drills[0].id,
      drill_version: drills[0].version,
      feed_method: 'human_feeder',
      capture_started_at: now,
      capture_ended_at: now,
      scenario: 'upload_error',
    })
  ).body;
  const up = () => api(`/api/sessions/${s.id}/upload`, 'POST', { model_id: 'simulated', clip_id: 'synthetic' });
  ok((await up()).status === 503, 'first upload fails (upload_error scenario)');
  ok((await up()).status === 200, 'retry under same session ID succeeds');
  let status;
  for (let i = 0; i < 30; i++) {
    status = (await api(`/api/sessions/${s.id}`)).body.status;
    if (status === 'completed' || status === 'failed') break;
    await new Promise((r) => setTimeout(r, 1000));
  }
  ok(status === 'completed', `pipeline finished: ${status}`);
  const r = (await api(`/api/sessions/${s.id}/results`)).body;
  ok(r.sufficient, `results: ${r.scored}/${r.total_attempts} scored, success ${Math.round(r.success_rate * 100)}%`);
  ok((await api(`/api/sessions/${s.id}/publish`, 'POST')).body.version === 1, 'publish -> profile v1');
}

// ---- browser helpers ---------------------------------------------------------
async function openBrowser(viewport) {
  const { chromium } = await import('playwright-core');
  const browser = await chromium.launch({ channel: process.env.CHROME_CHANNEL ?? 'chrome', headless: true });
  const page = await (await browser.newContext({ viewport })).newPage();
  const errors = [];
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  page.on('pageerror', (e) => errors.push('PAGEERROR ' + e.message));
  let n = 0;
  const shot = async (name) => {
    await page.waitForTimeout(400); // let RN-web transitions settle
    const file = join(SHOTS, `${String(++n).padStart(2, '0')}-${name}.png`);
    await page.screenshot({ path: file });
    console.log('shot', file);
  };
  // Expo Router keeps previous screens mounted but hidden, so the same text can
  // exist several times. Always target the visible match.
  const text = (t) => page.getByText(t, { exact: true }).locator('visible=true').first();
  const see = (t, timeout = 30000) => text(t).waitFor({ state: 'visible', timeout });
  const tap = (t) => text(t).click();
  return { browser, page, errors, shot, see, tap };
}

async function finish(ctx) {
  console.log(`console errors: ${ctx.errors.length}`);
  for (const e of ctx.errors.slice(0, 15)) console.log('  ', e.slice(0, 300));
  await ctx.browser.close();
}

// ---- shot: one route ---------------------------------------------------------
async function shotRoute() {
  const route = rest.find((a) => !a.startsWith('--')) ?? '/';
  const wi = rest.indexOf('--wait');
  const waitFor = wi >= 0 ? rest[wi + 1] : undefined;
  const ctx = await openBrowser(rest.includes('--desktop') ? DESKTOP : MOBILE);
  try {
    await ctx.page.goto(APP + route);
    if (waitFor) await ctx.see(waitFor, 60000);
    else await ctx.page.waitForLoadState('networkidle', { timeout: 60000 });
    await ctx.shot(route.replace(/[^a-z0-9]+/gi, '_').replace(/^_|_$/g, '') || 'home');
  } catch (e) {
    console.log('FAILED:', e.message.split('\n')[0]);
    await ctx.shot('FAILURE');
    process.exitCode = 1;
  } finally {
    await finish(ctx);
  }
}

// ---- flow: full walkthrough ----------------------------------------------------
async function flow() {
  await api('/api/debug/reset', 'POST');
  const ctx = await openBrowser(MOBILE);
  const { page, shot, see, tap } = ctx;
  try {
    await page.goto(APP);
    await see('Record a standardized drill', 60000); // first load compiles lazily
    await shot('1.0-dashboard');

    await tap('Record New Drill');
    await see('Lateral Coverage - Prescribed');
    await shot('1.2-drill-list');
    await tap('Lateral Coverage - Prescribed');
    await see('PURPOSE');
    await shot('1.3-instructions');

    await tap('Continue');
    await see('Before you start');
    for (const t of [
      'I have a paddle and 20 balls, or a loaded ball machine',
      'A feeder or ball machine is ready',
      'My phone is on a tripod or stable stand',
      "I'm wearing clothing that contrasts with the court",
    ])
      await tap(t);
    await tap('Ball machine');
    await shot('1.4-checklist');

    await tap('Start Camera Setup');
    await see('Camera setup check');
    await shot('2.2-camera-not-ready');
    await tap('Player visible'); // simulated check toggles
    await see('Ready to record');
    await shot('2.3-camera-ready');

    await tap('Start Recording');
    await see('Go to the center mark', 10000);
    await shot('2.4-countdown');
    await see('Stop Recording', 10000);
    await page.waitForTimeout(4000);
    await shot('2.5-recording');
    await tap('Stop Recording');

    await see('Prototype only');
    await see('UI prototype'); // model owner line; the name is split by a nested version <Text>
    await shot('3.1-model-select');
    await tap('Upload & Analyze');

    await see('Analyzing your drill');
    await page.waitForTimeout(1800);
    await shot('3.3-processing');
    await see('PROVISIONAL', 30000);
    await shot('4.1-results');

    await tap('Review Attempts');
    await page.getByText(/^SCORED · /).locator('visible=true').first().waitFor();
    await shot('4.2-attempts');
    await page.getByLabel(/^Flag attempt \d+$/).locator('visible=true').first().click();
    await see('Flag Attempt');
    await shot('4.3-flag-sheet');
    await tap('Flag Attempt');
    // Wait for the sheet (and its overlay) to close; a fixed delay was flaky when the API was busy.
    await page.getByText('Cancel', { exact: true }).locator('visible=true').first().waitFor({ state: 'hidden', timeout: 30000 });
    // Results reload on focus. Until the reload lands, the screen still shows the pre-flag data
    // (with Publish), even when the flag dropped a direction below 5 scored attempts; deciding
    // on that stale screen made this step flaky. Wait for the refreshed results first.
    const reloaded = page.waitForResponse((r) => /\/api\/sessions\/[^/]+\/results$/.test(r.url()) && r.request().method() === 'GET');
    await tap('Back to Profile');
    await reloaded;
    await page.waitForTimeout(300);

    await see('Coverage profile');
    if (await text_visible(page, 'Publish to Profile')) {
      await tap('Publish to Profile');
      await see('Assessment published');
      await shot('4.4-published');
      await tap('View Partner Matches');
      await see('Sample data');
      await shot('5.2-partners-dummy');
    } else {
      console.log('NOTE: flagging dropped a direction below 5 scored attempts; publish not offered');
      await shot('4.1-insufficient-after-flag');
    }

    // Error / empty variants through the debug panel.
    const jump = async (label) => {
      await page.goto(APP);
      await see('DEBUG', 30000);
      await tap('DEBUG');
      await see('NEXT RECORDING FOLLOWS');
      await tap(label);
    };
    await jump('Upload error');
    await see("Upload didn't finish");
    await shot('3.2-upload-error');
    await tap('Retry Upload');
    await see('Analyzing your drill');
    await shot('3.2-retry-processing');
    await jump('Processing error');
    await see("We couldn't analyze this drill");
    await shot('3.4-processing-error');
    await jump('Not enough valid data');
    await see('NOT ENOUGH DATA');
    await shot('4.1b-insufficient');

    await page.setViewportSize(DESKTOP);
    await page.goto(APP + '/drill/lateral-prescribed');
    await see('PURPOSE', 30000);
    await shot('desktop-framed');
    console.log('FLOW OK');
  } catch (e) {
    console.log('FAILED:', e.message.split('\n')[0]);
    await shot('FAILURE');
    process.exitCode = 1;
  } finally {
    await finish(ctx);
  }
}

async function text_visible(page, t) {
  return page
    .getByText(t, { exact: true })
    .locator('visible=true')
    .first()
    .isVisible()
    .catch(() => false);
}

if (mode === 'smoke') await smoke();
else {
  if (mode === 'flow') rmSync(SHOTS, { recursive: true, force: true });
  mkdirSync(SHOTS, { recursive: true });
  if (mode === 'flow') await flow();
  else if (mode === 'shot') await shotRoute();
  else {
    console.log('usage: node driver.mjs smoke | flow | shot <route> [--desktop] [--wait "<text>"]');
    process.exitCode = 2;
  }
}
