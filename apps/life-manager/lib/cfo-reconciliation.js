"use strict";

const { validateFleetSourceResult } = require("./cfo-fleet-source.js");

const ERROR = "cfo_reconciliation_invalid:business_fact";
const BUSINESS_ID = /^[a-z][a-z0-9_]{1,63}$/;
const SOURCE = /^[a-z][a-z0-9_:-]{1,80}$/;
const AMOUNT = /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]{1,8})?$/;
const NON_NEGATIVE = /^(?:0|[1-9][0-9]*)(?:\.[0-9]{1,8})?$/;
const MEASUREMENT = new Set(["external_income", "realized_pnl", "fee"]);
const EVIDENCE = new Set(["verified_provider_receipt", "verified_append_only_ledger", "unknown"]);
const USAGE_STATUS = new Set(["complete", "ready", "partial", "empty", "unavailable"]);
const ATTRIBUTION = new Set(["complete", "partial", "unknown"]);
const ROOT_KEYS = new Set(["observed_at", "business_unit_ids", "provider_receipts", "fleet_source", "usage", "api_cost"]);
const RECEIPT_KEYS = new Set(["business_id", "source", "observed_at", "measurement_kind", "currency", "amount_usd", "evidence_status"]);
const USAGE_KEYS = new Set(["observed_at", "sources"]);
const USAGE_SOURCE_KEYS = new Set(["source_id", "status", "event_count", "attributed_count", "unattributed_count", "missing_usage_count", "runner_collision_groups", "coverage_exceptions", "by_business"]);
const USAGE_BUSINESS_KEYS = new Set(["business_id", "event_count", "attributed_count", "missing_usage_count"]);
const COST_KEYS = new Set(["observed_at", "row_count", "total_est_usd", "attribution_status", "attributed_est_usd", "unattributed_est_usd", "latest_at"]);

function fail() { throw new Error(ERROR); }
function plain(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    && Object.getPrototypeOf(value) === Object.prototype;
}
function exact(value, allowed) {
  if (!plain(value)) fail();
  const keys = Object.keys(value);
  if (keys.length !== allowed.size || keys.some((key) => !allowed.has(key))) fail();
}
function freeze(value, seen = new WeakSet()) {
  if (value === null || typeof value !== "object" || seen.has(value)) return value;
  seen.add(value);
  Object.values(value).forEach((child) => freeze(child, seen));
  return Object.freeze(value);
}
function iso(value) {
  return typeof value === "string" && value.length <= 64 && Number.isFinite(Date.parse(value));
}
function nonNegativeInteger(value) { return Number.isSafeInteger(value) && value >= 0; }
function amount(value) { return typeof value === "string" && value.length <= 32 && AMOUNT.test(value); }
function nonNegativeAmount(value) { return typeof value === "string" && value.length <= 32 && NON_NEGATIVE.test(value); }
function scaled(value) {
  const negative = value[0] === "-";
  const raw = negative ? value.slice(1) : value;
  const [whole, fraction = ""] = raw.split(".");
  const result = BigInt(whole + fraction.padEnd(8, "0"));
  return negative ? -result : result;
}
function decimal(value) {
  const negative = value < 0n;
  const absolute = negative ? -value : value;
  const fraction = String(absolute % 100000000n).padStart(8, "0").replace(/0+$/, "");
  return `${negative ? "-" : ""}${absolute / 100000000n}${fraction ? `.${fraction}` : ".00"}`;
}
function decimalFromNumber(value) {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) fail();
  const raw = value.toFixed(8).replace(/0+$/, "").replace(/\.$/, "");
  return scaled(raw || "0");
}
function sumMetric(wallets, field, amountKey) {
  if (!wallets.length || wallets.some((wallet) => wallet[field].status !== "available")) return null;
  return wallets.reduce((total, wallet) => total + decimalFromNumber(wallet[field][amountKey]), 0n);
}
function sortedUnique(values) { return [...new Set(values)].sort(); }

