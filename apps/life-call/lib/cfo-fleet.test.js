"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const { createHmac } = require("node:crypto");
const { types } = require("node:util");
const { adaptFleetDashboard } = require("./cfo-fleet.js");

const OBSERVED_AT = "2026-08-09T12:00:00Z";
const REFERENCE_KEY = "synthetic-fleet-reference-key-32-bytes";
const BASE_ID = "0xAABBCCDDEEFF0011223344556677889900AABBCC";
const INFLOW_WINDOW = "approx_1200000_blocks";
const DASHBOARD = JSON.stringify({
  updated_at: "2026-08-09T11:59:59Z",
  total_net_worth_usd: 999999,
  leaderboard: [{
    id: BASE_ID,
    chain: "base",
    ts: 1786276770,
    host: "private-host",
    geo: "private-geo",
    model_live: "private-model",
    net_worth_usd: 12.5,
    net_worth_src: "chain",
    revenue_mo_usd: 3.25,
    revenue_today_usd: 999,
    earn_src: "chain",
    burn_day_usd: 0.75,
    signature: "must-not-escape",
  }, {
    id: "UNREGISTERED-WALLET",
    chain: "solana",
    ts: 1786276770,
    net_worth_usd: 500,
    net_worth_src: "chain",
    revenue_mo_usd: 500,
    earn_src: "chain",
    burn_day_usd: 500,
  }],
});

function input(overrides = {}) {
  return {
    dashboardJson: DASHBOARD,
    observedAt: OBSERVED_AT,
    referenceKey: REFERENCE_KEY,
    economicScopeRef: "organization:anicca_fleet",
    registeredWallets: [{ walletId: BASE_ID.toLowerCase(), chain: "base" }],
    ...overrides,
  };
}

function assertInvalid(value, reason) {
  assert.throws(() => adaptFleetDashboard(value), (error) => {
    assert.match(error.message, /^fleet_adapter_invalid:[a-z0-9_]+$/);
    assert.doesNotMatch(error.message, /secret|api[_-]?key|private|hostile|AABB|UNREGISTERED/iu);
    if (reason) assert.equal(error.message, `fleet_adapter_invalid:${reason}`);
    return true;
  });
}

function metricUnknown(wallet, field) {
  const value = wallet[field];
  assert.equal(value.status, "unknown");
  assert.equal(value.verificationStatus, "unavailable");
  assert.equal(value.evidenceRef, null);
}

function expectedReference(key, scope, domain, value) {
  const digest = createHmac("sha256", key)
    .update(`${scope}\0${domain}\0${value}`, "utf8")
    .digest("hex")
    .slice(0, 24);
  return `${domain === "account" ? "source_account" : "evidence"}:fleet_${digest}`;
}

function expectedEvidence({ metric, id, chain, telemetryAsOf, sourceStatus, value, window = "" }) {
  const normalizedValue = Object.is(value, -0) ? "0" : JSON.stringify(value);
  const preimage = [metric, id, chain, telemetryAsOf, sourceStatus, normalizedValue, window].join("\0");
  return expectedReference(REFERENCE_KEY, "organization:anicca_fleet", metric, preimage);
}

