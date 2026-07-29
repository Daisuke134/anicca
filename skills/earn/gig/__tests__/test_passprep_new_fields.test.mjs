// test_passprep_new_fields.test.mjs — RED (Phase 2a, feature gig-feasibility-volume).
// PROP-003 / REQ-GFV-002,005 — passprep.py exits 0 and prints valid JSON for all 4 fallback
// branches: (a) missing strategy.json, (b) corrupt strategy.json, (c) missing strategy.default.json
// + corrupt strategy.json, (d) unreadable listings.jsonl.
// PROP-007 / REQ-GFV-005 — `listings_due` is a boolean on every successful AND every fallback run.
// PROP-023 / REQ-GFV-017 — `cold_start` is a boolean on every successful AND every fallback run.
// PROP-011 / REQ-GFV-009 — strategy.default.json seeds apply_skip_thresholds.max_applicants=30 for
// a FRESH bootstrap; a LIVE fixture with max_applicants:12 is left at 12 after passprep.py runs.
//
// Same isolated-HOME-tmpdir + spawnSync convention as the existing passprep.test.mjs (kept
// untouched, still green as the regression baseline for pass_count/do_improve/skip-floor).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const PASSPREP = path.join(DIR, 'passprep.py');
const DEFAULT_STRATEGY = path.join(DIR, 'strategy.default.json');

function runPassprep(homeDir) {
  return spawnSync('python3', [PASSPREP], {
    env: { ...process.env, HOME: homeDir },
    encoding: 'utf8',
  });
}

function parseOut(stdout) {
  const line = stdout.trim().split('\n').filter(Boolean).pop();
  return JSON.parse(line);
}

