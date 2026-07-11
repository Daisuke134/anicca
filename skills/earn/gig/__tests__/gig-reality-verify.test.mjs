// node:test — RED (Phase 2a, feature gig-reality-verify, VCSDD-lean).
// REQ-004/005 (specs/behavioral-spec.md §8 増分2b): gig_reality_verify.sh does not exist yet ->
// fs.existsSync assertions fail -> RED. auditor.sh does not yet call it -> RED.
// Static/structural checks only (no live network/browser/LLM call here — that is the Green-phase
// self-verification "own-eyes" run, documented separately and never faked in a unit test).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const VERIFY_SH = path.join(DIR, 'gig_reality_verify.sh');
const JUDGE_PY = path.join(DIR, 'gig_judge.py');
const AUDITOR_SH = path.join(DIR, 'auditor.sh');

test('gig_reality_verify.sh exists', () => {
  assert.ok(fs.existsSync(VERIFY_SH), 'gig_reality_verify.sh missing');
});

test('gig_judge.py exists', () => {
  assert.ok(fs.existsSync(JUDGE_PY), 'gig_judge.py missing');
});

test('gig_reality_verify.sh: bash -n syntax check passes', () => {
  assert.ok(fs.existsSync(VERIFY_SH), 'gig_reality_verify.sh missing');
  // throws if bash -n reports a syntax error
  execFileSync('bash', ['-n', VERIFY_SH]);
});

test('gig_reality_verify.sh: reads all three claim jsonl sources', () => {
  const src = fs.readFileSync(VERIFY_SH, 'utf8');
  for (const f of ['shuppin.jsonl', 'applied.jsonl', 'earnings.jsonl']) {
    assert.ok(src.includes(f), `does not reference ${f}`);
  }
});

test('gig_reality_verify.sh: spawns a FRESH claude -p (report-independent, non-interactive)', () => {
  const src = fs.readFileSync(VERIFY_SH, 'utf8');
  assert.ok(/claude\s+-p\b/.test(src), 'does not spawn `claude -p`');
  assert.ok(src.includes('--dangerously-skip-permissions'), 'missing --dangerously-skip-permissions');
  assert.ok(src.includes('--add-dir'), 'missing --add-dir (browser/CDP + home file access)');
  assert.ok(/env\s+-u\s+ANTHROPIC_API_KEY/.test(src), 'missing env -u ANTHROPIC_API_KEY (subscription session, not API billing)');
});

test('gig_reality_verify.sh: caps the fresh spawn with a timeout (no infinite hang)', () => {
  const src = fs.readFileSync(VERIFY_SH, 'utf8');
  // accepts a literal-seconds timeout (`timeout 600 ...`) OR a timeout-seconds variable
  // (`timeout "$TIMEOUT_SECS" ...` where TIMEOUT_SECS=<int> is set earlier in the script).
  assert.ok(/\btimeout\s+("?\$\w+"?|\d+)\b/.test(src), 'no `timeout <seconds>` guard around the claude -p spawn');
});

test('gig_reality_verify.sh: writes audit-reality.jsonl', () => {
  const src = fs.readFileSync(VERIFY_SH, 'utf8');
  assert.ok(src.includes('audit-reality.jsonl'), 'does not write ~/gig/audit-reality.jsonl');
});

test('gig_reality_verify.sh: writes selfheal-request on verdict false', () => {
  const src = fs.readFileSync(VERIFY_SH, 'utf8');
  assert.ok(src.includes('.gig-core-selfheal-request.json'), 'does not reference the selfheal-request file');
});