test("maps only registered rows to the closed Fleet source contract", () => {
  const result = adaptFleetDashboard(input());
  assert.deepEqual(Object.keys(result), [
    "schemaVersion", "sourceId", "economicScopeRef", "readAsOf", "sourceUpdatedAt",
    "coverage", "wallets", "exceptions", "limitations",
  ]);
  assert.equal(result.readAsOf, OBSERVED_AT);
  assert.equal(result.sourceUpdatedAt, "2026-08-09T11:59:59Z");
  assert.deepEqual(result.coverage, { registeredWalletCount: 1, presentWalletCount: 1, partial: true });
  assert.equal(result.wallets.length, 1);
  const wallet = result.wallets[0];
  assert.equal(wallet.chain, "base");
  assert.equal(wallet.telemetryAsOf, "2026-08-09T11:59:30.000Z");
  assert.equal(wallet.telemetryFreshness, "fresh");
  assert.equal(wallet.walletValuation.valueUsd, 12.5);
  assert.equal(wallet.walletValuation.verificationStatus, "upstream_chain_enriched");
  assert.equal(wallet.externalStablecoinInflows.quantity, 3.25);
  assert.equal(wallet.externalStablecoinInflows.unit, "nominal_token_units");
  assert.equal(wallet.externalStablecoinInflows.window, "approx_1200000_blocks");
  assert.equal(wallet.externalStablecoinInflows.verificationStatus, "chain_observed_token_inflow");
  assert.equal(wallet.burnRate.amountUsdPerDay, 0.75);
  assert.equal(wallet.burnRate.verificationStatus, "signed_self_reported");
  assert.equal(result.exceptions.length, 0);
  assert.doesNotMatch(JSON.stringify(result), /999999|private-host|private-geo|private-model|must-not-escape|UNREGISTERED-WALLET|AABBCCDDEEFF/iu);
  assert.equal(Object.isFrozen(result), true);
  assert.equal(Object.isFrozen(wallet), true);
});

test("keeps tenant/domain claim references deterministic and claim-specific", () => {
  const same = adaptFleetDashboard(input());
  const repeated = adaptFleetDashboard(input());
  const otherKey = adaptFleetDashboard(input({ referenceKey: "other-synthetic-fleet-reference-key-32" }));
  assert.equal(same.wallets[0].accountRef, repeated.wallets[0].accountRef);
  assert.equal(same.wallets[0].walletValuation.evidenceRef, repeated.wallets[0].walletValuation.evidenceRef);
  assert.notEqual(same.wallets[0].accountRef, same.wallets[0].walletValuation.evidenceRef);
  assert.notEqual(same.wallets[0].walletValuation.evidenceRef, same.wallets[0].externalStablecoinInflows.evidenceRef);
  assert.notEqual(same.wallets[0].walletValuation.evidenceRef, same.wallets[0].burnRate.evidenceRef);
  assert.notEqual(same.wallets[0].accountRef, otherKey.wallets[0].accountRef);
  assert.notEqual(same.wallets[0].walletValuation.evidenceRef, otherKey.wallets[0].walletValuation.evidenceRef);

  const wallet = same.wallets[0];
  const common = { id: BASE_ID.toLowerCase(), chain: "base", telemetryAsOf: wallet.telemetryAsOf };
  assert.equal(wallet.accountRef, expectedReference(REFERENCE_KEY, "organization:anicca_fleet", "account", `${common.id}\0${common.chain}`));
  assert.equal(wallet.walletValuation.evidenceRef, expectedEvidence({ ...common, metric: "wallet_valuation", sourceStatus: "chain", value: 12.5 }));
  assert.equal(wallet.externalStablecoinInflows.evidenceRef, expectedEvidence({ ...common, metric: "external_inflows", sourceStatus: "chain", value: 3.25, window: INFLOW_WINDOW }));
  assert.equal(wallet.burnRate.evidenceRef, expectedEvidence({ ...common, metric: "burn_rate", sourceStatus: "signed_self_reported", value: 0.75 }));

  const changedMetric = JSON.parse(DASHBOARD);
  changedMetric.leaderboard[0].net_worth_usd = 13.5;
  const changedTelemetry = JSON.parse(DASHBOARD);
  changedTelemetry.leaderboard[0].ts += 1;
  const changedSourceStatus = JSON.parse(DASHBOARD);
  changedSourceStatus.leaderboard[0].net_worth_src = "provider";
  const changedChain = JSON.parse(DASHBOARD);
  changedChain.leaderboard[0].chain = "polygon";
  const claim = (json, field = "walletValuation", overrides = {}) => {
    const adapted = adaptFleetDashboard(input({ dashboardJson: JSON.stringify(json), ...overrides }));
    return adapted.wallets[0]?.[field]?.evidenceRef ?? null;
  };
  assert.notEqual(same.wallets[0].walletValuation.evidenceRef, claim(changedMetric));
  assert.notEqual(same.wallets[0].walletValuation.evidenceRef, claim(changedTelemetry));
  assert.notEqual(same.wallets[0].walletValuation.evidenceRef, claim(changedChain, "walletValuation", { registeredWallets: [{ walletId: BASE_ID, chain: "polygon" }] }));
  const changedSourceResult = adaptFleetDashboard(input({ dashboardJson: JSON.stringify(changedSourceStatus) }));
  metricUnknown(changedSourceResult.wallets[0], "walletValuation");
  assert.deepEqual(changedSourceResult.exceptions, [{ accountRef: wallet.accountRef, field: "wallet_valuation", reason: "unverified_source" }]);
  const sourceStatusVariant = expectedEvidence({ ...common, metric: "wallet_valuation", sourceStatus: "provider", value: 12.5 });
  assert.notEqual(wallet.walletValuation.evidenceRef, sourceStatusVariant);
  const changedWindow = expectedEvidence({ ...common, metric: "external_inflows", sourceStatus: "chain", value: 3.25, window: "different_window" });
  assert.notEqual(wallet.externalStablecoinInflows.evidenceRef, changedWindow);
  assert.match(same.wallets[0].accountRef, /^source_account:fleet_[a-f0-9]{24}$/);
  for (const field of ["walletValuation", "externalStablecoinInflows", "burnRate"]) {
    assert.match(same.wallets[0][field].evidenceRef, /^evidence:fleet_[a-f0-9]{24}$/);
  }
});

