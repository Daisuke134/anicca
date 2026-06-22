// VSDD: prove the fix #8 reconciliation produces NO phantom revenue cell.
// On-chain truth (verified 2026-06-22 via name() + balanceOf consensus):
//   telemetry `morpho` field  = Steakhouse Prime USDC vault (0xbeef…, a Morpho MetaMorpho) = 0.971 sh ≈ $1 REAL
//   telemetry `moonwell` field = Moonwell mUSDC (0xEdc817…)                                  = 4 wei dust ≈ $0
// So the PHANTOM cost-basis key was `moonwell` ($1 basis vs $0 on-chain), NOT morpho. The fix drops
// moonwell and KEEPS morpho. The dashboard must then show morpho≈0 (real value − real principal) and
// moonwell HIDDEN — not a fake +$1 / −$1 pair.
import { test } from "node:test";
import assert from "node:assert/strict";
import { revenueBySource } from "../revenue.mjs";

const nw = { liquid: 0.06, aave: 0.196, morpho: 1.00, moonwell: 0.0000000044, fluid: 0.447, beefy: 0, bluechip: 4.6 };
// reconciled cost-basis (fix #8): moonwell dropped (phantom), morpho principal kept (real)
const basis = { aave: 0.196092, morpho: 1.000479, fluid: 0.500048, bluechip: 4.632299 };

test("dropped moonwell does NOT appear as a phantom revenue cell", () => {
  const { bySource } = revenueBySource(nw, basis, {});
  assert.equal(bySource.moonwell, undefined, "moonwell must be hidden (value≈0 & cost=0), not a fake −$1 loss");
});

test("morpho nets to ≈0 (real value − real principal), NOT a phantom +$1 profit", () => {
  const { bySource } = revenueBySource(nw, basis, {});
  assert.ok(Math.abs(bySource.morpho) < 0.01, `morpho P&L should be ~0, got ${bySource.morpho}`);
});

test("regression sentinel: keeping the phantom moonwell $1 basis WOULD show a fake −$1 loss", () => {
  const phantomBasis = { ...basis, moonwell: 1.0 };
  const { bySource } = revenueBySource(nw, phantomBasis, {});
  assert.ok(bySource.moonwell < -0.9, "with phantom basis kept, moonwell shows the fake loss this fix removes");
});

test("regression sentinel: dropping the REAL morpho basis WOULD show a fake +$1 profit", () => {
  const { morpho, ...noMorpho } = basis;
  const { bySource } = revenueBySource(nw, noMorpho, {});
  assert.ok(bySource.morpho > 0.9, "dropping real morpho basis fabricates a +$1 profit — the bug we reverted");
});

test("beefy (0 value, no basis) stays hidden", () => {
  const { bySource } = revenueBySource(nw, basis, {});
  assert.equal(bySource.beefy, undefined);
});

test("realised earnings still surface (x402 sale adds a cell and lifts total by exactly that)", () => {
  const base = revenueBySource(nw, basis, {}).total;
  const { bySource, total } = revenueBySource(nw, basis, { x402: 0.02 });
  assert.equal(bySource.x402, 0.02);
  assert.ok(Math.abs(total - (base + 0.02)) < 1e-6, "an x402 sale must raise total by exactly the sale amount");
});
