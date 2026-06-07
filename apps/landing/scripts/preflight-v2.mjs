// taste-skill §v2.10 mechanical acceptance gate.
// Usage: node scripts/preflight-v2.mjs
// Exit 1 if any of out/en.html / out/ja.html / out/install.html is missing
// OR contains case-insensitive placeholder copy.

import { readFileSync, statSync } from 'node:fs';

const ROUTES = ['out/en.html', 'out/ja.html', 'out/install.html'];
// Patterns case-insensitive. Word-boundary on TODO / TBD / XXXX so longer
// product names containing them aren't flagged (none expected, but safer).
const PATTERNS = [/\bTODO\b/i, /\bTBD\b/i, /T\.B\.D\./i, /coming soon/i, /placeholder/i, /\bXXXX\b/i];

let fail = 0;
for (const f of ROUTES) {
  try {
    statSync(f);
  } catch {
    console.log(`FAIL missing route: ${f}`);
    fail++;
    continue;
  }
  const html = readFileSync(f, 'utf8');
  for (const re of PATTERNS) {
    const m = html.match(re);
    if (m) {
      console.log(`FAIL placeholder pattern ${re} in ${f}: "${m[0]}"`);
      fail++;
    }
  }
}
if (fail === 0) {
  console.log(`PREFLIGHT_V2 OK (${ROUTES.length} routes, no placeholders)`);
  process.exit(0);
}
console.log(`PREFLIGHT_V2 FAIL (${fail} violations)`);
process.exit(1);
