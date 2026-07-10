// VCSDD spawn-funding-swap Phase 2a (RED). REQ-003 — checkSourceFunded, the pure exact bigint-vs-bigint
// funding precondition (the live current blocker). Written against lib/pure/funding-check.mjs and
// lib/pure/base-units.mjs / lib/pure/constants.mjs, which do NOT exist yet — every test below MUST fail
// at module-load time (MODULE_NOT_FOUND) until Phase 2b.
import { test } from "node:test";
import assert from "node:assert/strict";
import fc from "fast-check";
import { checkSourceFunded } from "../pure/funding-check.mjs";
import { toBaseUnits } from "../pure/base-units.mjs";
import { MIN_GAS_WEI, USDC_DECIMALS_BASE } from "../pure/constants.mjs";

// PROP-006 — today's REAL balances (Base USDC ~= 0, Base gas ~= 0), a fixed regression fixture.
test("PROP-006: today's real balances (Base USDC=0n, Base gas=0n) fail closed with an explicit deficit — matches production's current real state", () => {
  const requiredBaseUnits = toBaseUnits(15.32, USDC_DECIMALS_BASE);
  assert.equal(checkSourceFunded(0n, 0n, requiredBaseUnits, MIN_GAS_WEI), false);
});

// PROP-005 — nonzero-balance DISCRIMINATING fixture (closes FIND-001/FIND-002's 10^6x wrong-unit gap
// that PROP-006's zero-balance-only fixture cannot catch: 0n is < any positive comparand regardless of
// unit, so a wrong-unit comparison would still coincidentally return false there).
test("PROP-005: nonzero-balance discriminating fixture — baseUsdcBalance=5000000n < requiredBaseUnits=toBaseUnits(15.32,6)=15320000n MUST return false (a wrong-unit impl comparing 5000000n >= 15.32 would wrongly return true)", () => {
  const requiredBaseUnits = toBaseUnits(15.32, USDC_DECIMALS_BASE);
  assert.equal(requiredBaseUnits, 15320000n, "sanity: the fixture's own requiredBaseUnits must be exactly 15320000n");
  const result = checkSourceFunded(5_000_000n, MIN_GAS_WEI * 2n, requiredBaseUnits, MIN_GAS_WEI);
  assert.equal(result, false);
});

// PROP-005 — MIN_GAS_WEI-literal fixture (closes FIND-001: minGasWei must never vacuously default to 0n).
test("PROP-005: MIN_GAS_WEI-literal fixture — baseGasBalance=500_000_000_000_000n (half of MIN_GAS_WEI) with minGasWei=MIN_GAS_WEI=1_000_000_000_000_000n MUST return false (a minGasWei=0n stand-in would wrongly return true)", () => {
  assert.equal(MIN_GAS_WEI, 1_000_000_000_000_000n, "sanity: MIN_GAS_WEI must be exactly the spec-pinned literal");
  const requiredBaseUnits = toBaseUnits(1.0, USDC_DECIMALS_BASE); // trivially satisfiable USDC amount
  const result = checkSourceFunded(requiredBaseUnits * 10n, 500_000_000_000_000n, requiredBaseUnits, MIN_GAS_WEI);
  assert.equal(result, false);
});

test("PROP-005: sufficient balances on both dimensions returns true", () => {
  const requiredBaseUnits = toBaseUnits(15.32, USDC_DECIMALS_BASE);
  const result = checkSourceFunded(requiredBaseUnits, MIN_GAS_WEI, requiredBaseUnits, MIN_GAS_WEI);
  assert.equal(result, true, "balances exactly AT the required thresholds must be treated as sufficient (>=, not >)");
});

test("PROP-005 (property): checkSourceFunded returns false for ANY baseUsdcBalance < requiredBaseUnits, given ample gas", () => {
  fc.assert(
    fc.property(fc.bigInt({ min: 0n, max: 10_000_000_000n }), fc.bigInt({ min: 0n, max: 10_000_000_000n }), (baseUsdcBalance, extra) => {
      const requiredBaseUnits = baseUsdcBalance + extra + 1n; // strictly greater than baseUsdcBalance
      const result = checkSourceFunded(baseUsdcBalance, MIN_GAS_WEI, requiredBaseUnits, MIN_GAS_WEI);
      assert.equal(result, false);
    }),
    { numRuns: 300 }
  );
});

test("PROP-005 (property): checkSourceFunded returns false for ANY baseGasBalance < minGasWei, given ample USDC", () => {
  fc.assert(
    fc.property(fc.bigInt({ min: 0n, max: MIN_GAS_WEI - 1n }), (baseGasBalance) => {
      const requiredBaseUnits = toBaseUnits(1.0, USDC_DECIMALS_BASE);
      const result = checkSourceFunded(requiredBaseUnits * 10n, baseGasBalance, requiredBaseUnits, MIN_GAS_WEI);
      assert.equal(result, false);
    }),
    { numRuns: 300 }
  );
});

test("PROP-005 (property): checkSourceFunded returns true whenever BOTH balances meet or exceed their exact required bigint thresholds", () => {
  fc.assert(
    fc.property(fc.bigInt({ min: 0n, max: 1_000_000_000n }), fc.bigInt({ min: 0n, max: 1_000_000_000_000_000n }), (extraUsdc, extraGas) => {
      const requiredBaseUnits = toBaseUnits(1.0, USDC_DECIMALS_BASE);
      const result = checkSourceFunded(requiredBaseUnits + extraUsdc, MIN_GAS_WEI + extraGas, requiredBaseUnits, MIN_GAS_WEI);
      assert.equal(result, true);
    }),
    { numRuns: 300 }
  );
});
