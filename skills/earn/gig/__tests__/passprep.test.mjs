// node:test — runs passprep.py against isolated temp HOME states and asserts deterministic behaviour.
// Uses env HOME=<tmpdir> so no live ~/gig files are touched.
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

// Run passprep.py with an isolated HOME dir. Returns the spawnSync result.
function runPassprep(homeDir) {
  return spawnSync('python3', [PASSPREP], {
    env: { ...process.env, HOME: homeDir },
    encoding: 'utf8',
  });
}

// Parse the last non-empty stdout line as JSON (the script prints exactly one JSON line).
function parseOut(stdout) {
  const line = stdout.trim().split('\n').filter(Boolean).pop();
  return JSON.parse(line);
}

// ─── 1. Missing strategy.json → bootstrapped ────────────────────────────────
test('passprep: missing strategy.json → bootstrapped + valid JSON out', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'passprep-t-'));
  try {
    // No ~/gig/ directory at all in tmp
    const res = runPassprep(tmp);
    assert.strictEqual(res.status, 0, `exit ${res.status}: stderr=${res.stderr}`);
    const out = parseOut(res.stdout);
    assert.ok(typeof out.pass_count === 'number', 'pass_count must be a number');
    assert.strictEqual(out.pass_count, 1, 'first pass should be 1');
    assert.ok(typeof out.do_improve === 'boolean', 'do_improve must be boolean');
    assert.ok(Array.isArray(out.priority_categories), 'priority_categories must be array');
    assert.ok(out.priority_categories.length > 0, 'priority_categories must be non-empty');
    assert.ok(Array.isArray(out.skip_categories), 'skip_categories must be array');
    // strategy.json must have been created in tmp/gig/
    const stratPath = path.join(tmp, 'gig', 'strategy.json');
    assert.ok(fs.existsSync(stratPath), 'strategy.json not bootstrapped in tmp/gig/');
    const saved = JSON.parse(fs.readFileSync(stratPath, 'utf8'));
    assert.strictEqual(saved.pass_count, 1, 'pass_count in saved file must be 1');
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

// ─── 2. Corrupt strategy.json → repaired + valid JSON out ───────────────────
test('passprep: corrupt strategy.json → repaired from default (or fallback) + valid JSON out', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'passprep-t-'));
  try {
    const gigDir = path.join(tmp, 'gig');
    fs.mkdirSync(gigDir, { recursive: true });
    // Write obviously corrupt JSON
    fs.writeFileSync(path.join(gigDir, 'strategy.json'), '{ this is NOT valid JSON {{ broken ');
    const res = runPassprep(tmp);
    assert.strictEqual(res.status, 0, `exit ${res.status}: stderr=${res.stderr}`);
    const out = parseOut(res.stdout);
    assert.ok(typeof out.pass_count === 'number', 'pass_count must be a number');
    assert.ok(out.pass_count >= 1, 'pass_count must be incremented');
    // strategy.json must now be valid JSON
    const stratPath = path.join(gigDir, 'strategy.json');
    const saved = JSON.parse(fs.readFileSync(stratPath, 'utf8')); // throws if still corrupt
    assert.ok(saved.pass_count >= 1, 'pass_count not incremented in repaired file');
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

// ─── 3. skip⊇priority → skip_categories reset to [] ────────────────────────
test('passprep: skip_categories ⊇ priority_categories → reset to []', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'passprep-t-'));
  try {
    const gigDir = path.join(tmp, 'gig');
    fs.mkdirSync(gigDir, { recursive: true });
    // Load the canonical defaults and set skip to cover all priorities
    const strat = JSON.parse(fs.readFileSync(DEFAULT_STRATEGY, 'utf8'));
    strat.skip_categories = [...strat.priority_categories]; // skip ⊇ priority
    strat.pass_count = 0;
    fs.writeFileSync(path.join(gigDir, 'strategy.json'), JSON.stringify(strat, null, 2));

    const res = runPassprep(tmp);
    assert.strictEqual(res.status, 0, `exit ${res.status}: stderr=${res.stderr}`);
    const out = parseOut(res.stdout);
    assert.deepEqual(out.skip_categories, [], 'skip_categories must be reset to [] in JSON output');
    // Also verify written back to disk
    const saved = JSON.parse(fs.readFileSync(path.join(gigDir, 'strategy.json'), 'utf8'));
    assert.deepEqual(saved.skip_categories, [], 'skip_categories not reset in persisted strategy.json');
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

// ─── 4. pass_count increments and persists ──────────────────────────────────
test('passprep: pass_count increments from N → N+1 and persists to strategy.json', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'passprep-t-'));
  try {
    const gigDir = path.join(tmp, 'gig');
    fs.mkdirSync(gigDir, { recursive: true });
    const strat = JSON.parse(fs.readFileSync(DEFAULT_STRATEGY, 'utf8'));
    strat.pass_count = 10;
    fs.writeFileSync(path.join(gigDir, 'strategy.json'), JSON.stringify(strat, null, 2));

    const res = runPassprep(tmp);
    assert.strictEqual(res.status, 0, `exit ${res.status}: stderr=${res.stderr}`);
    const out = parseOut(res.stdout);
    assert.strictEqual(out.pass_count, 11, 'pass_count must increment to 11');
    const saved = JSON.parse(fs.readFileSync(path.join(gigDir, 'strategy.json'), 'utf8'));
    assert.strictEqual(saved.pass_count, 11, 'pass_count must be persisted as 11');
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

// ─── 5. do_improve true exactly when pass_count % cadence == 0 ──────────────
test('passprep: do_improve=true when (current_pass_count % cadence == 0)', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'passprep-t-'));
  try {
    const gigDir = path.join(tmp, 'gig');
    fs.mkdirSync(gigDir, { recursive: true });
    const strat = JSON.parse(fs.readFileSync(DEFAULT_STRATEGY, 'utf8'));
    strat.improve_cadence_passes = 4;
    strat.pass_count = 3; // next pass = 4, 4 % 4 == 0 → do_improve true
    fs.writeFileSync(path.join(gigDir, 'strategy.json'), JSON.stringify(strat, null, 2));

    const res = runPassprep(tmp);
    assert.strictEqual(res.status, 0, `exit ${res.status}: stderr=${res.stderr}`);
    const out = parseOut(res.stdout);
    assert.strictEqual(out.pass_count, 4, 'pass_count must be 4');
    assert.strictEqual(out.do_improve, true, 'do_improve must be true at pass 4 (cadence=4)');
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

test('passprep: do_improve=false when (current_pass_count % cadence != 0)', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'passprep-t-'));
  try {
    const gigDir = path.join(tmp, 'gig');
    fs.mkdirSync(gigDir, { recursive: true });
    const strat = JSON.parse(fs.readFileSync(DEFAULT_STRATEGY, 'utf8'));
    strat.improve_cadence_passes = 4;
    strat.pass_count = 4; // next pass = 5, 5 % 4 != 0 → do_improve false
    fs.writeFileSync(path.join(gigDir, 'strategy.json'), JSON.stringify(strat, null, 2));

    const res = runPassprep(tmp);
    assert.strictEqual(res.status, 0, `exit ${res.status}: stderr=${res.stderr}`);
    const out = parseOut(res.stdout);
    assert.strictEqual(out.pass_count, 5, 'pass_count must be 5');
    assert.strictEqual(out.do_improve, false, 'do_improve must be false at pass 5 (cadence=4)');
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});