test("source gates preserve zero and turn unverified or unsafe metrics into unknown", () => {
  const zero = JSON.parse(DASHBOARD);
  Object.assign(zero.leaderboard[0], { net_worth_usd: 0, revenue_mo_usd: 0, burn_day_usd: 0 });
  const result = adaptFleetDashboard(input({ dashboardJson: JSON.stringify(zero) }));
  assert.equal(result.wallets[0].walletValuation.valueUsd, 0);
  assert.equal(result.wallets[0].externalStablecoinInflows.quantity, 0);
  assert.equal(result.wallets[0].burnRate.amountUsdPerDay, 0);

  const cases = [
    ["net_worth_src", "unverified_source", "wallet_valuation"],
    ["earn_src", "unverified_source", "external_inflows"],
    ["missing_net_worth_usd", "missing_value", "wallet_valuation"],
    ["negative_revenue_mo_usd", "missing_value", "external_inflows"],
    ["nonfinite_burn_day_usd", "missing_value", "burn_rate"],
  ];
  for (const [name, reason, field] of cases) {
    const dashboard = JSON.parse(DASHBOARD);
    if (name === "net_worth_src") dashboard.leaderboard[0].net_worth_src = "signed";
    if (name === "earn_src") dashboard.leaderboard[0].earn_src = "signed";
    if (name === "missing_net_worth_usd") delete dashboard.leaderboard[0].net_worth_usd;
    if (name === "negative_revenue_mo_usd") dashboard.leaderboard[0].revenue_mo_usd = -1;
    const dashboardJson = name === "nonfinite_burn_day_usd"
      ? `{"updated_at":"2026-08-09T11:59:59Z","leaderboard":[{"id":"${BASE_ID}","chain":"base","ts":1786276770,"net_worth_usd":12.5,"net_worth_src":"chain","revenue_mo_usd":3.25,"earn_src":"chain","burn_day_usd":1e400}]}`
      : JSON.stringify(dashboard);
    const adapted = adaptFleetDashboard(input({ dashboardJson }));
    const metric = field === "wallet_valuation" ? "walletValuation" : field === "external_inflows" ? "externalStablecoinInflows" : "burnRate";
    metricUnknown(adapted.wallets[0], metric);
    assert.deepEqual(adapted.exceptions, [{ accountRef: adapted.wallets[0].accountRef, field, reason }]);
  }
});

