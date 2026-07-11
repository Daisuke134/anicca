// REQ-001..004 — runtime/anicca-daemon.sh Franklin-family instance-classification tests
// (franklin2-daemon-identity, P4-code, 2026-07-11).
//
// Franklin2's launchd plist sets ANICCA_INSTANCE=franklin2, but daemon.sh's 3 routing call sites
// (brain-probe / telemetry-poster choice / wallet-address derivation) literal-match ONLY
// `"$INSTANCE" = "franklin"`, so Franklin2 falls to the default/EVM path and runs walletless — see
// docs/loop-engineering/20-implementation-certainty-2026-07-11.md §C (anicca-project) Gap B.
//
// Method (mirrors runtime/loop/__tests__/daemon-script-franklin-routing.test.mjs's PORT_SNIPPET
// technique): extract the new, pure, side-effect-free `is_franklin_instance()` predicate verbatim from
// the REAL daemon.sh source text and execute it in a throwaway /bin/bash subshell (no git/curl/node/
// pkill side effects ever triggered) — plus static regex assertions over the source text confirming the
// 3 call sites were actually rewired to use it (PROP-005).
//
// RED PHASE: today, `is_franklin_instance()` does not exist anywhere in daemon.sh, and all 3 call sites
// still read the literal `[ "$INSTANCE" = "franklin" ]`. Every test below FAILS until Phase 2b.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DAEMON_PATH = path.resolve(__dirname, '../../anicca-daemon.sh');
const source = fs.readFileSync(DAEMON_PATH, 'utf8');

// Extracts the `is_franklin_instance() { ... }` function definition verbatim, up to (and including)
// the first standalone closing brace after it. Pure text slice — never executes anything itself.
function extractClassifierFunction(text) {
  const match = text.match(/is_franklin_instance\(\)\s*\{[\s\S]*?\n\}\n/);
  if (!match) {
    throw new Error(
      'is_franklin_instance() function not found in anicca-daemon.sh (RED phase expected: REQ-001 not yet implemented)',
    );
  }
  return match[0];
}

function classify(instance) {
  const fn = extractClassifierFunction(source);
  const result = spawnSync(
    '/bin/bash',
    ['-c', `${fn}\nis_franklin_instance "$1" && echo MATCH || echo NOMATCH`, '_', instance === undefined ? '' : instance],
    { env: { PATH: '/usr/bin:/bin' }, encoding: 'utf8', timeout: 5000 },
  );
  assert.equal(result.error, undefined, `bash subshell must run cleanly (stderr: ${result.stderr})`);
  return result.stdout.trim();
}

test('REQ-001 PROP-001 (regression): is_franklin_instance("franklin") matches — the original citizen, unchanged', () => {
  assert.equal(classify('franklin'), 'MATCH');
});

test('REQ-001 PROP-002 (new): is_franklin_instance("franklin2") matches — the exact bug this feature fixes', () => {
  assert.equal(classify('franklin2'), 'MATCH');
});

test('REQ-001 PROP-003: is_franklin_instance matches franklin + any digit-run (franklin3, franklin10, franklin99)', () => {
  for (const value of ['franklin3', 'franklin10', 'franklin99']) {
    assert.equal(classify(value), 'MATCH', `expected ${value} to match`);
  }
});

test('REQ-001/REQ-004 PROP-004: is_franklin_instance rejects non-matching decoys (fail-closed)', () => {
  const decoys = ['clawrouter', '', 'franklinX', 'franklins', 'franklin-2', 'franklin2x', 'Franklin2'];
  for (const value of decoys) {
    assert.equal(classify(value), 'NOMATCH', `expected ${JSON.stringify(value)} to NOT match`);
  }
});

test('REQ-001 PROP-005 (static): all 3 daemon call sites use is_franklin_instance — zero remaining literal `"$INSTANCE" = "franklin"` string-equality left in the file', () => {
  assert.equal(
    (source.match(/"\$INSTANCE"\s*=\s*"franklin"/g) || []).length,
    0,
    'no call site may still literal-match only "franklin" — franklin2/franklin3/... would fall through',
  );
  const classifierCalls = (source.match(/is_franklin_instance\s+"\$INSTANCE"/g) || []).length;
  assert.equal(classifierCalls, 3, `expected exactly 3 call sites (brain/telemetry/wallet) to use is_franklin_instance "$INSTANCE", found ${classifierCalls}`);
});

