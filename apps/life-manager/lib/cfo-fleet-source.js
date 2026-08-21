"use strict";

const { types } = require("node:util");

const ERROR_PREFIX = "fleet_source_invalid:";
const ROOT_KEYS = new Set(["schemaVersion", "sourceId", "economicScopeRef", "readAsOf", "sourceUpdatedAt", "coverage", "wallets", "exceptions", "limitations"]);
const COVERAGE_KEYS = new Set(["registeredWalletCount", "presentWalletCount", "partial"]);
const WALLET_KEYS = new Set(["accountRef", "chain", "telemetryAsOf", "telemetryFreshness", "walletValuation", "externalStablecoinInflows", "burnRate"]);
const VALUATION_KEYS = new Set(["status", "asset", "quantity", "currency", "valueUsd", "verificationStatus", "evidenceRef"]);
const INFLOW_KEYS = new Set(["status", "asset", "quantity", "unit", "currency", "window", "verificationStatus", "evidenceRef"]);
const BURN_KEYS = new Set(["status", "amountUsdPerDay", "currency", "verificationStatus", "evidenceRef"]);
const EXCEPTION_KEYS = new Set(["accountRef", "field", "reason"]);
const CHAINS = new Set(["base", "polygon", "polygon-proxy", "solana"]);
const STATUSES = new Set(["available", "unknown"]);
const FIELDS = new Set(["wallet", "wallet_valuation", "external_inflows", "burn_rate"]);
const WALLET_REASONS = new Set(["missing_registered_wallet", "chain_mismatch"]);
const METRIC_REASONS = new Set(["unverified_source", "missing_value"]);
const ACCOUNT_REF = /^source_account:fleet_[a-f0-9]{24}$/;
const EVIDENCE_REF = /^evidence:fleet_[a-f0-9]{24}$/;
const RFC3339 = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?(Z|[+-]\d{2}:\d{2})$/;
const LIMITATIONS = [
  "asset_positions_unavailable",
  "valuation_quote_provenance_unavailable",
  "inflows_not_recognized_revenue",
  "inflow_window_approximate",
  "burn_estimated",
  "economic_owner_mapping_unavailable",
];

class FleetSourceError extends Error {}

function fail(reason) { throw new FleetSourceError(`${ERROR_PREFIX}${reason}`); }
function hasValue(descriptor) { return descriptor && Object.prototype.hasOwnProperty.call(descriptor, "value"); }
function contractError(error) { return error instanceof FleetSourceError; }

function snapshot(input, active = new WeakSet()) {
  if (input === null) return null;
  if (typeof input === "string" || typeof input === "boolean" || typeof input === "number") return input;
  if (typeof input !== "object") fail("invalid_value");
  if (types.isProxy(input)) fail("proxy_input");
  if (active.has(input)) fail("cycle");

  let prototype;
  try { prototype = Object.getPrototypeOf(input); } catch { fail("invalid_input"); }
  const array = Array.isArray(input);
  if (prototype !== (array ? Array.prototype : Object.prototype)) fail("invalid_prototype");
  active.add(input);
  try {
    const ownKeys = Reflect.ownKeys(input);
    if (array) {
      const lengthDescriptor = Object.getOwnPropertyDescriptor(input, "length");
      const length = lengthDescriptor && lengthDescriptor.value;
      if (!hasValue(lengthDescriptor) || lengthDescriptor.enumerable || !Number.isSafeInteger(length) || length < 0 || length >= 4294967295) fail("invalid_array");
      if (ownKeys.length !== length + 1) fail("invalid_array");
      const clone = new Array(length);
      const indexes = new Set();
      for (const key of ownKeys) {
        if (key === "length") continue;
        if (typeof key !== "string" || !/^(0|[1-9]\d*)$/.test(key) || Number(key) >= length) fail("invalid_array");
        const descriptor = Object.getOwnPropertyDescriptor(input, key);
        if (!hasValue(descriptor) || !descriptor.enumerable) fail(hasValue(descriptor) ? "invalid_array" : "accessor_property");
        indexes.add(Number(key));
        Object.defineProperty(clone, key, { value: snapshot(descriptor.value, active), enumerable: true, writable: true, configurable: true });
      }
      if (indexes.size !== length) fail("invalid_array");
      return clone;
    }

    const clone = {};
    for (const key of ownKeys) {
      if (typeof key !== "string") fail("symbol_key");
      const descriptor = Object.getOwnPropertyDescriptor(input, key);
      if (!hasValue(descriptor)) fail("accessor_property");
      if (!descriptor.enumerable) fail("invalid_keys");
      Object.defineProperty(clone, key, { value: snapshot(descriptor.value, active), enumerable: true, writable: true, configurable: true });
    }
    return clone;
  } catch (error) {
    if (contractError(error)) throw error;
    fail("invalid_input");
  } finally {
    active.delete(input);
  }
}