test("supports Solana case sensitivity and polygon-proxy unknown financial lanes", () => {
  const solanaId = "SolanaWalletCase";
  const dashboard = JSON.parse(DASHBOARD);
  dashboard.leaderboard = [{ id: solanaId, chain: "solana", ts: 1786276770 }];
  const exact = adaptFleetDashboard(input({ dashboardJson: JSON.stringify(dashboard), registeredWallets: [{ walletId: solanaId, chain: "solana" }] }));
  assert.equal(exact.wallets.length, 1);
  assert.equal(exact.wallets[0].chain, "solana");
  const differentCase = adaptFleetDashboard(input({ dashboardJson: JSON.stringify(dashboard), registeredWallets: [{ walletId: solanaId.toLowerCase(), chain: "solana" }] }));
  assert.equal(differentCase.wallets.length, 0);
  assert.equal(differentCase.exceptions[0].reason, "missing_registered_wallet");

  const proxyDashboard = JSON.parse(DASHBOARD);
  proxyDashboard.leaderboard[0].chain = "polygon-proxy";
  delete proxyDashboard.leaderboard[0].net_worth_usd;
  delete proxyDashboard.leaderboard[0].revenue_mo_usd;
  delete proxyDashboard.leaderboard[0].burn_day_usd;
  const proxy = adaptFleetDashboard(input({ dashboardJson: JSON.stringify(proxyDashboard), registeredWallets: [{ walletId: BASE_ID, chain: "polygon-proxy" }] }));
  assert.equal(proxy.wallets.length, 1);
  for (const field of ["walletValuation", "externalStablecoinInflows", "burnRate"]) metricUnknown(proxy.wallets[0], field);
  assert.deepEqual(proxy.exceptions.map(({ field, reason }) => ({ field, reason })), [
    { field: "wallet_valuation", reason: "missing_value" },
    { field: "external_inflows", reason: "missing_value" },
    { field: "burn_rate", reason: "missing_value" },
  ].sort((a, b) => a.field.localeCompare(b.field)));
});

test("classifies cross-family identity matches as chain mismatch and ignores unregistered rows", () => {
  const cases = [
    ["Solana registration observed on EVM", "SolanaWalletCase", "solana", "base"],
    ["EVM registration observed on Solana", BASE_ID, "base", "solana"],
  ];
  for (const [name, walletId, registeredChain, observedChain] of cases) {
    const result = adaptFleetDashboard(input({
      dashboardJson: JSON.stringify({
        updated_at: "2026-08-09T11:59:59Z",
        leaderboard: [
          { id: walletId, chain: observedChain, ts: 1786276770 },
          { id: "UNREGISTERED-CROSS-FAMILY", chain: observedChain },
        ],
      }),
      registeredWallets: [{ walletId, chain: registeredChain }],
    }));
    assert.equal(result.wallets.length, 0, name);
    assert.deepEqual(result.exceptions.map(({ field, reason }) => ({ field, reason })), [{ field: "wallet", reason: "chain_mismatch" }], name);
  }
});

test("emits deterministic coverage exceptions for mismatch or missing registrations", () => {
  for (const [chain, reason] of [["polygon", "chain_mismatch"], ["base", "missing_registered_wallet"]]) {
    const registeredWallets = [{ walletId: BASE_ID.toLowerCase(), chain }];
    const dashboardJson = reason === "missing_registered_wallet" ? JSON.stringify({ updated_at: "2026-08-09T11:59:59Z", leaderboard: [] }) : DASHBOARD;
    const result = adaptFleetDashboard(input({ dashboardJson, registeredWallets }));
    assert.equal(result.wallets.length, 0);
    assert.equal(result.coverage.registeredWalletCount, 1);
    assert.equal(result.coverage.presentWalletCount, 0);
    assert.equal(result.exceptions.length, 1);
    assert.equal(result.exceptions[0].field, "wallet");
    assert.equal(result.exceptions[0].reason, reason);
  }
});

