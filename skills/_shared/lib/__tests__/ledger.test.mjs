// node:test — hl-realized-pnl additions to the shared ledger module: deriveLine's new
// `fill_tid` passthrough (REQ-C2) and isProfitable's new Hyperliquid disjunct (REQ-C3).
// Kept in a SEPARATE new file (verification-architecture.md lists this exact path as NEW) so
// the pre-existing ledger.test.js (EVM/Solana coverage) is left completely untouched — this
// file is purely additive, mirroring the non-regression discipline REQ-C3/PROP-014e require.
//
// Covers verification-architecture.md PROP-013, PROP-014a, PROP-014b, PROP-014c, PROP-014d,
// PROP-014e.
import { test } from "node:test";
import assert from "node:assert/strict";
import { deriveLine, isProfitable } from "../ledger.mjs";

// --- PROP-013 (REQ-C2): deriveLine passes fill_tid through unchanged when present, and adds
//     no fill_tid key at all when absent (not merely `undefined`) ---

test("deriveLine passes fill_tid through unchanged when present", () => {
  const l = deriveLine({
    wallet: "0xMyWallet", source: "hl-trade", task: "hl-close ETH tid=999",
    earn_usdc: 1, cost_usdc: 0, wake: "w1", fill_tid: 999,
  });
  assert.equal(l.fill_tid, 999);
});

test("deriveLine omits fill_tid entirely (not just undefined) when absent from input", () => {
  const l = deriveLine({
    wallet: "0xMyWallet", source: "x402", task: "t", earn_usdc: 1, cost_usdc: 0, wake: "w1",
  });
  assert.equal("fill_tid" in l, false, "fill_tid must be ABSENT as a key, not present-but-undefined");
});

// --- PROP-014a (REQ-C3): a well-formed Hyperliquid WIN line is profitable ---

test("isProfitable: well-formed Hyperliquid win (chain+fill_tid+confirmed+external+net>0)", () => {
  assert.equal(
    isProfitable({
      source: "hl-trade", chain: "hyperliquid", fill_tid: 1, confirmed: true,
      external: true, net_usdc: 1.5,
    }),
    true
  );
});

// --- PROP-014b (REQ-C3): a well-formed Hyperliquid LOSS line is still rejected (gate 1 unchanged) ---

test("isProfitable: Hyperliquid loss (net_usdc<=0) is rejected even though it's a real settled fill", () => {
  assert.equal(
    isProfitable({
      source: "hl-trade", chain: "hyperliquid", fill_tid: 2, confirmed: true,
      external: true, net_usdc: -0.5,
    }),
    false
  );
});

// --- PROP-014c (REQ-C3): missing/false external is rejected — not bypassed for Hyperliquid ---

test("isProfitable: Hyperliquid line missing external is rejected (external omitted)", () => {
  assert.equal(
    isProfitable({
      source: "hl-trade", chain: "hyperliquid", fill_tid: 3, confirmed: true, net_usdc: 1.0,
    }),
    false
  );
});

test("isProfitable: Hyperliquid line with external:false is rejected", () => {
  assert.equal(
    isProfitable({
      source: "hl-trade", chain: "hyperliquid", fill_tid: 3, confirmed: true,
      external: false, net_usdc: 1.0,
    }),
    false
  );
});

// --- PROP-014d (REQ-C3): malformed Hyperliquid shape never accidentally satisfies the EVM or
//     Solana disjunct (missing fill_tid; confirmed:false) ---

test("isProfitable: chain=hyperliquid but fill_tid missing is rejected", () => {
  assert.equal(
    isProfitable({
      source: "hl-trade", chain: "hyperliquid", confirmed: true, external: true, net_usdc: 1.0,
    }),
    false
  );
});

test("isProfitable: chain=hyperliquid, fill_tid present, but confirmed:false is rejected", () => {
  assert.equal(
    isProfitable({
      source: "hl-trade", chain: "hyperliquid", fill_tid: 4, confirmed: false,
      external: true, net_usdc: 1.0,
    }),
    false
  );
});

// --- PROP-014e (non-regression): pre-existing EVM/Solana/narrate/swap fixtures are unchanged ---

test("isProfitable: non-regression — real EVM row (tx+status 0x1) still true", () => {
  assert.equal(
    isProfitable({ source: "0xwork", net_usdc: 0.1, status: "0x1", tx: "0x1", external: true }),
    true
  );
});

test("isProfitable: non-regression — real Solana row (sig+confirmed) still true", () => {
  assert.equal(
    isProfitable({ source: "promote.fun", net_usdc: 0.5, sig: "sigA", confirmed: true, external: true }),
    true
  );
});

test("isProfitable: non-regression — narrate-only row (no tx/sig/hl fields) still false", () => {
  assert.equal(isProfitable({ net_usdc: 0.1 }), false);
});

test("isProfitable: non-regression — swap row (asset rotation) still false even with net>0", () => {
  assert.equal(
    isProfitable({ source: "swap-eth-usdc", net_usdc: 0.1, status: "0x1", tx: "0x1", external: true }),
    false
  );
});
