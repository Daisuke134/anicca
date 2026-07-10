/**
 * harness-health-no-autoaction.test.mjs — RED/regression guard (Phase 2a, feature
 * anicca-harness-tooluse-health). R10 / INV-NO-AUTOACTION (behavioral-spec.md +
 * verification-architecture.md proof table row "R10 | static/code-review").
 *
 * This feature is READ/OBSERVE/RECORD only: nothing built in this slice may call
 * skills/self/self-fix.sh (that wiring is explicit FOLLOW-UP work, out of scope here).
 * A permanent, machine-checked regression guard: grep the two directories this feature
 * touches for any "self-fix.sh" call-site string. Passes today (pre-feature: zero
 * matches, confirmed by hand) and must keep passing after Phase 2b's GREEN implementation.
 */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');

test('R10: grep -rn "self-fix.sh" runtime/loop/ skills/self/self-improve/ (excluding this feature\'s own test/spec prose) returns ZERO matches', () => {
  // --exclude-dir=__tests__/tests: this feature's OWN test files (this file included) must be free to
  // document/reference the string "self-fix.sh" in comments (as this file's header does) without
  // tripping their own regression guard -- the guard is about PRODUCTION call sites, not prose.
  let output = '';
  try {
    output = execFileSync('grep', [
      '-rn',
      '--exclude-dir=__tests__',
      '--exclude-dir=tests',
      'self-fix.sh',
      path.join(REPO_ROOT, 'runtime', 'loop'),
      path.join(REPO_ROOT, 'skills', 'self', 'self-improve'),
    ], { encoding: 'utf8' });
  } catch (err) {
    // grep exits 1 when there are no matches -- that is the PASS condition here.
    if (err.status === 1) {
      output = '';
    } else {
      throw err;
    }
  }
  assert.equal(output.trim(), '', `no new self-fix.sh call site may be introduced by this feature; found:\n${output}`);
});