test('REQ-002(b): step-3 telemetry branch condition now reached for franklin2 (static: step 3 still selects telemetry-post-franklin.mjs behind is_franklin_instance)', () => {
  const step3Start = source.indexOf('# 3. telemetry poster');
  const step4Start = source.indexOf('# 4. brain endpoint');
  assert.ok(step3Start !== -1 && step4Start !== -1, 'expected step 3/4 markers to exist in daemon.sh');
  const step3 = source.slice(step3Start, step4Start);
  assert.ok(/is_franklin_instance "\$INSTANCE"/.test(step3), 'step 3 must gate on is_franklin_instance "$INSTANCE"');
  assert.ok(/telemetry-post-franklin\.mjs/.test(step3), 'step 3 franklin branch must still loop telemetry-post-franklin.mjs');
});

test('REQ-002(c): step-4 wallet-derivation branch condition now reached for franklin2 (static: step 4 still selects wallet-address-solana.mjs behind is_franklin_instance)', () => {
  const step4Start = source.indexOf('# 4. brain endpoint');
  const execStart = source.indexOf('# 5. run the loop');
  assert.ok(step4Start !== -1 && execStart !== -1, 'expected step 4/5 markers to exist in daemon.sh');
  const step4 = source.slice(step4Start, execStart);
  assert.ok(/is_franklin_instance "\$INSTANCE"/.test(step4), 'step 4 must gate on is_franklin_instance "$INSTANCE"');
  assert.ok(/wallet-address-solana\.mjs/.test(step4), 'step 4 franklin branch must still derive via wallet-address-solana.mjs');
});

test('REQ-003 (regression): non-franklin/unset still resolves to the default EVM/ClawRouter path (static: step 4 else-branch still uses wallet-address.mjs, not solana)', () => {
  const step4Start = source.indexOf('# 4. brain endpoint');
  const execStart = source.indexOf('# 5. run the loop');
  const step4 = source.slice(step4Start, execStart);
  assert.ok(/wallet-address\.mjs/.test(step4), 'non-franklin else-branch must still use the EVM wallet-address.mjs helper');
});

test('impl-review iteration-1 FIND-002 fix (static): the franklin-branch telemetry pkill is scoped to THIS instance\'s own $ANICCA_HOME, never an unscoped script-path-only pattern that would also match a concurrently-running sibling Franklin instance', () => {
  const step3Start = source.indexOf('# 3. telemetry poster');
  const step4Start = source.indexOf('# 4. brain endpoint');
  assert.ok(step3Start !== -1 && step4Start !== -1, 'expected step 3/4 markers to exist in daemon.sh');
  const step3 = source.slice(step3Start, step4Start);
  assert.ok(
    /pkill -f "dashboard\/telemetry-post-franklin\.mjs --home \$ANICCA_HOME"/.test(step3),
    'the telemetry pkill pattern must include --home $ANICCA_HOME so it cannot match another instance\'s poster process (FIND-002)',
  );
  assert.ok(
    !/pkill -f "dashboard\/telemetry-post-franklin\.mjs"\s*2>\/dev\/null/.test(step3),
    'no unscoped (script-path-only) pkill pattern for telemetry-post-franklin.mjs may remain (FIND-002 regression guard)',
  );
  assert.ok(
    /node "\$REPO\/runtime\/dashboard\/telemetry-post-franklin\.mjs" --home "\$ANICCA_HOME"/.test(step3),
    'the poster must be launched with the --home "$ANICCA_HOME" argv marker so the scoped pkill pattern above can actually match it',
  );
});

test('impl-review iteration-2 FIND-001 fix (static): a one-time, end-anchored legacy-poster cleanup pkill is present, positioned after the scoped pkill and before the poster is (re)launched', () => {
  const step3Start = source.indexOf('# 3. telemetry poster');
  const step4Start = source.indexOf('# 4. brain endpoint');
  const step3 = source.slice(step3Start, step4Start);
  const scopedIdx = step3.indexOf('pkill -f "dashboard/telemetry-post-franklin.mjs --home $ANICCA_HOME"');
  const legacyIdx = step3.indexOf('pkill -f "dashboard/telemetry-post-franklin\\.mjs$"');
  const launchIdx = step3.indexOf('node "$REPO/runtime/dashboard/telemetry-post-franklin.mjs" --home "$ANICCA_HOME"');
  assert.ok(scopedIdx !== -1, 'expected the FIND-002(iter1) scoped pkill pattern to still be present');
  assert.ok(legacyIdx !== -1, 'expected a new end-anchored legacy-cleanup pkill pattern (FIND-001 iter2 fix)');
  assert.ok(launchIdx !== -1, 'expected the poster launch line to still be present');
  assert.ok(scopedIdx < legacyIdx && legacyIdx < launchIdx, 'legacy-cleanup pkill must run after the scoped pkill and before the poster is (re)launched');
});