function validateReceipt(value, businessIds) {
  exact(value, RECEIPT_KEYS);
  if (typeof value.business_id !== "string" || !BUSINESS_ID.test(value.business_id) || !businessIds.has(value.business_id)) fail();
  if (typeof value.source !== "string" || !SOURCE.test(value.source)) fail();
  if (!iso(value.observed_at) || !MEASUREMENT.has(value.measurement_kind) || value.currency !== "USD"
    || !amount(value.amount_usd) || !EVIDENCE.has(value.evidence_status)) fail();
  if (value.evidence_status === "unknown") fail();
  return value;
}

function validateUsage(input, businessIds) {
  exact(input, USAGE_KEYS);
  if (!iso(input.observed_at) || !Array.isArray(input.sources)) fail();
  const sources = input.sources.map((source) => {
    exact(source, USAGE_SOURCE_KEYS);
    if (typeof source.source_id !== "string" || !SOURCE.test(source.source_id)
      || !USAGE_STATUS.has(source.status) || !nonNegativeInteger(source.event_count)
      || !nonNegativeInteger(source.attributed_count) || !nonNegativeInteger(source.unattributed_count)
      || !nonNegativeInteger(source.missing_usage_count) || !nonNegativeInteger(source.runner_collision_groups)
      || !Array.isArray(source.coverage_exceptions) || source.coverage_exceptions.some((item) => typeof item !== "string")
      || !Array.isArray(source.by_business)) fail();
    if (source.attributed_count + source.unattributed_count > source.event_count) fail();
    const seen = new Set();
    const byBusiness = source.by_business.map((row) => {
      exact(row, USAGE_BUSINESS_KEYS);
      if (typeof row.business_id !== "string" || !BUSINESS_ID.test(row.business_id) || !businessIds.has(row.business_id)
        || seen.has(row.business_id) || !nonNegativeInteger(row.event_count)
        || !nonNegativeInteger(row.attributed_count) || !nonNegativeInteger(row.missing_usage_count)) fail();
      seen.add(row.business_id);
      return row;
    }).sort((a, b) => a.business_id.localeCompare(b.business_id));
    return { ...source, by_business: byBusiness, coverage_exceptions: sortedUnique(source.coverage_exceptions) };
  });
  return sources;
}

function validateCost(input) {
  exact(input, COST_KEYS);
  if (!iso(input.observed_at) || !nonNegativeInteger(input.row_count) || !nonNegativeAmount(input.total_est_usd)
    || !ATTRIBUTION.has(input.attribution_status) || (input.attributed_est_usd !== null && !nonNegativeAmount(input.attributed_est_usd))
    || (input.unattributed_est_usd !== null && !nonNegativeAmount(input.unattributed_est_usd))
    || (input.latest_at !== null && !iso(input.latest_at))) fail();
  if (input.attributed_est_usd !== null && input.unattributed_est_usd !== null
    && scaled(input.attributed_est_usd) + scaled(input.unattributed_est_usd) !== scaled(input.total_est_usd)) fail();
  return input;
}