function exactKeys(value, allowed) {
  if (value === null || typeof value !== "object" || Array.isArray(value) || Object.getPrototypeOf(value) !== Object.prototype) fail("invalid_object");
  const keys = Reflect.ownKeys(value);
  if (keys.length !== allowed.size || keys.some((key) => typeof key !== "string" || !allowed.has(key) || !Object.prototype.propertyIsEnumerable.call(value, key))) fail("invalid_keys");
}

function timestamp(value) {
  const match = typeof value === "string" && RFC3339.exec(value);
  if (!match) fail("invalid_timestamp");
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const hour = Number(match[4]);
  const minute = Number(match[5]);
  const second = Number(match[6]);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const monthDays = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (month < 1 || month > 12 || day < 1 || day > monthDays[month - 1] || hour > 23 || minute > 59 || second > 59) fail("invalid_timestamp");
  const zone = match[8];
  const zoneHour = zone === "Z" ? 0 : Number(zone.slice(1, 3));
  const zoneMinute = zone === "Z" ? 0 : Number(zone.slice(4));
  if (zoneHour > 23 || zoneMinute > 59) fail("invalid_timestamp");
  const local = new Date(0);
  local.setUTCFullYear(year, month - 1, day);
  local.setUTCHours(hour, minute, second, 0);
  const fraction = match[7] ? Number(`0${match[7]}`) * 1000 : 0;
  if (!Number.isFinite(fraction)) fail("invalid_timestamp");
  const offsetMinutes = zone === "Z" ? 0 : (zone[0] === "+" ? 1 : -1) * (zoneHour * 60 + zoneMinute);
  return local.getTime() - offsetMinutes * 60000 + fraction;
}

function amount(value) {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) fail("invalid_amount");
}

function typedRef(value, pattern, reason) {
  if (typeof value !== "string" || !pattern.test(value)) fail(reason);
}

function metric(value, kind) {
  const keys = kind === "wallet_valuation" ? VALUATION_KEYS : kind === "external_inflows" ? INFLOW_KEYS : BURN_KEYS;
  exactKeys(value, keys);
  if (!STATUSES.has(value.status)) fail("invalid_metric_status");
  if (kind === "wallet_valuation" && (value.asset !== "fleet_wallet_aggregate" || value.quantity !== null || value.currency !== "USD")) fail("invalid_metric_constants");
  if (kind === "external_inflows" && (value.asset !== "external_stablecoin_transfer_aggregate" || value.unit !== "nominal_token_units" || value.currency !== null || value.window !== "approx_1200000_blocks")) fail("invalid_metric_constants");
  if (kind === "burn_rate" && value.currency !== "USD") fail("invalid_metric_constants");
  const amountKey = kind === "wallet_valuation" ? "valueUsd" : kind === "external_inflows" ? "quantity" : "amountUsdPerDay";
  const verification = kind === "wallet_valuation" ? "upstream_chain_enriched" : kind === "external_inflows" ? "chain_observed_token_inflow" : "signed_self_reported";
  if (value.status === "available") {
    amount(value[amountKey]);
    if (value.verificationStatus !== verification) fail("invalid_metric_status");
    typedRef(value.evidenceRef, EVIDENCE_REF, "invalid_evidence_ref");
  } else if (value[amountKey] !== null || value.verificationStatus !== "unavailable" || value.evidenceRef !== null) {
    fail("invalid_metric_state");
  }
  return value.status;
}