test("accepts only the organizational Fleet scope and keeps chain-aware registrations distinct", () => {
  for (const economicScopeRef of ["person:dais", "organization:other", "human:anicca"]) {
    assertInvalid(input({ economicScopeRef }), "economic_scope");
  }
  const secondId = "0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB";
  const dashboard = { updated_at: "2026-08-09T11:59:59Z", leaderboard: [
    { id: BASE_ID, chain: "base", ts: 1786276770 },
    { id: BASE_ID, chain: "polygon", ts: 1786276770 },
  ] };
  const result = adaptFleetDashboard(input({ dashboardJson: JSON.stringify(dashboard), registeredWallets: [
    { walletId: BASE_ID.toLowerCase(), chain: "base" },
    { walletId: BASE_ID.toLowerCase(), chain: "polygon" },
  ] }));
  assert.equal(result.wallets.length, 2);
  assert.notEqual(result.wallets[0].accountRef, result.wallets[1].accountRef);
  assertInvalid(input({ registeredWallets: [{ walletId: secondId, chain: "base" }, { walletId: secondId.toLowerCase(), chain: "base" }] }), "duplicate_registered_wallet");
});

test("sorts wallets and exceptions by their opaque account references", () => {
  const rows = [
    { id: "0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB", chain: "base", ts: 1786276770, net_worth_usd: 1, net_worth_src: "chain", revenue_mo_usd: 1, earn_src: "chain", burn_day_usd: 1 },
    { id: "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", chain: "base", ts: 1786276770, net_worth_usd: 1, net_worth_src: "chain", revenue_mo_usd: 1, earn_src: "chain", burn_day_usd: 1 },
  ];
  const result = adaptFleetDashboard(input({ dashboardJson: JSON.stringify({ updated_at: "2026-08-09T11:59:59Z", leaderboard: rows }), registeredWallets: rows.map(({ id }) => ({ walletId: id, chain: "base" })) }));
  assert.deepEqual(result.wallets.map(({ accountRef }) => accountRef), [...result.wallets].map(({ accountRef }) => accountRef).sort());
  const absent = adaptFleetDashboard(input({ dashboardJson: JSON.stringify({ updated_at: "2026-08-09T11:59:59Z", leaderboard: [] }), registeredWallets: rows.map(({ id }) => ({ walletId: id, chain: "base" })) }));
  assert.deepEqual(absent.exceptions.map(({ accountRef }) => accountRef), [...absent.exceptions].map(({ accountRef }) => accountRef).sort());
});

test("enforces chronology and freshness boundaries", () => {
  const exactSource = input({ observedAt: "2026-08-09T12:00:04Z", dashboardJson: JSON.stringify({ updated_at: "2026-08-09T12:00:09Z", leaderboard: [{ id: BASE_ID, chain: "base", ts: 1786276770 }] }) });
  const exactSourceResult = adaptFleetDashboard(exactSource);
  assert.equal(exactSourceResult.sourceUpdatedAt, "2026-08-09T12:00:09Z");
  assert.equal(exactSourceResult.wallets.length, 1);
  assertInvalid({ ...input(), observedAt: "2026-08-09T11:59:53Z" }, "source_chronology");
  const telemetryAtSourcePlusFive = JSON.parse(DASHBOARD);
  telemetryAtSourcePlusFive.leaderboard[0].ts = 1786276784;
  const telemetryBoundaryResult = adaptFleetDashboard(input({ dashboardJson: JSON.stringify(telemetryAtSourcePlusFive) }));
  assert.equal(telemetryBoundaryResult.wallets.length, 1);
  assert.equal(telemetryBoundaryResult.wallets[0].telemetryAsOf, "2026-08-09T11:59:44.000Z");
  const telemetryTooFuture = JSON.parse(DASHBOARD);
  telemetryTooFuture.leaderboard[0].ts = 1786276805;
  assertInvalid(input({ dashboardJson: JSON.stringify(telemetryTooFuture) }), "telemetry_chronology");

  const fresh = JSON.parse(DASHBOARD);
  fresh.leaderboard[0].ts = 1786276499;
  const freshResult = adaptFleetDashboard(input({ dashboardJson: JSON.stringify(fresh) }));
  assert.equal(freshResult.wallets[0].telemetryFreshness, "fresh");
  const stale = JSON.parse(DASHBOARD);
  stale.leaderboard[0].ts = 1786276498;
  const staleResult = adaptFleetDashboard(input({ dashboardJson: JSON.stringify(stale) }));
  assert.equal(staleResult.wallets[0].telemetryFreshness, "stale");
});

