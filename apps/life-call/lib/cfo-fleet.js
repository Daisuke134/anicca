"use strict";
const { createHmac } = require("node:crypto");
const { types } = require("node:util");
const { validateFleetSourceResult } = require("./cfo-fleet-source");
const ERROR_PREFIX = "fleet_adapter_invalid:", SCOPE = "organization:anicca_fleet";
const CHAINS = new Set(["base", "polygon", "polygon-proxy", "solana"]);
const INPUT_KEYS = new Set(["dashboardJson", "observedAt", "referenceKey", "economicScopeRef", "registeredWallets"]);
const REGISTRY_KEYS = new Set(["walletId", "chain"]);
const RFC3339 = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?(Z|[+-]\d{2}:\d{2})$/;
const LIMITATIONS = ["asset_positions_unavailable", "valuation_quote_provenance_unavailable", "inflows_not_recognized_revenue", "inflow_window_approximate", "burn_estimated", "economic_owner_mapping_unavailable"];
const WINDOW = "approx_1200000_blocks";
class AdapterError extends Error {}
function fail(reason) { throw new AdapterError(`${ERROR_PREFIX}${reason}`); }
function hasValue(descriptor) { return descriptor && Object.prototype.hasOwnProperty.call(descriptor, "value"); }
function snapshot(value, active = new WeakSet()) {
  if (value === null || typeof value === "string" || typeof value === "boolean" || typeof value === "number") return value;
  if (typeof value !== "object") fail("invalid_input");
  if (types.isProxy(value)) fail("proxy_input");
  const array = Array.isArray(value);
  let prototype;
  try { prototype = Object.getPrototypeOf(value); } catch { fail("invalid_input"); }
  if (prototype !== (array ? Array.prototype : Object.prototype)) fail("invalid_prototype");
  if (active.has(value)) fail("cycle");
  active.add(value);
  try {
    const ownKeys = Reflect.ownKeys(value);
    if (array) {
      const lengthDescriptor = Object.getOwnPropertyDescriptor(value, "length"), length = lengthDescriptor && lengthDescriptor.value;
      if (!hasValue(lengthDescriptor) || lengthDescriptor.enumerable || !Number.isSafeInteger(length) || length < 0 || length >= 4294967295 || ownKeys.length !== length + 1) fail("invalid_array");
      const clone = new Array(length);
      for (const key of ownKeys) {
        if (key === "length") continue;
        if (typeof key !== "string" || !/^(0|[1-9]\d*)$/.test(key) || Number(key) >= length) fail("invalid_array");
        const descriptor = Object.getOwnPropertyDescriptor(value, key);
        if (!hasValue(descriptor) || !descriptor.enumerable) fail(hasValue(descriptor) ? "invalid_array" : "accessor_property");
        Object.defineProperty(clone, key, { value: snapshot(descriptor.value, active), enumerable: true, writable: true, configurable: true });
      }
      return clone;
    }
    const clone = {};
    for (const key of ownKeys) {
      if (typeof key !== "string") fail("symbol_key");
      const descriptor = Object.getOwnPropertyDescriptor(value, key);
      if (!hasValue(descriptor)) fail("accessor_property");
      if (!descriptor.enumerable) fail("invalid_keys");
      Object.defineProperty(clone, key, { value: snapshot(descriptor.value, active), enumerable: true, writable: true, configurable: true });
    }
    return clone;
  } finally { active.delete(value); }
}
function exactKeys(value, allowed, reason = "invalid_input") {
  if (value === null || typeof value !== "object" || Array.isArray(value) || Object.getPrototypeOf(value) !== Object.prototype) fail(reason);
  const keys = Reflect.ownKeys(value); if (keys.length !== allowed.size || keys.some((key) => typeof key !== "string" || !allowed.has(key) || !Object.prototype.propertyIsEnumerable.call(value, key))) fail(reason);
}
function timestamp(value) {
  const match = typeof value === "string" && RFC3339.exec(value);
  if (!match) fail("invalid_timestamp");
  const year = Number(match[1]), month = Number(match[2]), day = Number(match[3]), hour = Number(match[4]), minute = Number(match[5]), second = Number(match[6]);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0), days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (month < 1 || month > 12 || day < 1 || day > days[month - 1] || hour > 23 || minute > 59 || second > 59) fail("invalid_timestamp");
  const zone = match[8], zoneHour = zone === "Z" ? 0 : Number(zone.slice(1, 3)), zoneMinute = zone === "Z" ? 0 : Number(zone.slice(4));
  if (zoneHour > 23 || zoneMinute > 59) fail("invalid_timestamp");
  const local = new Date(0); local.setUTCFullYear(year, month - 1, day); local.setUTCHours(hour, minute, second, 0); const fraction = match[7] ? Number(`0${match[7]}`) * 1000 : 0;
  if (!Number.isFinite(fraction)) fail("invalid_timestamp");
  return local.getTime() - (zone === "Z" ? 0 : (zone[0] === "+" ? 1 : -1) * (zoneHour * 60 + zoneMinute) * 60000) + fraction;
}
function ref(referenceKey, economicScopeRef, domain, value) {
  const digest = createHmac("sha256", referenceKey).update(`${economicScopeRef}\0${domain}\0${value}`, "utf8").digest("hex").slice(0, 24); return `${domain === "account" ? "source_account" : "evidence"}:fleet_${digest}`;
}
function normalizeIdentity(walletId, chain) { return chain === "solana" ? walletId : walletId.toLowerCase(); }
function claimPreimage(metric, id, chain, telemetryAsOf, sourceStatus, value, window = "") { return [metric, id, chain, telemetryAsOf, sourceStatus, Object.is(value, -0) ? "0" : JSON.stringify(value), window].join("\0"); }
function unknownMetric(kind) { if (kind === "wallet_valuation") return { status: "unknown", asset: "fleet_wallet_aggregate", quantity: null, currency: "USD", valueUsd: null, verificationStatus: "unavailable", evidenceRef: null };
  if (kind === "external_inflows") return { status: "unknown", asset: "external_stablecoin_transfer_aggregate", quantity: null, unit: "nominal_token_units", currency: null, window: WINDOW, verificationStatus: "unavailable", evidenceRef: null };
  return { status: "unknown", amountUsdPerDay: null, currency: "USD", verificationStatus: "unavailable", evidenceRef: null };
}
function metric(kind, row, id, chain, telemetryAsOf, key, scope, exceptions, account) {
  const field = kind === "wallet_valuation" ? "wallet_valuation" : kind === "external_inflows" ? "external_inflows" : "burn_rate";
  const source = kind === "wallet_valuation" ? row.net_worth_src : kind === "external_inflows" ? row.earn_src : "signed_self_reported";
  const value = kind === "wallet_valuation" ? row.net_worth_usd : kind === "external_inflows" ? row.revenue_mo_usd : row.burn_day_usd;
  const validSource = kind === "burn_rate" || source === "chain", validValue = typeof value === "number" && Number.isFinite(value) && value >= 0;
  if (!validSource || !validValue) { exceptions.push({ accountRef: account, field, reason: validSource ? "missing_value" : "unverified_source" }); return unknownMetric(kind); }
  const evidenceRef = ref(key, scope, kind, claimPreimage(kind, id, chain, telemetryAsOf, source, value, kind === "external_inflows" ? WINDOW : ""));
  if (kind === "wallet_valuation") return { status: "available", asset: "fleet_wallet_aggregate", quantity: null, currency: "USD", valueUsd: value, verificationStatus: "upstream_chain_enriched", evidenceRef };
  if (kind === "external_inflows") return { status: "available", asset: "external_stablecoin_transfer_aggregate", quantity: value, unit: "nominal_token_units", currency: null, window: WINDOW, verificationStatus: "chain_observed_token_inflow", evidenceRef };
  return { status: "available", amountUsdPerDay: value, currency: "USD", verificationStatus: "signed_self_reported", evidenceRef };
}
function lexical(a, b) { return a < b ? -1 : a > b ? 1 : 0; }
function adaptFleetDashboard(input) {
  try {
    const value = snapshot(input); exactKeys(value, INPUT_KEYS);
    if (value.economicScopeRef !== SCOPE) fail("economic_scope");
    const dashboardJson = value.dashboardJson;
    if (typeof dashboardJson !== "string") fail("invalid_json");
    if (typeof value.referenceKey !== "string" || Buffer.byteLength(value.referenceKey, "utf8") < 32) fail("weak_reference_key");
    const observedAt = value.observedAt, readMs = timestamp(observedAt);
    let parsed; try { parsed = JSON.parse(dashboardJson); } catch { fail("invalid_json"); }
    const dashboard = snapshot(parsed);
    if (dashboard === null || typeof dashboard !== "object" || Array.isArray(dashboard)) fail("invalid_dashboard");
    const sourceUpdatedAt = dashboard.updated_at, sourceMs = timestamp(sourceUpdatedAt);
    if (sourceMs > readMs + 5000) fail("source_chronology");
    const leaderboard = dashboard.leaderboard, registry = value.registeredWallets;
    if (!Array.isArray(leaderboard)) fail("invalid_leaderboard");
    if (!Array.isArray(registry)) fail("invalid_array");
    const byIdentity = new Map(), byEvmId = new Map(), bySolanaId = new Map(), records = [];
    for (const entry of registry) {
      exactKeys(entry, REGISTRY_KEYS, "invalid_registry");
      const walletId = entry.walletId, chain = entry.chain;
      if (typeof walletId !== "string" || walletId.length === 0) fail("invalid_wallet_id");
      if (!CHAINS.has(chain)) fail("invalid_chain");
      const id = normalizeIdentity(walletId, chain), identity = `${id}\0${chain}`;
      if (byIdentity.has(identity)) fail("duplicate_registered_wallet");
      const record = { id, chain, accountRef: ref(value.referenceKey, SCOPE, "account", identity), present: false, mismatch: false };
      records.push(record); byIdentity.set(identity, record); const index = chain === "solana" ? bySolanaId : byEvmId;
      if (!index.has(id)) index.set(id, []); index.get(id).push(record);
    }
    const wallets = [], exceptions = [];
    for (const row of leaderboard) {
      if (row === null || typeof row !== "object" || Array.isArray(row)) fail("invalid_row");
      if (typeof row.id !== "string") continue;
      const chain = typeof row.chain === "string" ? row.chain : "";
      const candidates = [...(byEvmId.get(row.id.toLowerCase()) || []), ...(bySolanaId.get(row.id) || [])], registered = candidates.find((record) => record.chain === chain);
      if (!registered) { for (const record of candidates) record.mismatch = true; continue; }
      if (registered.present) fail("duplicate_dashboard_wallet");
      registered.present = true;
      if (!Number.isSafeInteger(row.ts) || row.ts < 0 || row.ts > 8640000000000) fail("invalid_timestamp");
      const telemetryMs = row.ts * 1000, telemetryAsOf = new Date(telemetryMs).toISOString(); if (telemetryMs > sourceMs + 5000) fail("telemetry_chronology");
      const walletExceptions = [], account = registered.accountRef;
      wallets.push({ accountRef: account, chain: registered.chain, telemetryAsOf, telemetryFreshness: sourceMs - telemetryMs <= 300000 ? "fresh" : "stale", walletValuation: metric("wallet_valuation", row, registered.id, registered.chain, telemetryAsOf, value.referenceKey, SCOPE, walletExceptions, account), externalStablecoinInflows: metric("external_inflows", row, registered.id, registered.chain, telemetryAsOf, value.referenceKey, SCOPE, walletExceptions, account), burnRate: metric("burn_rate", row, registered.id, registered.chain, telemetryAsOf, value.referenceKey, SCOPE, walletExceptions, account) });
      exceptions.push(...walletExceptions);
    }
    for (const record of records) if (!record.present) exceptions.push({ accountRef: record.accountRef, field: "wallet", reason: record.mismatch ? "chain_mismatch" : "missing_registered_wallet" });
    wallets.sort((a, b) => lexical(a.accountRef, b.accountRef));
    exceptions.sort((a, b) => lexical(a.accountRef, b.accountRef) || lexical(a.field, b.field) || lexical(a.reason, b.reason));
    return validateFleetSourceResult({ schemaVersion: 1, sourceId: "fleet_dashboard", economicScopeRef: SCOPE, readAsOf: observedAt, sourceUpdatedAt, coverage: { registeredWalletCount: registry.length, presentWalletCount: wallets.length, partial: true }, wallets, exceptions, limitations: LIMITATIONS });
  } catch (error) {
    if (error instanceof AdapterError) throw error;
    throw new Error(`${ERROR_PREFIX}result_invalid`);
  }
}
module.exports = { adaptFleetDashboard };
