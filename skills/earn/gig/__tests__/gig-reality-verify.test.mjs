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

test('gig_reality_verify.sh: uses the bounded tool judge route through common runner', () => {
  const src = fs.readFileSync(VERIFY_SH, 'utf8');
  assert.ok(src.includes('agent_runner.py'), 'does not invoke common runner');
  assert.ok(/--task-class\s+tool-agent/.test(src), 'judge is not routed as bounded tool-agent');
  assert.ok(!/--task-class\s+high-value-agent/.test(src), 'read-only audit must not use high-value route');
  assert.ok(!/--model\s+|sonnet|"\$CLAUDE"/i.test(src), 'provider/model leaked into business script');
});

test('auditor.sh: expensive reality judge is cadence-gated to six hours', () => {
  const src = fs.readFileSync(AUDITOR_SH, 'utf8');
  assert.match(src, /REALITY_VERIFY_INTERVAL_SECS=.*21600/, 'missing six-hour reality cadence');
  assert.ok(src.includes('.reality-verify-last-start'), 'missing durable cadence marker');
});

test('gig_reality_verify.sh: consumes runner timeout evidence', () => {
  const src = fs.readFileSync(VERIFY_SH, 'utf8');
  assert.ok(src.includes('attempts.jsonl') && src.includes('timed_out'), 'runner timeout evidence not consumed');
});

test('gig_reality_verify.sh: shares the Gig daily token breaker and handles exit 75', () => {
  const src = fs.readFileSync(VERIFY_SH, 'utf8');
  assert.ok(src.includes('ANICCA_BUDGET_SCOPE_ID="$PASS_ID"'), 'audit budget scope missing');
  assert.ok(src.includes('GIG_DAILY_TOKEN_BUDGET:-262144'), 'shared daily budget missing');
  assert.match(src, /JUDGE_RC"\s+-eq\s+75/, 'budget circuit exit is not handled');
  assert.ok(src.includes('budget_blocked'), 'budget stop reason is not persisted');
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
  const spawnIdx = src.search(/python3\s+"\$RUNNER"/);
  assert.ok(passIdIdx !== -1 && spawnIdx !== -1 && passIdIdx < spawnIdx, 'PASS_ID must be generated BEFORE runner spawn');
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

// ─── auth-wall cooldown (2026-07-13 self-fix, gh#1015): reached_captcha=true (login wall) is an ──
// external/session precondition, not a code bug — auditor.sh must not respawn a full self-fix.sh
// agent every hourly audit pass for an unchanged, already-diagnosed condition.

test('gig_reality_verify.sh: selfheal-request classifies kind from reached_captcha (auth_wall vs claim_mismatch)', () => {
  const src = fs.readFileSync(VERIFY_SH, 'utf8');
  assert.ok(/reached_captcha/.test(src), 'does not read reached_captcha from the judge verdict');
  assert.ok(/'auth_wall'/.test(src) && /'claim_mismatch'/.test(src), 'does not classify selfheal-request kind into auth_wall/claim_mismatch');
  assert.ok(/'kind'\s*:\s*kind/.test(src), 'does not write the kind field into the selfheal-request JSON');
});

test('auditor.sh: cooldown-gates auth_wall selfheal requests before spawning self-fix.sh', () => {
  const src = fs.readFileSync(AUDITOR_SH, 'utf8');
  assert.ok(src.includes('AUTH_WALL_COOLDOWN_SECS'), 'no auth-wall cooldown window defined');
  assert.ok(src.includes('AUTH_WALL_COOLDOWN_MARKER'), 'no auth-wall cooldown marker file');
  assert.ok(/KIND.*=.*auth_wall|auth_wall.*=.*KIND/.test(src) || /"\$KIND"\s*=\s*"auth_wall"/.test(src), 'does not branch on kind=auth_wall');
  // the cooldown gate must precede the self-fix.sh spawn call, and claim_mismatch must remain reachable
  const kindIdx = src.indexOf("KIND=");
  const spawnIdx = src.indexOf('bash "$SELF_FIX"');
  assert.ok(kindIdx !== -1 && spawnIdx !== -1 && kindIdx < spawnIdx, 'kind must be read before the self-fix.sh spawn decision');
});

test('auditor.sh: still consumes (rm -f) the selfheal-request even when cooldown-skipped (no stale request pileup)', () => {
  const src = fs.readFileSync(AUDITOR_SH, 'utf8');
  const selfHealBlockStart = src.indexOf('SELFHEAL_REQ=');
  const block = src.slice(selfHealBlockStart);
  assert.ok(/rm -f "\$SELFHEAL_REQ"/.test(block), 'selfheal-request file is never removed');
});