test("rejects malformed, sparse, duplicated, weak, and unsafe boundaries", () => {
  const invalid = [
    ["malformed JSON", { dashboardJson: "secret-json" }, "invalid_json"],
    ["short key", { referenceKey: "a".repeat(31) }, "weak_reference_key"],
    ["invalid observed timestamp", { observedAt: "not-a-time" }, "invalid_timestamp"],
    ["invalid source timestamp", { dashboardJson: JSON.stringify({ updated_at: "not-a-time", leaderboard: [] }) }, "invalid_timestamp"],
    ["wrong leaderboard type", { dashboardJson: JSON.stringify({ updated_at: "2026-08-09T11:59:59Z", leaderboard: {} }) }, "invalid_leaderboard"],
    ["sparse registry", { registeredWallets: Object.assign(new Array(1), { 1: { walletId: BASE_ID, chain: "base" } }) }, "invalid_array"],
    ["duplicate EVM registry", { registeredWallets: [{ walletId: BASE_ID, chain: "base" }, { walletId: BASE_ID.toLowerCase(), chain: "base" }] }, "duplicate_registered_wallet"],
    ["duplicate Solana registry", { registeredWallets: [{ walletId: "Same", chain: "solana" }, { walletId: "Same", chain: "solana" }] }, "duplicate_registered_wallet"],
  ];
  for (const [name, overrides, reason] of invalid) test(`rejects ${name}`, () => assertInvalid(input(overrides), reason));
});

test("rejects accessors and Proxies before unstable values are inspected", () => {
  const accessor = input();
  let reads = 0;
  Object.defineProperty(accessor, "dashboardJson", { enumerable: true, get() { reads += 1; return DASHBOARD; } });
  assertInvalid(accessor, "accessor_property");
  assert.equal(reads, 0);
  let trapReads = 0;
  const proxy = new Proxy(input(), { get(target, key) { trapReads += 1; if (key === "referenceKey") return "secret-hostile-key"; return Reflect.get(target, key); } });
  assert.ok(types.isProxy(proxy));
  assertInvalid(proxy, "proxy_input");
  assert.equal(trapReads, 0);
  const registryProxy = input({ registeredWallets: new Proxy([{ walletId: BASE_ID, chain: "base" }], {}) });
  assertInvalid(registryProxy, "proxy_input");
});

test("rejects custom prototypes and cycles in public object boundaries", () => {
  const customInput = Object.assign(Object.create({ hostile: true }), input());
  assertInvalid(customInput, "invalid_prototype");

  const customRegistryEntry = Object.assign(Object.create({ hostile: true }), { walletId: BASE_ID, chain: "base" });
  assertInvalid(input({ registeredWallets: [customRegistryEntry] }), "invalid_prototype");

  const cyclicInput = input();
  cyclicInput.self = cyclicInput;
  assertInvalid(cyclicInput, "cycle");

  const cyclicRegistryEntry = { walletId: BASE_ID, chain: "base" };
  cyclicRegistryEntry.self = cyclicRegistryEntry;
  assertInvalid(input({ registeredWallets: [cyclicRegistryEntry] }), "cycle");
});

test("snapshots inputs and ignores unknown dashboard fields", () => {
  const original = JSON.parse(DASHBOARD);
  const value = input({ dashboardJson: JSON.stringify({ ...original, hostile_secret: "secret-value" }) });
  const result = adaptFleetDashboard(value);
  original.leaderboard[0].net_worth_usd = 999;
  value.registeredWallets[0].walletId = "changed";
  assert.equal(result.wallets[0].walletValuation.valueUsd, 12.5);
  assert.doesNotMatch(JSON.stringify(result), /hostile_secret|secret-value|changed/iu);
  assert.throws(() => { result.wallets[0].walletValuation.valueUsd = 9; }, TypeError);
});
