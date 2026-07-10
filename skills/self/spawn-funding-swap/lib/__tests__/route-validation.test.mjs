// VCSDD spawn-funding-swap Phase 2a (RED). REQ-002 — validateRoute, the pure predicate gating every
// signing code path. Written against lib/pure/route-validation.mjs, which does NOT exist yet — every
// test below MUST fail at module-load time (MODULE_NOT_FOUND) until Phase 2b.
import { test } from "node:test";
import assert from "node:assert/strict";
import { validateRoute } from "../pure/route-validation.mjs";
import { validRouteFixture } from "./fakes/fake-clients.mjs";

// PROP-003
test("PROP-003: validateRoute accepts the live-confirmed shape (Base USDC -> AKT, txs_required=2)", () => {
  const result = validateRoute(validRouteFixture({ amountOutUakt: 24_650_000n }));
  assert.equal(result.ok, true);
});

test("PROP-003: validateRoute rejects an empty body", () => {
  assert.equal(validateRoute({}).ok, false);
  assert.equal(validateRoute(null).ok, false);
  assert.equal(validateRoute(undefined).ok, false);
});

test("PROP-003: validateRoute rejects wrong dest_asset_denom (defends against an intermediary hop swap-out to the wrong asset)", () => {
  const bad = { ...validRouteFixture(), dest_asset_denom: "uosmo" };
  assert.equal(validateRoute(bad).ok, false);
});

test("PROP-003: validateRoute rejects wrong dest_asset_chain_id", () => {
  const bad = { ...validRouteFixture(), dest_asset_chain_id: "osmosis-1" };
  assert.equal(validateRoute(bad).ok, false);
});

test("PROP-003: validateRoute rejects amount_out missing, zero, negative, or NaN after parse", () => {
  for (const badAmountOut of [undefined, "0", "0.0", "-5", "not-a-number"]) {
    const bad = { ...validRouteFixture() };
    if (badAmountOut === undefined) delete bad.amount_out;
    else bad.amount_out = badAmountOut;
    assert.equal(validateRoute(bad).ok, false, `amount_out=${badAmountOut} must be rejected`);
  }
});

test("PROP-003: validateRoute rejects a route with missing txs_required (unsupported/unspecified execution shape)", () => {
  const bad = { ...validRouteFixture() };
  delete bad.txs_required;
  assert.equal(validateRoute(bad).ok, false);
});

test("PROP-003: a valid route's amountOutUakt/txsRequired surface on the result for downstream consumers (planNextLeg/verifySettlement)", () => {
  const result = validateRoute(validRouteFixture({ amountOutUakt: 24_650_000n }));
  assert.equal(result.ok, true);
  assert.equal(result.amountOutUakt, 24_650_000n);
  assert.equal(result.txsRequired, 2);
});
