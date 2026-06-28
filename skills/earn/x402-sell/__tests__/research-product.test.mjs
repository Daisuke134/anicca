// E2E (no-mock) test for research-product.mjs — real DDG + Jina network calls, $0.
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { readFileSync } from 'node:fs';
import assert from 'node:assert';

const execFileP = promisify(execFile);
const here = dirname(fileURLToPath(import.meta.url));
const SCRIPT = join(here, '..', 'research-product.mjs');

let pass = 0, fail = 0;
const ok = (cond, msg) => { if (cond) { pass++; console.log('PASS', msg); } else { fail++; console.log('FAIL', msg); } };

// R5 (static): no paid/keyed service references
const src = readFileSync(SCRIPT, 'utf8');
ok(!/TWITTERAPI_KEY|FIRECRAWL_API_KEY|OPENAI_API_KEY|CDP_API_KEY/.test(src), 'R5 no paid-key env referenced');

// R3 + R1 + R2: real run returns valid JSON with non-empty digest + real sources
try {
  const { stdout } = await execFileP('node', [SCRIPT, 'x402 agent payments base'], { timeout: 60000, maxBuffer: 8 << 20 });
  const j = JSON.parse(stdout);
  ok(Array.isArray(j.sources) && j.sources.length >= 1, 'R1 >=1 real source');
  ok(j.sources.every((s) => /^https?:\/\//.test(s.url)), 'R1 sources are real external URLs');
  ok(typeof j.digest === 'string' && j.digest.length > 200, 'R3 non-empty digest (>200 chars)');
} catch (e) { ok(false, 'R1-R3 real run: ' + (e && e.message)); }

// R4: empty query exits non-zero with no JSON on stdout
try {
  await execFileP('node', [SCRIPT, ''], { timeout: 10000 });
  ok(false, 'R4 empty query should exit non-zero');
} catch (e) {
  ok(e.code !== 0, 'R4 empty query exits non-zero');
  ok(!String(e.stdout || '').trim(), 'R4 no fake JSON on stdout for empty query');
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
