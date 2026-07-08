// parse-pass.mjs — deterministic, total parser for franklin-trading's own fixed-format
// "Signature: <base58>" receipt line (REQ-002 / PROP-010). NOT judgment: the trading decision
// already happened; this only reads the CLI's own receipt back (parsing of a fixed machine
// format, consistent with the project's regex-for-judgment ban, which targets decision-making,
// not fixed-format log parsing). Multiple "Signature:" lines can appear in one pass's stdout
// (a multi-step swap chain in a single session) -- REQ-002 mandates recording only the LAST one
// (one ledger line per pass, matching every other earn skill's append-only convention).
const ANSI_RE = /\x1b\[[0-9;]*m/g;
// base58 alphabet (no 0 O I l), 60-100 chars covers real Solana signatures (~87-88 chars) with
// slack for format drift, mirroring solana-verify.mjs's own B58_RE discipline.
const SIG_RE = /signature:\s*([1-9A-HJ-NP-Za-km-z]{60,100})/gi;

export function extractLastSignature(stdout) {
  if (typeof stdout !== "string" || stdout.length === 0) return null;
  const clean = stdout.replace(ANSI_RE, "");
  let last = null;
  for (const m of clean.matchAll(SIG_RE)) {
    last = m[1];
  }
  return last;
}

// CLI: `printf '%s' "$OUT" | node parse-pass.mjs` reads the full captured pass stdout from
// stdin and prints ONLY the last signature (nothing if none) -- run.sh uses this instead of
// the old inline `head -1` (which took the FIRST signature; REQ-002 requires the LAST).
import path from "node:path";
import { fileURLToPath } from "node:url";

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  let input = "";
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (chunk) => { input += chunk; });
  process.stdin.on("end", () => {
    const sig = extractLastSignature(input);
    if (sig) process.stdout.write(sig + "\n");
  });
}
