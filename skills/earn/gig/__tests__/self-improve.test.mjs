// node:test — validates the self-improving multi-apply loop invariants:
// 1. strategy.default.json has all required schema keys and is valid JSON.
// 2. lessons.jsonl dedup logic: a lesson row requires all required fields.
// 3. No-fake-earn: earnings.jsonl guard — only settled + evidence + jpy>0 rows count.
// 4. gig-cli.sh cron prompt contains all 5 behavior markers.
// 5. strategy.default.json pass_count seeds at 0 (reset base).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');

// ─── 1. strategy.default.json schema ────────────────────────────────────────
test('strategy.default.json: exists and is valid JSON', () => {
  const p = path.join(DIR, 'strategy.default.json');
  assert.ok(fs.existsSync(p), 'strategy.default.json missing');
  const raw = fs.readFileSync(p, 'utf8');
  // must parse without throwing
  const obj = JSON.parse(raw);
  assert.ok(obj !== null, 'parsed as null');
});

test('strategy.default.json: all required keys present', () => {
  const obj = JSON.parse(fs.readFileSync(path.join(DIR, 'strategy.default.json'), 'utf8'));
  const REQUIRED = [
    'version',
    'max_apply_per_pass',
    'improve_cadence_passes',
    'priority_categories',
    'skip_categories',
    'price_defaults',
    'proposal_templates',
    'profile_blurb',
    'pass_count',
  ];
  for (const k of REQUIRED) {
    assert.ok(Object.prototype.hasOwnProperty.call(obj, k), `missing key: ${k}`);
  }
});

test('strategy.default.json: max_apply_per_pass is a positive integer ≤ 20', () => {
  const obj = JSON.parse(fs.readFileSync(path.join(DIR, 'strategy.default.json'), 'utf8'));
  assert.ok(Number.isInteger(obj.max_apply_per_pass), 'max_apply_per_pass not integer');
  assert.ok(obj.max_apply_per_pass > 0, 'max_apply_per_pass must be > 0');
  // sanity cap raised 10 -> 20: throughput was deliberately bumped to 12 (RCA FIX C, apply-throughput 増).
  assert.ok(obj.max_apply_per_pass <= 20, 'max_apply_per_pass must be ≤ 20 (sanity cap)');
});

test('strategy.default.json: improve_cadence_passes is a positive integer', () => {
  const obj = JSON.parse(fs.readFileSync(path.join(DIR, 'strategy.default.json'), 'utf8'));
  assert.ok(Number.isInteger(obj.improve_cadence_passes), 'improve_cadence_passes not integer');
  assert.ok(obj.improve_cadence_passes > 0, 'must be > 0');
});

test('strategy.default.json: priority_categories is non-empty array of strings', () => {
  const obj = JSON.parse(fs.readFileSync(path.join(DIR, 'strategy.default.json'), 'utf8'));
  assert.ok(Array.isArray(obj.priority_categories), 'not an array');
  assert.ok(obj.priority_categories.length > 0, 'empty array');
  for (const c of obj.priority_categories) {
    assert.strictEqual(typeof c, 'string', `non-string category: ${c}`);
  }
});

test('strategy.default.json: skip_categories is an array', () => {
  const obj = JSON.parse(fs.readFileSync(path.join(DIR, 'strategy.default.json'), 'utf8'));
  assert.ok(Array.isArray(obj.skip_categories), 'skip_categories not an array');
});

test('strategy.default.json: price_defaults values are numbers > 0', () => {
  const obj = JSON.parse(fs.readFileSync(path.join(DIR, 'strategy.default.json'), 'utf8'));
  assert.ok(typeof obj.price_defaults === 'object', 'not an object');
  for (const [k, v] of Object.entries(obj.price_defaults)) {
    assert.ok(typeof v === 'number' && v > 0, `price for "${k}" not a positive number: ${v}`);
  }
});

