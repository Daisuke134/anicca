"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const { types } = require("node:util");
const { validateFleetSourceResult } = require("./cfo-fleet-source.js");

const LIMITATIONS = [
  "asset_positions_unavailable",
  "valuation_quote_provenance_unavailable",
  "inflows_not_recognized_revenue",
  "inflow_window_approximate",
  "burn_estimated",
  "economic_owner_mapping_unavailable",
];

function validResult() {
  return {
    schemaVersion: 1,
    sourceId: "fleet_dashboard",
    economicScopeRef: "organization:anicca_fleet",
    readAsOf: "2026-08-09T12:00:00Z",
    sourceUpdatedAt: "2026-08-09T11:59:59Z",
    coverage: { registeredWalletCount: 1, presentWalletCount: 1, partial: true },
    wallets: [{
      accountRef: "source_account:fleet_aaaaaaaaaaaaaaaaaaaaaaaa",
      chain: "base",
      telemetryAsOf: "2026-08-09T11:59:30Z",
      telemetryFreshness: "fresh",
      walletValuation: {
        status: "available", asset: "fleet_wallet_aggregate", quantity: null,
        currency: "USD", valueUsd: 12.5, verificationStatus: "upstream_chain_enriched",
        evidenceRef: "evidence:fleet_bbbbbbbbbbbbbbbbbbbbbbbb",
      },
      externalStablecoinInflows: {
        status: "available", asset: "external_stablecoin_transfer_aggregate", quantity: 3.25,
        unit: "nominal_token_units", currency: null, window: "approx_1200000_blocks",
        verificationStatus: "chain_observed_token_inflow", evidenceRef: "evidence:fleet_cccccccccccccccccccccccc",
      },
      burnRate: {
        status: "available", amountUsdPerDay: 0.75, currency: "USD",
        verificationStatus: "signed_self_reported",
        evidenceRef: "evidence:fleet_dddddddddddddddddddddddd",
      },
    }],
    exceptions: [],
    limitations: [...LIMITATIONS],
  };
}

function assertInvalid(value, reason) {
  assert.throws(() => validateFleetSourceResult(value), (error) => {
    assert.equal(error.name, "Error");
    assert.match(error.message, /^fleet_source_invalid:[a-z0-9_]+$/);
    if (reason) assert.equal(error.message, `fleet_source_invalid:${reason}`);
    return true;
  });
}

function assertInvalidMutation(mutate, reason) {
  const value = validResult();
  mutate(value);
  assertInvalid(value, reason);
}

function unknown(metric, accountRef = validResult().wallets[0].accountRef) {
  const value = validResult();
  const wallet = value.wallets[0];
  if (metric === "wallet_valuation") {
    wallet.walletValuation = {
      status: "unknown", asset: "fleet_wallet_aggregate", quantity: null, currency: "USD",
      valueUsd: null, verificationStatus: "unavailable", evidenceRef: null,
    };
  } else if (metric === "external_inflows") {
    wallet.externalStablecoinInflows = {
      status: "unknown", asset: "external_stablecoin_transfer_aggregate", quantity: null,
      unit: "nominal_token_units", currency: null, window: "approx_1200000_blocks",
      verificationStatus: "unavailable", evidenceRef: null,
    };
  } else {
    wallet.burnRate = {
      status: "unknown", amountUsdPerDay: null, currency: "USD",
      verificationStatus: "unavailable", evidenceRef: null,
    };
  }
  value.wallets[0].accountRef = accountRef;
  value.exceptions = [{ accountRef, field: metric, reason: "missing_value" }];
  return value;
}