// ─── PROP-007/023 branch (a): missing strategy.json (fresh bootstrap) ──────
test('passprep: fresh bootstrap -> listings_due:true, cold_start:true, both booleans', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'passprep-gfv-'));
  try {
    const res = runPassprep(tmp);
    assert.strictEqual(res.status, 0, `exit ${res.status}: stderr=${res.stderr}`);
    const out = parseOut(res.stdout);
    assert.strictEqual(typeof out.listings_due, 'boolean', 'listings_due must be boolean');
    assert.strictEqual(out.listings_due, true, 'fresh bootstrap: 0 listings ever -> listings_due:true');
    assert.strictEqual(typeof out.cold_start, 'boolean', 'cold_start must be boolean');
    assert.strictEqual(out.cold_start, true, 'fresh bootstrap: 0 settled revenue -> cold_start:true');
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

// ─── PROP-003 branch (b): corrupt strategy.json -> repaired, valid JSON, exit 0, new fields present
test('passprep: corrupt strategy.json -> exit 0, valid JSON, listings_due/cold_start present', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'passprep-gfv-'));
  try {
    const gigDir = path.join(tmp, 'gig');
    fs.mkdirSync(gigDir, { recursive: true });
    fs.writeFileSync(path.join(gigDir, 'strategy.json'), '{ this is NOT valid JSON {{ broken ');
    const res = runPassprep(tmp);
    assert.strictEqual(res.status, 0, `exit ${res.status}: stderr=${res.stderr}`);
    const out = parseOut(res.stdout);
    assert.strictEqual(typeof out.listings_due, 'boolean', 'listings_due must be boolean even on repair path');
    assert.strictEqual(typeof out.cold_start, 'boolean', 'cold_start must be boolean even on repair path');
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

// ─── PROP-003 branch (d): unreadable listings.jsonl -> passprep degrades to listings_due:true,
// never a stack trace to stdout, exit 0.
test('passprep: unreadable listings.jsonl -> exit 0, degrades to listings_due:true (fallback path)', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'passprep-gfv-'));
  try {
    const gigDir = path.join(tmp, 'gig');
    fs.mkdirSync(gigDir, { recursive: true });
    const listingsPath = path.join(gigDir, 'listings.jsonl');
    fs.writeFileSync(listingsPath, 'not valid jsonl at all {{{');
    fs.chmodSync(listingsPath, 0o000); // unreadable
    const res = runPassprep(tmp);
    try {
      assert.strictEqual(res.status, 0, `exit ${res.status}: stderr=${res.stderr}`);
      const out = parseOut(res.stdout);
      assert.strictEqual(typeof out.listings_due, 'boolean', 'listings_due must still be boolean');
      assert.strictEqual(out.listings_due, true, 'unreadable listings.jsonl -> degrades to listings_due:true');
    } finally {
      fs.chmodSync(listingsPath, 0o644); // restore so rmSync can clean up
    }
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

// ─── PROP-011: fresh bootstrap seeds max_applicants=30 ─────────────────────
test('passprep: fresh bootstrap seeds apply_skip_thresholds.max_applicants=30', () => {
  const seed = JSON.parse(fs.readFileSync(DEFAULT_STRATEGY, 'utf8'));
  assert.strictEqual(
    seed.apply_skip_thresholds && seed.apply_skip_thresholds.max_applicants,
    30,
    'strategy.default.json.apply_skip_thresholds.max_applicants must be 30'
  );

  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'passprep-gfv-'));
  try {
    runPassprep(tmp);
    const stratPath = path.join(tmp, 'gig', 'strategy.json');
    const saved = JSON.parse(fs.readFileSync(stratPath, 'utf8'));
    assert.strictEqual(saved.apply_skip_thresholds.max_applicants, 30, 'fresh-bootstrap strategy.json must inherit max_applicants=30');
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

// ─── PROP-011: live-tuned max_applicants:12 is NOT overwritten by bootstrap default ─────────────
test('passprep: LIVE strategy.json with max_applicants:12 is left at 12 (not reset to seed 30)', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'passprep-gfv-'));
  try {
    const gigDir = path.join(tmp, 'gig');
    fs.mkdirSync(gigDir, { recursive: true });
    const strat = JSON.parse(fs.readFileSync(DEFAULT_STRATEGY, 'utf8'));
    strat.apply_skip_thresholds = { max_applicants: 12, min_contracted_to_skip: 1, min_budget_jpy: 3000 };
    strat.pass_count = 217;
    fs.writeFileSync(path.join(gigDir, 'strategy.json'), JSON.stringify(strat, null, 2));

    const res = runPassprep(tmp);
    assert.strictEqual(res.status, 0, `exit ${res.status}: stderr=${res.stderr}`);
    const saved = JSON.parse(fs.readFileSync(path.join(gigDir, 'strategy.json'), 'utf8'));
    assert.strictEqual(saved.apply_skip_thresholds.max_applicants, 12, 'live-tuned max_applicants must survive unchanged at 12');
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

// ─── PROP-007: listings.jsonl with 2 rows in the last 7 days (target=2) -> listings_due:false ──
test('passprep: 2 listings.jsonl rows in trailing 7 days (target=2) -> listings_due:false', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'passprep-gfv-'));
  try {
    const gigDir = path.join(tmp, 'gig');
    fs.mkdirSync(gigDir, { recursive: true });
    const now = Date.now() / 1000;
    const rows = [
      { ts: now - 1 * 86400, listing_id: 'L1', status: 'live' },
      { ts: now - 3 * 86400, listing_id: 'L2', status: 'live' },
    ];
    fs.writeFileSync(path.join(gigDir, 'listings.jsonl'), rows.map((r) => JSON.stringify(r)).join('\n') + '\n');
    const res = runPassprep(tmp);
    assert.strictEqual(res.status, 0, `exit ${res.status}: stderr=${res.stderr}`);
    const out = parseOut(res.stdout);
    assert.strictEqual(out.listings_due, false, '2 rows in trailing 7 days at target=2 -> listings_due:false');
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

// ─── PROP-023: earnings.jsonl with a real settled row -> cold_start:false ──────────────────────
test('passprep: earnings.jsonl with one real SETTLED row -> cold_start:false', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'passprep-gfv-'));
  try {
    const gigDir = path.join(tmp, 'gig');
    fs.mkdirSync(gigDir, { recursive: true });
    fs.writeFileSync(
      path.join(gigDir, 'earnings.jsonl'),
      JSON.stringify({ status: '検収', jpy: 5000, evidence: 'https://example.com/proof.png' }) + '\n'
    );
    const res = runPassprep(tmp);
    assert.strictEqual(res.status, 0, `exit ${res.status}: stderr=${res.stderr}`);
    const out = parseOut(res.stdout);
    assert.strictEqual(out.cold_start, false, 'real settled earnings row -> cold_start:false');
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});