function exception(value, emitted, pairs, absent) {
  exactKeys(value, EXCEPTION_KEYS);
  typedRef(value.accountRef, ACCOUNT_REF, "invalid_account_ref");
  if (!FIELDS.has(value.field)) fail("invalid_exception");
  if (value.field === "wallet") {
    if (emitted.has(value.accountRef) || !WALLET_REASONS.has(value.reason) || absent.has(value.accountRef)) fail("invalid_exception");
    absent.add(value.accountRef);
    return;
  }
  if (!emitted.has(value.accountRef) || !METRIC_REASONS.has(value.reason)) fail("invalid_exception");
  const pair = `${value.accountRef}\0${value.field}`;
  if (pairs.has(pair)) fail("duplicate_exception");
  pairs.add(pair);
}

function freeze(value, seen = new WeakSet()) {
  if (value === null || typeof value !== "object" || seen.has(value)) return value;
  seen.add(value);
  for (const child of Object.values(value)) freeze(child, seen);
  return Object.freeze(value);
}

function validateFleetSourceResult(input) {
  try {
    const value = snapshot(input);
    exactKeys(value, ROOT_KEYS);
    if (value.schemaVersion !== 1) fail("schema_version");
    if (value.sourceId !== "fleet_dashboard") fail("source_id");
    if (value.economicScopeRef !== "organization:anicca_fleet") fail("economic_scope");
    const readAsOf = timestamp(value.readAsOf);
    const sourceUpdatedAt = timestamp(value.sourceUpdatedAt);
    if (sourceUpdatedAt > readAsOf + 5000) fail("source_chronology");
    exactKeys(value.coverage, COVERAGE_KEYS);
    if (!Number.isSafeInteger(value.coverage.registeredWalletCount) || value.coverage.registeredWalletCount < 0 || !Number.isSafeInteger(value.coverage.presentWalletCount) || value.coverage.presentWalletCount < 0 || value.coverage.partial !== true) fail("coverage");
    if (!Array.isArray(value.wallets) || !Array.isArray(value.exceptions) || !Array.isArray(value.limitations)) fail("invalid_array");
    if (value.limitations.length !== LIMITATIONS.length || value.limitations.some((item, index) => item !== LIMITATIONS[index])) fail("limitations");

    const emitted = new Set();
    const unknownFields = [];
    for (const wallet of value.wallets) {
      exactKeys(wallet, WALLET_KEYS);
      typedRef(wallet.accountRef, ACCOUNT_REF, "invalid_account_ref");
      if (emitted.has(wallet.accountRef)) fail("duplicate_account_ref");
      emitted.add(wallet.accountRef);
      if (!CHAINS.has(wallet.chain)) fail("invalid_chain");
      const telemetryAsOf = timestamp(wallet.telemetryAsOf);
      if (telemetryAsOf > sourceUpdatedAt + 5000) fail("telemetry_chronology");
      const expectedFreshness = sourceUpdatedAt - telemetryAsOf <= 300000 ? "fresh" : "stale";
      if (wallet.telemetryFreshness !== expectedFreshness) fail("freshness_mismatch");
      for (const [field, metricValue] of [["wallet_valuation", wallet.walletValuation], ["external_inflows", wallet.externalStablecoinInflows], ["burn_rate", wallet.burnRate]]) {
        if (metric(metricValue, field) === "unknown") unknownFields.push(`${wallet.accountRef}\0${field}`);
      }
    }
    if (value.coverage.presentWalletCount !== value.wallets.length) fail("coverage_count");
    const pairs = new Set();
    const absent = new Set();
    for (const item of value.exceptions) exception(item, emitted, pairs, absent);
    for (const pair of unknownFields) {
      if (!pairs.has(pair)) fail("missing_exception");
    }
    for (const pair of pairs) {
      if (!unknownFields.includes(pair)) fail("unexpected_exception");
    }
    if (value.coverage.registeredWalletCount !== value.wallets.length + absent.size) fail("coverage_count");
    return freeze(value);
  } catch (error) {
    if (contractError(error)) throw error;
    fail("invalid_input");
  }
}

module.exports = { validateFleetSourceResult };