test("valid Fleet result has the closed schema and exact constants", () => {
  const input = validResult();
  const output = validateFleetSourceResult(input);
  assert.notEqual(output, input);
  assert.deepEqual(Object.keys(output), [
    "schemaVersion", "sourceId", "economicScopeRef", "readAsOf", "sourceUpdatedAt",
    "coverage", "wallets", "exceptions", "limitations",
  ]);
  assert.deepEqual(Object.keys(output.coverage), ["registeredWalletCount", "presentWalletCount", "partial"]);
  assert.deepEqual(Object.keys(output.wallets[0]), [
    "accountRef", "chain", "telemetryAsOf", "telemetryFreshness", "walletValuation",
    "externalStablecoinInflows", "burnRate",
  ]);
  assert.deepEqual(Object.keys(output.wallets[0].walletValuation), [
    "status", "asset", "quantity", "currency", "valueUsd", "verificationStatus", "evidenceRef",
  ]);
  assert.deepEqual(Object.keys(output.wallets[0].externalStablecoinInflows), [
    "status", "asset", "quantity", "unit", "currency", "window", "verificationStatus", "evidenceRef",
  ]);
  assert.deepEqual(Object.keys(output.wallets[0].burnRate), [
    "status", "amountUsdPerDay", "currency", "verificationStatus", "evidenceRef",
  ]);
  assert.deepEqual(Object.keys(output.exceptions), []);
  assert.deepEqual(output.limitations, LIMITATIONS);
  assert.equal(output.economicScopeRef, "organization:anicca_fleet");
  assert.equal(output.coverage.partial, true);
  assert.equal(output.wallets[0].walletValuation.valueUsd, 12.5);
  assert.equal(output.wallets[0].externalStablecoinInflows.quantity, 3.25);
  assert.equal(output.wallets[0].burnRate.amountUsdPerDay, 0.75);
});

test("available zero is valid and every unknown metric is paired with one exception", () => {
  const zero = validResult();
  zero.wallets[0].walletValuation.valueUsd = 0;
  zero.wallets[0].externalStablecoinInflows.quantity = 0;
  zero.wallets[0].burnRate.amountUsdPerDay = 0;
  assert.doesNotThrow(() => validateFleetSourceResult(zero));

  for (const field of ["wallet_valuation", "external_inflows", "burn_rate"]) {
    const result = validateFleetSourceResult(unknown(field));
    const metric = field === "wallet_valuation" ? result.wallets[0].walletValuation
      : field === "external_inflows" ? result.wallets[0].externalStablecoinInflows : result.wallets[0].burnRate;
    assert.equal(metric.status, "unknown");
    assert.equal(metric.verificationStatus, "unavailable");
    assert.equal(metric.evidenceRef, null);
  }
});

test("missing registered wallets are counted and kept separate from emitted wallets", () => {
  const value = validResult();
  value.coverage.registeredWalletCount = 2;
  value.exceptions = [{
    accountRef: "source_account:fleet_eeeeeeeeeeeeeeeeeeeeeeee",
    field: "wallet",
    reason: "missing_registered_wallet",
  }];
  assert.doesNotThrow(() => validateFleetSourceResult(value));

  const duplicate = structuredClone(value);
  duplicate.exceptions.push(structuredClone(duplicate.exceptions[0]));
  assertInvalid(duplicate);
  const emitted = structuredClone(value);
  emitted.exceptions[0].accountRef = emitted.wallets[0].accountRef;
  assertInvalid(emitted);
});

test("invalid available/unknown pairs fail closed", () => {
  const cases = [
    ["available_without_value", (value) => { value.wallets[0].walletValuation.valueUsd = null; }],
    ["unknown_with_value", (value) => {
      value.wallets[0].walletValuation.status = "unknown";
      value.wallets[0].walletValuation.verificationStatus = "unavailable";
    }],
    ["unknown_with_evidence", (value) => {
      value.wallets[0].burnRate.status = "unknown";
      value.wallets[0].burnRate.amountUsdPerDay = null;
      value.wallets[0].burnRate.verificationStatus = "unavailable";
    }],
    ["negative_amount", (value) => { value.wallets[0].externalStablecoinInflows.quantity = -1; }],
    ["nan_amount", (value) => { value.wallets[0].externalStablecoinInflows.quantity = Number.NaN; }],
    ["infinite_amount", (value) => { value.wallets[0].externalStablecoinInflows.quantity = Number.POSITIVE_INFINITY; }],
    ["negative_infinite_amount", (value) => { value.wallets[0].externalStablecoinInflows.quantity = Number.NEGATIVE_INFINITY; }],
    ["wrong_window", (value) => { value.wallets[0].externalStablecoinInflows.window = "month"; }],
    ["complete_claim", (value) => { value.coverage.partial = false; }],
    ["count_mismatch", (value) => { value.coverage.presentWalletCount = 0; }],
  ];
  for (const [name, mutate] of cases) {
    assertInvalidMutation(mutate, name === "complete_claim" ? "coverage" : undefined);
  }
});