function composeCfoReconciliation(input) {
  try {
    exact(input, ROOT_KEYS);
    if (!iso(input.observed_at) || !Array.isArray(input.business_unit_ids) || input.business_unit_ids.length === 0) fail();
    const businessIds = new Set();
    for (const id of input.business_unit_ids) {
      if (typeof id !== "string" || !BUSINESS_ID.test(id) || businessIds.has(id)) fail();
      businessIds.add(id);
    }
    if (!Array.isArray(input.provider_receipts)) fail();
    const receipts = input.provider_receipts.map((receipt) => validateReceipt(receipt, businessIds));
    const fleet = validateFleetSourceResult(input.fleet_source);
    const usage = validateUsage(input.usage, businessIds);
    const costs = validateCost(input.api_cost);
    const receiptMap = new Map(input.business_unit_ids.map((id) => [id, []]));
    for (const receipt of receipts) receiptMap.get(receipt.business_id).push(receipt);
    const fleetValuation = sumMetric(fleet.wallets, "walletValuation", "valueUsd");
    const fleetInflows = sumMetric(fleet.wallets, "externalStablecoinInflows", "quantity");
    const fleetBurn = sumMetric(fleet.wallets, "burnRate", "amountUsdPerDay");
    const fleetHasRows = fleet.coverage.presentWalletCount > 0;
    const exceptions = new Set([
      "provider_statement_to_fleet_join_unknown",
      "fleet_economic_owner_mapping_unknown",
      "landed_cash_unknown",
      "capital_unknown",
      "profit_disabled_until_reconciliation",
      "roi_disabled_until_reconciliation",
      "nominal_inflows_not_recognized_revenue",
      "burn_is_estimated_self_reported",
    ]);
    if (!fleetHasRows) exceptions.add("fleet_rows_missing");
    if (costs.attribution_status !== "complete") exceptions.add("api_cost_business_attribution_unknown");
    if (usage.some((source) => source.status !== "complete" || source.unattributed_count > 0 || source.missing_usage_count > 0 || source.runner_collision_groups > 0)) {
      exceptions.add("local_usage_coverage_partial");
    }
    const businesses = input.business_unit_ids.map((id) => {
      const own = receiptMap.get(id);
      const totals = new Map();
      for (const receipt of own) totals.set(receipt.measurement_kind, (totals.get(receipt.measurement_kind) || 0n) + scaled(receipt.amount_usd));
      return {
        financial_unit_id: id,
        provider_receipt_status: own.length ? "observed" : "unknown",
        provider_receipt_count: own.length,
        provider_totals: [...totals.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([kind, total]) => ({ measurement_kind: kind, currency: "USD", amount_decimal: decimal(total) })),
        fleet_join_status: "unknown",
        landed_cash_status: "unknown",
        cost_status: "unknown",
        capital_status: "unknown",
        profit: null,
        roi: null,
      };
    });
    return freeze({
      schema_version: 1,
      observed_at: input.observed_at,
      status: "partial",
      reconciliation_status: fleetHasRows ? "provider_fleet_join_unknown" : "incomplete_fleet_read",
      businesses,
      fleet: {
        source_id: fleet.sourceId,
        read_as_of: fleet.readAsOf,
        source_updated_at: fleet.sourceUpdatedAt,
        coverage: fleet.coverage,
        wallet_valuation: { status: fleetValuation === null ? "unknown" : "upstream_chain_enriched", currency: "USD", amount_decimal: fleetValuation === null ? null : decimal(fleetValuation), owner_mapping_status: "unknown" },
        nominal_inflows: { status: fleetInflows === null ? "unknown" : "chain_observed_token_inflow", unit: "nominal_token_units", amount_decimal: fleetInflows === null ? null : decimal(fleetInflows), recognized_as_revenue: false },
        burn_rate: { status: fleetBurn === null ? "unknown" : "signed_self_reported", currency: "USD", amount_usd_per_day: fleetBurn === null ? null : decimal(fleetBurn), evidence_status: fleetBurn === null ? "unknown" : "estimated" },
      },
      usage: { observed_at: input.usage.observed_at, sources: usage, attribution_status: usage.every((source) => source.status === "complete" && source.unattributed_count === 0) ? "complete" : "partial" },
      api_cost: { observed_at: costs.observed_at, row_count: costs.row_count, total_est_usd: costs.total_est_usd, attribution_status: costs.attribution_status, attributed_est_usd: costs.attributed_est_usd, unattributed_est_usd: costs.unattributed_est_usd, latest_at: costs.latest_at },
      coverage_exceptions: [...exceptions].sort(),
    });
  } catch { throw new Error(ERROR); }
}

module.exports = { composeCfoReconciliation };
