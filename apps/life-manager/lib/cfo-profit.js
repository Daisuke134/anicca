"use strict";

const ERROR = "cfo_profit_invalid:business_fact";
const ID = /^[a-z][a-z0-9_]{1,63}$/;
const AMOUNT = /^(?:0|[1-9][0-9]*)(?:\.[0-9]{1,8})?$/;
const SIGNED_AMOUNT = /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]{1,8})?$/;
const STATUS = new Set(["verified", "observed", "unknown", "partial"]);
const EVIDENCE = new Set(["verified", "measured", "estimated", "unknown"]);

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
function iso(value) { return typeof value === "string" && value.length <= 64 && Number.isFinite(Date.parse(value)); }
function amount(value) { return typeof value === "string" && value.length <= 32 && AMOUNT.test(value); }
function freeze(value, seen = new WeakSet()) {
  if (value === null || typeof value !== "object" || seen.has(value)) return value;
  seen.add(value);
  Object.values(value).forEach((child) => freeze(child, seen));
  return Object.freeze(value);
}
function scaled(value) {
  const [whole, fraction = ""] = value.split(".");
  return BigInt(whole + fraction.padEnd(8, "0"));
}
function decimal(value) {
  const fraction = String(value % 100000000n).padStart(8, "0").replace(/0+$/, "");
  return `${value / 100000000n}${fraction ? `.${fraction}` : ".00"}`;
}

function validateCash(value) {
  exact(value, new Set(["status", "currency", "amount_decimal", "observed_at", "evidence_status"]));
  if (!STATUS.has(value.status) || typeof value.currency !== "string" || !/^[A-Z]{3}$/.test(value.currency)
    || (value.amount_decimal !== null && !amount(value.amount_decimal))
    || (value.observed_at !== null && !iso(value.observed_at)) || !EVIDENCE.has(value.evidence_status)) fail();
  if (value.status === "verified" && (value.amount_decimal === null || value.observed_at === null)) fail();
  if (value.status !== "verified" && value.amount_decimal !== null) fail();
  return value;
}

function validateBurn(value) {
  exact(value, new Set(["status", "currency", "amount_decimal", "period", "observed_at", "evidence_status"]));
  if (!STATUS.has(value.status) || value.currency !== "USD" || (value.amount_decimal !== null && !amount(value.amount_decimal))
    || (value.observed_at !== null && !iso(value.observed_at)) || !EVIDENCE.has(value.evidence_status)
    || (value.status === "verified" && (value.amount_decimal === null || value.observed_at === null))
    || (value.status !== "verified" && value.amount_decimal !== null)) fail();
  if (typeof value.period !== "string" || value.period.length === 0 || value.period.length > 32) fail();
  return value;
}

function validateBusiness(value) {
  if (!plain(value) || typeof value.financial_unit_id !== "string" || !ID.test(value.financial_unit_id)
    || !STATUS.has(value.provider_receipt_status) || !Number.isSafeInteger(value.provider_receipt_count)
    || value.provider_receipt_count < 0 || !Array.isArray(value.provider_totals)
    || value.fleet_join_status !== "unknown" && value.fleet_join_status !== "matched"
    || value.landed_cash_status !== "unknown" && value.landed_cash_status !== "verified"
    || value.cost_status !== "unknown" && value.cost_status !== "verified"
    || value.capital_status !== "unknown" && value.capital_status !== "verified") fail();
  if (value.provider_receipt_count === 0 && value.provider_receipt_status !== "unknown") fail();
  if (value.provider_receipt_count > 0 && value.provider_receipt_status === "unknown") fail();
  for (const total of value.provider_totals) {
    if (!plain(total) || typeof total.measurement_kind !== "string" || total.currency !== "USD"
      || !(total.measurement_kind === "realized_pnl" ? SIGNED_AMOUNT.test(String(total.amount_decimal)) : amount(total.amount_decimal))) fail();
  }
  return value;
}

/**
 * Publishes contribution profit, ROI, runway, and evidence completeness only
 * when reconciliation has a comparable revenue/cost/capital join. Realized
 * activity remains visible as evidence but is not silently upgraded to profit.
 */
function composeCfoProfit(input) {
  try {
    exact(input, new Set(["observed_at", "reconciliation", "cash_snapshot", "burn_snapshot"]));
    if (!iso(input.observed_at) || !plain(input.reconciliation) || input.reconciliation.schema_version !== 1
      || !Array.isArray(input.reconciliation.businesses) || !Array.isArray(input.reconciliation.coverage_exceptions)) fail();
    const cash = validateCash(input.cash_snapshot);
    const burn = validateBurn(input.burn_snapshot);
    const businesses = input.reconciliation.businesses.map(validateBusiness);
    const seen = new Set();
    const rows = businesses.map((business) => {
      if (seen.has(business.financial_unit_id)) fail();
      seen.add(business.financial_unit_id);
      const complete = business.fleet_join_status === "matched" && business.landed_cash_status === "verified"
        && business.cost_status === "verified" && business.capital_status === "verified";
      return {
        financial_unit_id: business.financial_unit_id,
        evidence_status: complete ? "complete" : business.provider_receipt_status === "observed" ? "partial" : "unknown",
        provider_receipt_count: business.provider_receipt_count,
        realized_activity: business.provider_totals,
        contribution_profit: null,
        roi: null,
        reason: complete ? null : "reconciliation_join_incomplete",
      };
    });
    const completeCount = rows.filter((row) => row.evidence_status === "complete").length;
    const partialCount = rows.filter((row) => row.evidence_status === "partial").length;
    const exceptions = new Set(input.reconciliation.coverage_exceptions);
    exceptions.add("profit_requires_reconciled_revenue_landed_cash_cost_capital");
    exceptions.add("roi_requires_reconciled_revenue_cost_capital");
    exceptions.add("runway_requires_verified_cash_and_burn");
    exceptions.add("advice_disabled_until_profit_and_reconciliation_close");
    if (cash.status !== "verified") exceptions.add("cash_snapshot_unknown");
    if (burn.status !== "verified") exceptions.add("burn_snapshot_unknown");
    return freeze({
      schema_version: 1,
      observed_at: input.observed_at,
      status: completeCount === rows.length ? "complete" : "partial",
      evidence_completeness: {
        business_count: rows.length,
        complete_count: completeCount,
        partial_count: partialCount,
        unknown_count: rows.length - completeCount - partialCount,
        status: completeCount === rows.length ? "complete" : "partial",
      },
      businesses: rows,
      contribution_profit: null,
      roi: null,
      runway: {
        status: cash.status === "verified" && burn.status === "verified" ? "measured_inputs_pending_join" : "unknown",
        cash: cash.status === "verified" ? { currency: cash.currency, amount_decimal: cash.amount_decimal, evidence_status: cash.evidence_status } : null,
        burn_per_day: burn.status === "verified" ? { currency: burn.currency, amount_decimal: burn.amount_decimal, evidence_status: burn.evidence_status } : null,
        days: null,
      },
      advice_status: "disabled",
      coverage_exceptions: [...exceptions].sort(),
    });
  } catch { throw new Error(ERROR); }
}

module.exports = { composeCfoProfit };
