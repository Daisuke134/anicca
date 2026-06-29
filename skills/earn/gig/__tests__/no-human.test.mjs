// node:test — D4: PROVE the whole slot is no-human (audit every executable file).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { auditNoHuman } from '../lib/no-human.mjs';

const SLOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');

function execFiles() {
  const out = [];
  out.push({ path: 'run.sh', content: fs.readFileSync(path.join(SLOT, 'run.sh'), 'utf8') });
  for (const f of fs.readdirSync(path.join(SLOT, 'lib'))) {
    if (f === 'no-human.mjs') continue; // the auditor legitimately contains the patterns it detects
    if (f.endsWith('.mjs')) out.push({ path: 'lib/' + f, content: fs.readFileSync(path.join(SLOT, 'lib', f), 'utf8') });
  }
  return out;
}

test('the slot has ZERO human-in-the-loop steps (D4)', () => {
  const v = auditNoHuman(execFiles());
  assert.deepEqual(v, [], 'human-step violations: ' + JSON.stringify(v));
});

test('the audit actually catches a planted human step (not a no-op)', () => {
  const v = auditNoHuman([{ path: 'evil.sh', content: 'read -p "enter code" CODE' },
                          { path: 'evil2.mjs', content: 'const x = await prompt("ask the user")' }]);
  assert.ok(v.length >= 2, 'audit failed to catch planted human steps');
});
