// node:test — the Coconala LOOP (the artifact that actually runs) must have NO human in the daily op.
// Adversary F1: the old no-human audit scanned run.sh/lib (now archived), never gig-cli.sh. This scans
// the live loop files for any runtime human-step (ask/approve/manual click/stdin prompt).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
// All .sh files that are part of the live loop (add new scripts here when created)
// gig_reality_verify.sh added (feature gig-reality-verify, 増分2b): the fresh-spawn reality-verifier
// runner must also be human-free — it delegates through the common runner and never asks/waits for a human.
const FILES = ['gig-cli.sh', 'monitor.sh', 'gig-healthcheck.sh', 'auditor.sh', 'run.sh', 'gig_reality_verify.sh'];

// runtime human-step patterns (the one allowed human element — Dais's one-time KYC/account — is not a
// runtime step and is only mentioned in comments, which we strip before scanning).
const FORBIDDEN = [
  /\bask (the )?(user|human|dais)\b/i,
  /\bwait for (human|approval|dais)\b/i,
  /\bmanual(ly)? (enter|type|click|approve)\b/i,
  /\bread -p\b/,
  /\bprompt the (user|human)\b/i,
];

// Scan the RAW file (FIND-R3-002): the core's cron prompt is one quoted line containing
// `#5121769`, so a comment-stripper would blind the scan after that token. The FORBIDDEN
// patterns never legitimately appear (the only allowed human element, Dais's one-time KYC,
// does not match them), so scanning raw is both safe and complete.
function scan(code) {
  return FORBIDDEN.filter(re => re.test(code)).map(re => String(re));
}

for (const f of FILES) {
  test(`${f}: no runtime human-in-the-loop step`, () => {
    const p = path.join(DIR, f);
    assert.ok(fs.existsSync(p), `${f} missing`);
    const hits = scan(fs.readFileSync(p, 'utf8'));
    assert.deepEqual(hits, [], `${f} contains human-loop step(s): ${hits.join(', ')}`);
  });
}

test('planted-violation: a human step AFTER a #token is caught (raw scan, not comment-blinded)', () => {
  const poison = 'CronCreate prompt="... TRACK #5121769 specifically. then wait for Dais approval before 応募."';
  assert.ok(scan(poison).length > 0, 'scanner is blind to a violation placed after a # token');
});

test('gig-cli.sh is a provider-free deterministic supervisor', () => {
  const code = fs.readFileSync(path.join(DIR, 'gig-cli.sh'), 'utf8');
  assert.ok(code.includes('gig_core_supervisor.sh'), 'provider-free supervisor missing');
  assert.ok(!/claude\s+-p|codex\s+exec|--model(?:=|\s+)sonnet/i.test(code), 'gig core directly invokes a provider');
});
