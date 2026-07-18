// node:test — the SELF_WALLETS list (shared by verify-inflow.mjs and store-review.mjs) must not
// under-count what it excludes.
//
// WHY (2026-07-16): verify-inflow is the ONLY judge of "did we earn" (SKILL.md step 7), but its
// wallet set was missing addresses that a SIBLING judge had already identified as internal.
// founder-loop/record-earn.mjs:40-49 records the 2026-07-12 forensic finding: 0xf70da978… is the
// source of both of the two largest "earn" rows ever recorded ($22.97 + $7.98), is a plain EOA
// holding >$3.1M USDC on Base, and is therefore funding routed THROUGH us, not revenue. That judge
// fail-closes on it. This one never learned, so it still reports those transfers as EXTERNAL --
// and franklin1's $6.4778 from the same address looked like a first sale.
//
// The rule being pinned: an address that ANY judge in the colony has classified as internal must be
// internal in EVERY judge. Revenue is the number we are least allowed to overstate.
//
// SELF-STORE-1 (2026-07-18): the list moved out of verify-inflow.mjs into lib/self-wallets.mjs so
// store-review.mjs can share it too — this test now reads the shared module directly.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const SRC = readFileSync(new URL("../lib/self-wallets.mjs", import.meta.url), "utf8");
const SIBLING = readFileSync(
  new URL("../../../self/founder-loop/record-earn.mjs", import.meta.url), "utf8",
);

// Read each judge's internal set straight from source: the point is that the two agree, so parsing
// the real files (rather than importing a shared constant that does not exist yet) is what proves it.
// Scoped to the literal itself — a looser window swept in neighbouring constants (the USDC contract
// address) and reported them as missing wallets.
function addressesIn(src, marker) {
  const start = src.indexOf(marker);
  assert.notEqual(start, -1, `${marker} not found — the judge was restructured, revisit this test`);
  const open = src.indexOf("[", start);
  const close = src.indexOf("]", open);
  assert.ok(open !== -1 && close !== -1, `${marker} is no longer an array literal, revisit this test`);
  const literal = src.slice(open, close);
  return new Set((literal.match(/0x[0-9a-fA-F]{40}/g) || []).map((a) => a.toLowerCase()));
}

test("every address the sibling judge calls internal is internal here too", () => {
  const ours = addressesIn(SRC, "SELF_WALLETS");
  const shared = addressesIn(SIBLING, "const SHARED");

  const missing = [...shared].filter((a) => !ours.has(a));
  assert.deepEqual(
    missing, [],
    `these are internal in record-earn.mjs but would be counted as revenue here: ${missing.join(", ")}`,
  );
});

test("the funding address found on 2026-07-12 can never be counted as revenue", () => {
  // Pinned explicitly: this one address accounts for every large "earn" row we have ever recorded.
  // If a future edit drops it, that silently restores a ~$37 phantom revenue claim across the colony.
  const ours = addressesIn(SRC, "SELF_WALLETS");
  assert.ok(
    ours.has("0xf70da97812cb96acdf810712aa562db8dfa3dbef"),
    "0xf70da978… is funding routed through us (EOA holding >$3.1M), not a micro-payment buyer",
  );
});
