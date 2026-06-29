// node:test — the Coconala LOOP (the artifact that actually runs) must have NO human in the daily op.
// Adversary F1: the old no-human audit scanned run.sh/lib (now archived), never gig-cli.sh. This scans
// the live loop files for any runtime human-step (ask/approve/manual click/stdin prompt).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const FILES = ['gig-cli.sh', 'producer.sh', 'monitor.sh', 'gig-healthcheck.sh'];

// runtime human-step patterns (the one allowed human element — Dais's one-time KYC/account — is not a
// runtime step and is only mentioned in comments, which we strip before scanning).
const FORBIDDEN = [
  /\bask (the )?(user|human|dais)\b/i,
  /\bwait for (human|approval|dais)\b/i,
  /\bmanual(ly)? (enter|type|click|approve)\b/i,
  /\bread -p\b/,
  /\bprompt the (user|human)\b/i,
];

function stripComments(src, isShell) {
  return src.split('\n').map(l => {
    if (isShell) return l.replace(/(^|\s)#.*$/, '$1');   // shell comments
    return l;
  }).join('\n');
}

for (const f of FILES) {
  test(`${f}: no runtime human-in-the-loop step`, () => {
    const p = path.join(DIR, f);
    assert.ok(fs.existsSync(p), `${f} missing`);
    const code = stripComments(fs.readFileSync(p, 'utf8'), f.endsWith('.sh'));
    for (const re of FORBIDDEN) {
      assert.ok(!re.test(code), `${f} contains a human-loop step matching ${re}`);
    }
  });
}

test('gig-cli.sh routes blockers to autonomous paths (captcha/OTP/login), never a human', () => {
  const code = fs.readFileSync(path.join(DIR, 'gig-cli.sh'), 'utf8');
  assert.ok(/CapSolver/i.test(code), 'no CapSolver captcha path');
  assert.ok(/gog gmail|OTP/i.test(code), 'no OTP autonomous path');
  assert.ok(/blocker is NOT a stop/i.test(code), 'blocker-is-not-stop not asserted');
  assert.ok(/do NOT claim USDC|do NOT call record-earn/i.test(code), 'no-fake-earn guard missing');
});