test('gig_reality_verify.sh: stdout-JSON-only discipline (work goes to stderr, not bare echo to stdout mid-script)', () => {
  const src = fs.readFileSync(VERIFY_SH, 'utf8');
  const lines = src.split('\n');
  // Every bare (unredirected) `echo`/`print` line before the final JSON emission must be commented
  // out OR redirected to stderr (>&2) OR be inside a log-file redirect. We assert there is at least
  // one explicit >&2 redirect (diagnostic channel exists) and no bare `echo "..."` line lacking a
  // redirect AND lacking JSON-looking content (heuristic: a line that echoes free text with no `{`
  // and no `>&2` is a stdout-pollution smell).
  const hasStderrChannel = />&2/.test(src);
  assert.ok(hasStderrChannel, 'no >&2 diagnostic channel found — risk of stdout pollution');
  const polluting = lines.filter((l) => {
    const t = l.trim();
    if (!t.startsWith('echo ')) return false;
    if (t.includes('>&2')) return false;
    if (t.includes('>>') || / > /.test(t)) return false; // redirected to a file, never touches real stdout
    if (t.includes('{')) return false; // JSON-looking final emission is allowed on stdout
    if (/\$\{?(ROW|PARSED_ROW|JSON_ROW|RESULT)\}?"/i.test(t)) return false; // a JSON-holding variable
    if (t.startsWith('#')) return false;
    return true;
  });
  assert.deepEqual(polluting, [], `bare non-JSON echo to stdout found: ${JSON.stringify(polluting)}`);
});

test('auditor.sh: calls gig_reality_verify.sh after the deterministic verdict block', () => {
  const src = fs.readFileSync(AUDITOR_SH, 'utf8');
  assert.ok(src.includes('gig_reality_verify.sh'), 'auditor.sh does not call gig_reality_verify.sh');
  const verdictIdx = src.indexOf('audit.jsonl');
  const callIdx = src.indexOf('gig_reality_verify.sh');
  assert.ok(verdictIdx !== -1 && callIdx > verdictIdx, 'gig_reality_verify.sh call must come after the existing audit.jsonl verdict block');
});

test('auditor.sh: bash -n syntax check passes', () => {
  execFileSync('bash', ['-n', AUDITOR_SH]);
});

test('auditor.sh: existing deterministic PY heredoc verdict logic markers still present (regression)', () => {
  const src = fs.readFileSync(AUDITOR_SH, 'utf8');
  for (const marker of ['SETTLED', 'progressing', 'jpy_earned', 'audit.jsonl']) {
    assert.ok(src.includes(marker), `regression: missing existing marker ${marker}`);
  }
});

// ─── fresh-adversary fix round (FIND-001/002/003): reproducible nav + deterministic evidence gate ──

test('gig_reality_verify.sh: generates a STABLE pass_id BEFORE spawning the judge (REQ-008)', () => {
  const src = fs.readFileSync(VERIFY_SH, 'utf8');
  assert.ok(/PASS_ID=/.test(src), 'no PASS_ID variable generated');
  const passIdIdx = src.indexOf('PASS_ID=');
  // match the ACTUAL invocation line ("$CLAUDE" -p ...), not any comment/doc text that merely
  // mentions "claude -p" (this file's header comments do, well before PASS_ID is generated).
  const spawnIdx = src.search(/"\$CLAUDE"\s+-p\b/);
  assert.ok(passIdIdx !== -1 && spawnIdx !== -1 && passIdIdx < spawnIdx, 'PASS_ID must be generated BEFORE the claude -p spawn');
});

test('gig_reality_verify.sh: embeds the pass_id into the prompt (build_verifier_prompt call)', () => {
  const src = fs.readFileSync(VERIFY_SH, 'utf8');
  assert.ok(/build_verifier_prompt\(claims,\s*pass_id/.test(src) || /build_verifier_prompt\(\s*claims,\s*\w*pass_id/i.test(src),
    'gig_reality_verify.sh does not pass pass_id into build_verifier_prompt');
});

test('gig_reality_verify.sh: uses the deterministic evidence gate (gig_reality_gate.py), not a bare parse-and-trust', () => {
  const src = fs.readFileSync(VERIFY_SH, 'utf8');
  assert.ok(src.includes('gig_reality_gate.py'), 'gig_reality_verify.sh does not call scripts/gig_reality_gate.py');
});

test('gig_reality_verify.sh: records a run_start timestamp before the spawn (min_ts bound for the gate)', () => {
  const src = fs.readFileSync(VERIFY_SH, 'utf8');
  assert.ok(/RUN_START/.test(src), 'no RUN_START timestamp captured for the evidence-window bound');
});

test("gig_reality_verify.sh: required evidence count is derived from DEFAULT_GROUND_TRUTH_URLS, not hardcoded blind", () => {
  const src = fs.readFileSync(VERIFY_SH, 'utf8');
  assert.ok(/DEFAULT_GROUND_TRUTH_URLS/.test(src), 'gig_reality_verify.sh does not derive required_count from DEFAULT_GROUND_TRUTH_URLS');
});