test("metric exceptions are exact, unique, and cannot be attached to available values", () => {
  const missing = unknown("wallet_valuation");
  missing.exceptions = [];
  assertInvalid(missing);

  const extra = validResult();
  extra.exceptions = [{ accountRef: extra.wallets[0].accountRef, field: "burn_rate", reason: "missing_value" }];
  assertInvalid(extra);

  const duplicate = unknown("burn_rate");
  duplicate.exceptions.push(structuredClone(duplicate.exceptions[0]));
  assertInvalid(duplicate);

  const wrongField = unknown("burn_rate");
  wrongField.exceptions[0].field = "external_inflows";
  assertInvalid(wrongField);

  const wrongReason = unknown("burn_rate");
  wrongReason.exceptions[0].reason = "missing_registered_wallet";
  assertInvalid(wrongReason);
});

test("root, metric, exception, and reference enums are closed", () => {
  const mutations = [
    (value) => { value.schemaVersion = 2; },
    (value) => { value.sourceId = "other_source"; },
    (value) => { value.economicScopeRef = "person:dais"; },
    (value) => { value.coverage.registeredWalletCount = -1; },
    (value) => { value.coverage.presentWalletCount = 1.5; },
    (value) => { value.wallets[0].chain = "ethereum"; },
    (value) => { value.wallets[0].walletValuation.asset = "other"; },
    (value) => { value.wallets[0].externalStablecoinInflows.unit = "USD"; },
    (value) => { value.wallets[0].burnRate.currency = "JPY"; },
    (value) => { value.wallets[0].burnRate.verificationStatus = "estimated"; },
    (value) => { value.wallets[0].accountRef = "source_account:fleet_NOT_HEX"; },
    (value) => { value.wallets[0].walletValuation.evidenceRef = "evidence:fleet_bad"; },
    (value) => {
      value.coverage.registeredWalletCount = 2;
      value.exceptions = [{ accountRef: "source_account:fleet_eeeeeeeeeeeeeeeeeeeeeeee", field: "wallet", reason: "unverified_source" }];
    },
    (value) => {
      value.coverage.registeredWalletCount = 2;
      value.coverage.presentWalletCount = 2;
      value.wallets.push(structuredClone(value.wallets[0]));
    },
  ];
  for (const mutate of mutations) {
    const value = structuredClone(validResult());
    mutate(value);
    assertInvalid(value);
  }
  const chainMismatch = validResult();
  chainMismatch.coverage.registeredWalletCount = 2;
  chainMismatch.exceptions = [{
    accountRef: "source_account:fleet_eeeeeeeeeeeeeeeeeeeeeeee",
    field: "wallet",
    reason: "chain_mismatch",
  }];
  assert.doesNotThrow(() => validateFleetSourceResult(chainMismatch));
});

test("unknown keys, symbols, and non-dense arrays are rejected", () => {
  const cases = [
    (value) => { value.extra = "unexpected"; },
    (value) => { value.coverage.extra = true; },
    (value) => { value.wallets[0].walletValuation.extra = true; },
    (value) => { value.exceptions = [{ accountRef: value.wallets[0].accountRef, field: "wallet_valuation", reason: "missing_value", extra: true }]; value.wallets[0].walletValuation.status = "unknown"; value.wallets[0].walletValuation.valueUsd = null; value.wallets[0].walletValuation.verificationStatus = "unavailable"; value.wallets[0].walletValuation.evidenceRef = null; },
    (value) => { value[Symbol("secret")] = "secret-shaped"; },
    (value) => { delete value.wallets[0]; },
    (value) => { value.wallets.push(); value.wallets.length = 2; },
  ];
  for (const mutate of cases) {
    assertInvalidMutation(mutate);
  }
});