test('strategy.default.json: proposal_templates values are non-empty strings', () => {
  const obj = JSON.parse(fs.readFileSync(path.join(DIR, 'strategy.default.json'), 'utf8'));
  assert.ok(typeof obj.proposal_templates === 'object', 'not an object');
  for (const [k, v] of Object.entries(obj.proposal_templates)) {
    assert.ok(typeof v === 'string' && v.length > 0, `template for "${k}" is empty or non-string`);
  }
});

test('strategy.default.json: pass_count seeds at 0', () => {
  const obj = JSON.parse(fs.readFileSync(path.join(DIR, 'strategy.default.json'), 'utf8'));
  assert.strictEqual(obj.pass_count, 0, 'pass_count must seed at 0');
});

// ─── 2. lessons.jsonl dedup / required-fields guard ─────────────────────────
const LESSON_REQUIRED = ['ts', 'requestId', 'category', 'outcome', 'reason', 'lesson'];
const VALID_OUTCOMES = new Set([
  'accepted', 'rejected', 'ignored_closed', 'low_rating',
  'needs_human', 'unsustainable', 'delivered_no_収',
]);

function validateLessonRow(row) {
  for (const k of LESSON_REQUIRED) {
    if (!Object.prototype.hasOwnProperty.call(row, k) || row[k] === null || row[k] === '') {
      return { ok: false, msg: `missing/empty field: ${k}` };
    }
  }
  if (!VALID_OUTCOMES.has(row.outcome)) {
    return { ok: false, msg: `invalid outcome: ${row.outcome}` };
  }
  return { ok: true };
}

test('lessons.jsonl validator: rejects row with missing ts', () => {
  const bad = { requestId: '123', category: 'PPT', outcome: 'rejected', reason: 'high price', lesson: 'lower price' };
  const r = validateLessonRow(bad);
  assert.ok(!r.ok, 'should fail');
  assert.ok(r.msg.includes('ts'), r.msg);
});

test('lessons.jsonl validator: rejects row with invalid outcome', () => {
  const bad = { ts: '2026-06-30T00:00:00Z', requestId: '123', category: 'PPT', outcome: 'UNKNOWN_STATUS', reason: 'x', lesson: 'y' };
  const r = validateLessonRow(bad);
  assert.ok(!r.ok, 'should fail');
});

test('lessons.jsonl validator: accepts a valid row', () => {
  const good = { ts: '2026-06-30T00:00:00Z', requestId: '5121769', category: 'PPT/スライド', outcome: 'rejected', reason: '価格が高い', lesson: 'lower price to 6000' };
  const r = validateLessonRow(good);
  assert.ok(r.ok, r.msg);
});

test('gig-cli.sh delegates scheduling to the OS-owned pass LaunchAgent', () => {
  const code = fs.readFileSync(path.join(DIR, 'gig-cli.sh'), 'utf8');
  assert.ok(/OS-owned LaunchAgent/.test(code), 'OS scheduler ownership is not documented');
  assert.ok(!/CronCreate|claude\s+-p|codex\s+exec|--model(?:=|\s+)sonnet/i.test(code), 'legacy provider cron remains in gig-cli');
});

// ─── 3. No-fake-earn guard (earnings.jsonl) ──────────────────────────────────
const SETTLED = new Set(['検収', '支払', '検収完了', 'completed', 'paid']);

function jnum(v) {
  try { return parseFloat(String(v).replace(/[,¥円]/g, '').trim() || '0'); }
  catch { return 0; }
}

function isValidEarnRow(row) {
  return SETTLED.has(row.status) && row.evidence && String(row.evidence).length > 0 && jnum(row.jpy) > 0;
}

test('no-fake-earn: applied/in-progress row does NOT count as earned', () => {
  const fake = { ts: '2026-06-30T00:00:00Z', requestId: '5121769', status: 'applied', jpy: 5000, evidence: 'applied' };
  assert.ok(!isValidEarnRow(fake), 'applied row must not count as earned');
});

