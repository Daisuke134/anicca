// E2E (no-mock) test for research-product.mjs — real Wikipedia + HN Algolia + Jina network calls, $0.
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { readFileSync } from 'node:fs';

const execFileP = promisify(execFile);
const here = dirname(fileURLToPath(import.meta.url));
const SCRIPT = join(here, '..', 'research-product.mjs');

let pass = 0, fail = 0;
const ok = (cond, msg) => { if (cond) { pass++; console.log('PASS', msg); } else { fail++; console.log('FAIL', msg); } };

async function run(arg) {
  return execFileP('node', [SCRIPT, arg], { timeout: 70000, maxBuffer: 8 << 20 });
}

// R5 (static): no paid/keyed/secret env referenced (broadened per adversary FIND-005)
const src = readFileSync(SCRIPT, 'utf8');
ok(!/TWITTERAPI_KEY|FIRECRAWL_API_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|BRAVE_API_KEY|CDP_API_KEY|_PRIVATE_KEY|GOOGLE_LOGIN/.test(src), 'R5 no paid/keyed/secret env referenced');
ok(!/https?:\/\/[^\s'"`]*(duckduckgo|bing\.com\/search|google\.com\/search)/i.test(src), 'R1 no bot-blocked search backend actually used (URL form)');

// R1/R2/R3 — TECH query (HN path)
try {
  const { stdout } = await run('x402 agent payments base');
  const j = JSON.parse(stdout);
  ok(Array.isArray(j.sources) && j.sources.length >= 1, 'R1 tech query → >=1 source');
  ok(j.sources.every((s) => /^https?:\/\//.test(s.url)), 'R1 tech sources are real URLs');
  ok(typeof j.digest === 'string' && j.digest.length > 200, 'R3 tech digest non-empty (>200)');
  ok(!/rate limit|too many requests|authentication is required/i.test(j.digest.slice(0, 400)), 'R6 digest is real content, not an error body');
} catch (e) { ok(false, 'R1-R3/R6 tech run: ' + (e && e.message)); }

// R1 UNIVERSALITY — GENERAL non-tech query (Wikipedia path) — adversary FIND-002/004
try {
  const { stdout } = await run('photosynthesis');
  const j = JSON.parse(stdout);
  ok(Array.isArray(j.sources) && j.sources.length >= 1, 'R1 general (non-tech) query → >=1 source (UNIVERSAL)');
  ok(j.digest.length > 200, 'R3 general digest non-empty');
} catch (e) { ok(false, 'R1 general-query universality: ' + (e && e.message)); }

// R4 — empty query exits non-zero, no fake JSON
try {
  await run('');
  ok(false, 'R4 empty query should exit non-zero');
} catch (e) {
  ok(e.code !== 0, 'R4 empty query exits non-zero');
  ok(!String(e.stdout || '').trim(), 'R4 no fake JSON on stdout for empty query');
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