test("RFC3339 calendar and chronology boundaries are validated", () => {
  const invalid = [
    (value) => { value.readAsOf = "2026-02-29T12:00:00Z"; },
    (value) => { value.readAsOf = "2026-01-01T12:00:00"; },
    (value) => { value.readAsOf = "2026-01-01T12:00:00+24:00"; },
    (value) => { value.sourceUpdatedAt = "2026-08-09T12:00:05.001Z"; },
    (value) => { value.wallets[0].telemetryAsOf = "2026-08-09T12:00:04.001Z"; },
  ];
  for (const mutate of invalid) assertInvalidMutation(mutate);

  const sourceBoundary = validResult();
  sourceBoundary.sourceUpdatedAt = "2026-08-09T12:00:05Z";
  sourceBoundary.wallets[0].telemetryAsOf = "2026-08-09T12:00:05Z";
  assert.doesNotThrow(() => validateFleetSourceResult(sourceBoundary));

  const telemetryBoundary = validResult();
  telemetryBoundary.sourceUpdatedAt = "2026-08-09T12:00:00Z";
  telemetryBoundary.wallets[0].telemetryAsOf = "2026-08-09T11:55:00Z";
  assert.equal(validateFleetSourceResult(telemetryBoundary).wallets[0].telemetryFreshness, "fresh");

  const stale = structuredClone(telemetryBoundary);
  stale.wallets[0].telemetryAsOf = "2026-08-09T11:54:59.999Z";
  stale.wallets[0].telemetryFreshness = "stale";
  assert.equal(validateFleetSourceResult(stale).wallets[0].telemetryFreshness, "stale");

  const mismatch = structuredClone(telemetryBoundary);
  mismatch.wallets[0].telemetryFreshness = "stale";
  assertInvalid(mismatch);
  const future = structuredClone(telemetryBoundary);
  future.wallets[0].telemetryAsOf = "2026-08-09T12:00:05Z";
  assert.doesNotThrow(() => validateFleetSourceResult(future));
});

test("snapshot rejects accessors, proxies, custom prototypes, functions, and cycles", () => {
  const accessor = validResult();
  let reads = 0;
  Object.defineProperty(accessor, "sourceId", { enumerable: true, get() { reads += 1; return "fleet_dashboard"; } });
  assertInvalid(accessor);
  assert.equal(reads, 0);

  const changingProxy = new Proxy(validResult(), {
    get(target, key) {
      if (key === "sourceId") return "secret-shaped-proxy-value";
      return Reflect.get(target, key);
    },
  });
  assert.ok(types.isProxy(changingProxy));
  assertInvalid(changingProxy);

  const customPrototype = validResult();
  Object.setPrototypeOf(customPrototype, { hidden: true });
  assertInvalid(customPrototype);
  const nestedPrototype = validResult();
  Object.setPrototypeOf(nestedPrototype.wallets[0], { hidden: true });
  assertInvalid(nestedPrototype);

  const functionValue = validResult();
  functionValue.wallets[0].burnRate.amountUsdPerDay = () => 0;
  assertInvalid(functionValue);
  const cycle = validResult();
  cycle.coverage.cycle = cycle;
  assertInvalid(cycle);
});

test("result is isolated from input mutation and recursively frozen", () => {
  const input = validResult();
  const output = validateFleetSourceResult(input);
  assert.equal(Object.isFrozen(output), true);
  assert.equal(Object.isFrozen(output.coverage), true);
  assert.equal(Object.isFrozen(output.wallets), true);
  assert.equal(Object.isFrozen(output.wallets[0]), true);
  assert.equal(Object.isFrozen(output.wallets[0].walletValuation), true);
  assert.equal(Object.isFrozen(output.wallets[0].externalStablecoinInflows), true);
  assert.equal(Object.isFrozen(output.wallets[0].burnRate), true);
  assert.equal(Object.isFrozen(output.exceptions), true);
  assert.equal(Object.isFrozen(output.limitations), true);
  input.wallets[0].walletValuation.valueUsd = 999;
  input.limitations[0] = "changed";
  assert.equal(output.wallets[0].walletValuation.valueUsd, 12.5);
  assert.equal(output.limitations[0], LIMITATIONS[0]);
  assert.throws(() => { output.wallets[0].burnRate.amountUsdPerDay = 9; }, TypeError);
});

test("invalid secret-shaped strings produce only a fixed privacy-safe reason", () => {
  const value = validResult();
  value.economicScopeRef = "api_key=super-secret-value";
  assert.throws(() => validateFleetSourceResult(value), (error) => {
    assert.equal(error.message, "fleet_source_invalid:economic_scope");
    assert.doesNotMatch(error.message, /super-secret-value|api_key/);
    return true;
  });
});
