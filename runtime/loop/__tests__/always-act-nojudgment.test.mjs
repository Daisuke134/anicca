// franklin-alwaysact-skill-router — Phase 2a (RED phase), REQ-507 / PROP-507b.
//
// PROP-507a (the "for every slot in the menu, the harness executes exactly that slot with exactly
// those args" property, plus its args-blind-membership-check pure property) lives in
// always-act-router.test.mjs (isRejectableSleepOrOffMenu's slot-only membership check) and
// always-act-reroute.test.mjs (one concrete spawn-based confirmation that arbitrary args content
// reaches skill execution unmodified). This file is PROP-507b only: the static, Tier-0, grep-based
// "the pure-core module never branches on model-chosen content" check.
//
// `runtime/loop/always-act-router.mjs` does not exist yet — this test currently fails with ENOENT
// (fs.readFile on a nonexistent path), which is the correct RED signal: there is no way to prove "the
// module contains no regex/args-content branching" before the module exists.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { promises as fs } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const MODULE_PATH = path.resolve(__dirname, '../always-act-router.mjs');

test('PROP-507b (static, Tier 0): always-act-router.mjs contains no RegExp/.match(/.test( call, and no if(args./switch(slot)-style branching keyed on model-chosen slot/args CONTENT', async () => {
  let source;
  try {
    source = await fs.readFile(MODULE_PATH, 'utf8');
  } catch (err) {
    assert.fail(`always-act-router.mjs must exist for this static check to run (RED phase: ${err.message})`);
  }

  // Strip comments and string literals first so a comment/log-message MENTIONING the word "RegExp" (as
  // this very file's own docstring does) never produces a false positive.
  const stripped = source
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/\/\/.*$/gm, '')
    .replace(/`(?:[^`\\]|\\.)*`/g, '``')
    .replace(/"(?:[^"\\]|\\.)*"/g, '""')
    .replace(/'(?:[^'\\]|\\.)*'/g, "''");

  assert.doesNotMatch(stripped, /new\s+RegExp\s*\(/, 'no dynamic RegExp construction');
  assert.doesNotMatch(stripped, /\/(?:(?!\/).)+\/[a-z]*\.(?:test|exec)\s*\(/, 'no /pattern/.test()/.exec() literal regex usage');
  assert.doesNotMatch(stripped, /\.match\s*\(/, 'no .match( call');
  assert.doesNotMatch(stripped, /\bargs\s*\.\s*strategy\b/, 'no args.strategy-keyed branching (the canonical forbidden pattern this REQ names)');
  assert.doesNotMatch(stripped, /switch\s*\(\s*slot\s*\)/, 'no switch(slot) branching on the model-chosen slot value');

  // Positive control: registry BOOKKEEPING-field branching (status/risk/alwaysAvailable) IS expected
  // and allowed — assert the module actually contains at least one of these (proving the check above
  // is discriminating "bookkeeping" from "content", not merely finding an empty file).
  assert.match(source, /\brisk\b/, 'sanity: the module must reference the registry risk field somewhere');
});