test('no-fake-earn: row with status "replied" does NOT count as earned', () => {
  const r = { ts: '2026-06-30T00:00:00Z', requestId: '5121769', status: 'replied', jpy: 5000, evidence: 'replied' };
  assert.ok(!isValidEarnRow(r), 'replied row must not count');
});

test('no-fake-earn: row with jpy=0 does NOT count as earned', () => {
  const r = { ts: '2026-06-30T00:00:00Z', requestId: '5121769', status: '検収', jpy: 0, evidence: 'some screenshot' };
  assert.ok(!isValidEarnRow(r), 'zero-jpy row must not count');
});

test('no-fake-earn: row with empty evidence does NOT count as earned', () => {
  const r = { ts: '2026-06-30T00:00:00Z', requestId: '5121769', status: '検収', jpy: 5000, evidence: '' };
  assert.ok(!isValidEarnRow(r), 'empty-evidence row must not count');
});

test('no-fake-earn: valid 検収 row counts as earned', () => {
  const r = { ts: '2026-06-30T00:00:00Z', requestId: '5121769', status: '検収', jpy: 8000, evidence: 'Coconala UI: 検収完了 confirmed' };
  assert.ok(isValidEarnRow(r), 'valid row must count');
});

test('no-fake-earn: valid 支払 row counts as earned', () => {
  const r = { ts: '2026-06-30T00:00:00Z', requestId: '5121769', status: '支払', jpy: 15000, evidence: '支払完了 screenshot' };
  assert.ok(isValidEarnRow(r), 'valid 支払 row must count');
});

// ─── 4. delivery-first pass retains bounded lower-priority behaviors ─────────
test('gig_pass.sh: delivery queue precedes all lower-priority agent steps', () => {
  const code = fs.readFileSync(path.join(DIR, 'gig_pass.sh'), 'utf8');
  const queue = code.indexOf('TOP_CLASS=');
  for (const marker of ['step "LEARN"', 'step "B0"', 'step "PROFILE"', 'step "B1"', 'step "B2"']) {
    const index = code.indexOf(marker);
    assert.ok(index > queue, `${marker} does not follow deterministic queue gate`);
  }
  assert.ok(code.includes('repeatable-agent') && code.includes('tool-agent'), 'task-class routing missing');
});

test('gig_pass.sh: passprep runs after paid queue gate and before lower-priority work', () => {
  const code = fs.readFileSync(path.join(DIR, 'gig_pass.sh'), 'utf8');
  const gate = code.indexOf('case "$TOP_CLASS"');
  const prep = code.indexOf('passprep.py');
  const learn = code.indexOf('step "LEARN"');
  assert.ok(gate >= 0 && prep > gate && prep < learn, 'passprep must run after delivery gate and before LEARN');
});

test('gig_pass.sh: successful pass restores self-improve verifier before success markers', () => {
  const code = fs.readFileSync(path.join(DIR, 'gig_pass.sh'), 'utf8');
  const verifier = code.indexOf('gig_selfimprove_verify.sh');
  const finalize = code.indexOf('if ! finalize_success', verifier);
  assert.ok(verifier >= 0 && finalize > verifier, 'self-improve verification must precede atomic success finalize');
});

test('gig_pass.sh retains NURTURE/APPLY/lessons/strategy/shared-lessons behavior contracts', () => {
  const code = fs.readFileSync(path.join(DIR, 'gig_pass.sh'), 'utf8');
  for (const marker of ['NURTURE ALL', 'APPLY BROADLY', 'lessons.jsonl', 'strategy.json', 'shared-lessons.jsonl']) {
    assert.ok(code.includes(marker), `${marker} behavior contract missing`);
  }
  assert.match(code, /requestId.*outcome|outcome.*requestId/i, 'shared lesson dedupe key missing');
  assert.match(code, /gh fail|log a warning and continue|never abort/i, 'shared lesson failure degradation missing');
});
