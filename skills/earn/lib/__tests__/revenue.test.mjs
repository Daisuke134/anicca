// VSDD: per-source revenue must show value − basis, hide unused venues, and NEVER show a cost-basis key
// that has no on-chain position as a phantom loss. (deposit-guard.mjs is what stops such a basis from
// being recorded in the first place; this test pins the revenue math that consumes it.)
//
// On-chain truth (verified 2026-06-22 via decimals()+balanceOf consensus — see cost-basis-onchain-proof.json):
//   morpho   = Steakhouse Prime (0xbeef…, ERC4626 18-dec) = 0.971 sh  ≈ $1 REAL
//   moonwell = Moonwell mUSDC    (0xEdc817…, cToken 8-dec) = 43.66 mUSDC ≈ $1 REAL  (NOT dust — that was a units bug)
//   beefy    = 0 (empty, and has no cost-basis key)
// So NO morpho/moonwell key is phantom; both are kept. The original "phantom" was a decimals misread.
import { test } from "node:test";
import assert from "node:assert/strict";
import { revenueBySource } from "../revenue.mjs";

const nw = { liquid: 0.06, aave: 0.196, morpho: 1.00, moonwell: 1.00, fluid: 0.447, beefy: 0, bluechip: 4.6 };
const basis = { aave: 0.196092, moonwell: 1.000439, morpho: 1.000479, fluid: 0.500048, bluechip: 4.632299 };

test("both real lending positions (morpho & moonwell) net to ≈0 (value − principal), not a phantom ±$1", () => {
  const { bySource } = revenueBySource(nw, basis, {});
  assert.ok(Math.abs(bySource.morpho) < 0.01, `morpho P&L ~0, got ${bySource.morpho}`);
  assert.ok(Math.abs(bySource.moonwell) < 0.01, `moonwell P&L ~0, got ${bySource.moonwell}`);
});

test("beefy (0 on-chain value AND no basis key) stays hidden", () => {
  const { bySource } = revenueBySource(nw, basis, {});
  assert.equal(bySource.beefy, undefined);
});

test("PHANTOM sentinel: a basis key with NO on-chain position shows a fake loss (the thing deposit-guard prevents)", () => {
  // simulate a phantom: cost-basis records beefy $1 but on-chain beefy value is 0
  const phantomBasis = { ...basis, beefy: 1.0 };
  const { bySource } = revenueBySource(nw, phantomBasis, {});
  assert.ok(bySource.beefy < -0.9, "a recorded-but-not-landed deposit fabricates a −$1 loss — why we gate on depositLanded");
});

test("realised earnings surface and lift total by exactly the sale amount", () => {
  const base = revenueBySource(nw, basis, {}).total;
  const { bySource, total } = revenueBySource(nw, basis, { x402: 0.02 });
  assert.equal(bySource.x402, 0.02);
  assert.ok(Math.abs(total - (base + 0.02)) < 1e-6);
});
