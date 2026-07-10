// VCSDD spawn-funding-swap Phase 2a (RED). REQ-007 — verifySettlement, the pure final on-chain
// settlement check with the TOLERANCE_BPS=50 literal. Written against lib/pure/settlement.mjs and
// lib/pure/constants.mjs, which do NOT exist yet — every test below MUST fail at module-load time
// (MODULE_NOT_FOUND) until Phase 2b.
import { test } from "node:test";
import assert from "node:assert/strict";
import { verifySettlement } from "../pure/settlement.mjs";
import { TOLERANCE_BPS } from "../pure/constants.mjs";

test("sanity: TOLERANCE_BPS is the spec-pinned literal 50 (0.5%)", () => {
  assert.equal(TOLERANCE_BPS, 50);
});

// PROP-013 boundary fixtures (closing FIND-002)
test("PROP-013(a): observed delta EXACTLY at the 0.5% boundary (995_000n of a 1_000_000n quote) MUST pass", () => {
  const quotedAmountOutUakt = 1_000_000n;
  const preBalanceUakt = 0n;
  const postBalanceUakt = 995_000n; // quotedAmountOutUakt * 9950n / 10000n
  assert.equal(verifySettlement(preBalanceUakt, postBalanceUakt, quotedAmountOutUakt, TOLERANCE_BPS), true);
});

test("PROP-013(b): observed delta ONE base unit below the boundary (994_999n) MUST fail closed", () => {
  const quotedAmountOutUakt = 1_000_000n;
  const preBalanceUakt = 0n;
  const postBalanceUakt = 994_999n;
  assert.equal(verifySettlement(preBalanceUakt, postBalanceUakt, quotedAmountOutUakt, TOLERANCE_BPS), false);
});

test("PROP-013: zero-delta fixture (legs report success but destination balance is unchanged) fails closed — the non-discriminating baseline case", () => {
  const preBalanceUakt = 5_000_000n;
  assert.equal(verifySettlement(preBalanceUakt, preBalanceUakt, 1_000_000n, TOLERANCE_BPS), false);
});

test("PROP-013: a delta that exactly matches the quoted amount_out (zero slippage) always passes", () => {
  const preBalanceUakt = 0n;
  const quotedAmountOutUakt = 1_000_000n;
  assert.equal(verifySettlement(preBalanceUakt, quotedAmountOutUakt, quotedAmountOutUakt, TOLERANCE_BPS), true);
});

test("PROP-013: a delta materially worse than the quoted amount_out (beyond tolerance) fails closed", () => {
  const preBalanceUakt = 0n;
  const quotedAmountOutUakt = 1_000_000n;
  assert.equal(verifySettlement(preBalanceUakt, 500_000n, quotedAmountOutUakt, TOLERANCE_BPS), false);
});

test("a WRONG (looser) toleranceBps passed directly to the pure function changes the boundary outcome — proving the function is not hardcoding its own tolerance internally", () => {
  const quotedAmountOutUakt = 1_000_000n;
  // 994_999n fails at TOLERANCE_BPS=50 (above), but passes at a looser 100 bps (1%) tolerance —
  // demonstrating verifySettlement genuinely uses its toleranceBps PARAMETER, not a baked-in constant.
  assert.equal(verifySettlement(0n, 994_999n, quotedAmountOutUakt, 100), true);
});