test('impl-review iteration-2 FIND-002 fix (static): the dead env-var pkill ("FRANKLIN_TELEMETRY_LOOP") is gone — pkill -f matches argv, not exported environment variables, so it never matched anything', () => {
  const step3Start = source.indexOf('# 3. telemetry poster');
  const step4Start = source.indexOf('# 4. brain endpoint');
  const step3 = source.slice(step3Start, step4Start);
  assert.ok(
    !/pkill -f "FRANKLIN_TELEMETRY_LOOP"/.test(step3),
    'the dead pkill -f "FRANKLIN_TELEMETRY_LOOP" line must be removed (it matches argv, never an exported env var)',
  );
  // The export itself is untouched (harmless env marker on the poster subshell) — only the
  // ineffective pkill targeting it was dead code.
  assert.ok(/export FRANKLIN_TELEMETRY_LOOP=1/.test(step3), 'the FRANKLIN_TELEMETRY_LOOP export on the poster subshell is unrelated dead-pkill scope and must remain untouched');
});

test('impl-review iteration-2 FIND-001 fix — match-matrix simulation: applies the scoped pattern and the new legacy end-anchored pattern to real legacy/new-format argv strings for BOTH live instances, exactly reproducing pkill -f ERE semantics via grep -E', () => {
  // Real deployed --home values (from ai.anicca.franklin-loop.plist / ai.anicca.franklin2-loop.plist,
  // as confirmed in iteration-2 notes.md / iteration-1 FIND-002).
  const HOME_FRANKLIN = '/Users/operator/.blockrun';
  const HOME_FRANKLIN2 = '/Users/operator/.franklin2-home/.blockrun';
  const SCRIPT = 'node /Users/operator/anicca/runtime/dashboard/telemetry-post-franklin.mjs';

  const argv = {
    franklin_legacy: SCRIPT, // pre-29023a55: no --home argv marker at all
    franklin_new: `${SCRIPT} --home ${HOME_FRANKLIN}`,
    franklin2_legacy: SCRIPT, // identical text to franklin_legacy — legacy argv never differentiates instances
    franklin2_new: `${SCRIPT} --home ${HOME_FRANKLIN2}`,
  };

  function pkillMatches(pattern, text) {
    const result = spawnSync('/usr/bin/grep', ['-E', pattern], { input: text, encoding: 'utf8' });
    return result.status === 0;
  }

  const scopedPattern = (home) => `dashboard/telemetry-post-franklin\\.mjs --home ${home.replace(/[.]/g, '\\.')}`;
  const legacyPattern = 'dashboard/telemetry-post-franklin\\.mjs$';

  // Scoped pattern for franklin's own $ANICCA_HOME: matches ONLY franklin_new.
  assert.equal(pkillMatches(scopedPattern(HOME_FRANKLIN), argv.franklin_legacy), false);
  assert.equal(pkillMatches(scopedPattern(HOME_FRANKLIN), argv.franklin_new), true);
  assert.equal(pkillMatches(scopedPattern(HOME_FRANKLIN), argv.franklin2_legacy), false);
  assert.equal(pkillMatches(scopedPattern(HOME_FRANKLIN), argv.franklin2_new), false);

  // Scoped pattern for franklin2's own $ANICCA_HOME: matches ONLY franklin2_new.
  assert.equal(pkillMatches(scopedPattern(HOME_FRANKLIN2), argv.franklin_legacy), false);
  assert.equal(pkillMatches(scopedPattern(HOME_FRANKLIN2), argv.franklin_new), false);
  assert.equal(pkillMatches(scopedPattern(HOME_FRANKLIN2), argv.franklin2_legacy), false);
  assert.equal(pkillMatches(scopedPattern(HOME_FRANKLIN2), argv.franklin2_new), true);

  // Legacy end-anchored pattern: matches ONLY markerless (legacy) argv, for EITHER instance — never
  // a new-format argv (which always has trailing " --home <path>" so it can't end at ".mjs").
  assert.equal(pkillMatches(legacyPattern, argv.franklin_legacy), true);
  assert.equal(pkillMatches(legacyPattern, argv.franklin_new), false);
  assert.equal(pkillMatches(legacyPattern, argv.franklin2_legacy), true);
  assert.equal(pkillMatches(legacyPattern, argv.franklin2_new), false);
});
