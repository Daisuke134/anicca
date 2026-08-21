"use strict";

const ERROR = "cfo_capafy_invalid:business_fact";
const COVERAGE = new Set(["verified_external_read", "failed", "unknown"]);
const RUN_STATES = new Set(["SUCCEEDED", "FAILED", "UNKNOWN"]);
const PAYOUT_STATES = new Set(["provider_reported_unpaid", "provider_reported_paid", "unknown"]);

function fail() { throw new Error(ERROR); }

function plain(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    && Object.getPrototypeOf(value) === Object.prototype;
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

function date(value) {
  return value === null || (typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value));
}

function count(value) { return Number.isSafeInteger(value) && value >= 0; }
function nullableCount(value) { return value === null || count(value); }
function amount(value) {
  return typeof value === "string"
    && /^(?:0|[1-9][0-9]*)(?:\.[0-9]{1,8})?$/.test(value)
    && value.length <= 32;
}
function nullableAmount(value) { return value === null || amount(value); }
function status(value, allowed) { return typeof value === "string" && allowed.has(value); }
function scaledAmount(value) {
  const [whole, fraction = ""] = value.split(".");
  return BigInt(whole + fraction.padEnd(8, "0"));
}
function isZero(value) { return /^0(?:\.0*)?$/.test(value); }

/**
 * Keeps Capafy buyer sales, seller balances, and paid-out money separate.
 * A provider sales receipt is not a bank landing; costs, capital, profit, and
 * ROI remain unavailable until the later reconciliation slice.
 */
function composeCapafyBusinessFact(input) {
  try {
    if (!plain(input) || !iso(input.observed_at) || !plain(input.provider)
      || input.provider.name !== "capafy"
      || !iso(input.provider.observed_at)
      || !status(input.provider.sales_coverage_status, COVERAGE)
      || !status(input.provider.payout_coverage_status, COVERAGE)
      || input.provider.currency !== "USD"
      || !nullableCount(input.provider.lookback_days)
      || !nullableCount(input.provider.trend_request_count)
      || !nullableCount(input.provider.trend_row_count)
      || !nullableCount(input.provider.paid_sales_day_count)
      || !nullableCount(input.provider.order_count)
      || !nullableAmount(input.provider.gross_sales_usd)
      || !nullableAmount(input.provider.net_sales_usd)
      || !nullableAmount(input.provider.refund_amount_usd)
      || !date(input.provider.latest_order_date)
      || !date(input.provider.latest_paid_sale_date)
      || !nullableCount(input.provider.payout_record_count)
      || !nullableCount(input.provider.paid_payout_record_count)
      || !nullableAmount(input.provider.balance_pending_usd)
      || !nullableAmount(input.provider.balance_confirmed_usd)
      || !nullableAmount(input.provider.balance_payout_usd)
      || !nullableAmount(input.provider.total_payout_usd)
      || !status(input.provider.payout_status, PAYOUT_STATES)
      || !plain(input.runtime)
      || !iso(input.runtime.observed_at)
      || !(input.runtime.duration_ms === null || count(input.runtime.duration_ms))
      || !RUN_STATES.has(input.runtime.run_state)
      || typeof input.runtime.truth_verified !== "boolean") fail();

    const p = input.provider;
    const salesVerified = p.sales_coverage_status === "verified_external_read";
    const payoutVerified = p.payout_coverage_status === "verified_external_read";
    if (salesVerified && (p.lookback_days === null || p.lookback_days < 1 || p.lookback_days > 90
      || p.trend_request_count === null || p.trend_request_count < 1
      || p.trend_row_count === null || p.paid_sales_day_count === null || p.order_count === null
      || p.gross_sales_usd === null || p.net_sales_usd === null || p.refund_amount_usd === null)) fail();
    if (payoutVerified && (p.payout_record_count === null || p.paid_payout_record_count === null
      || p.balance_pending_usd === null || p.balance_confirmed_usd === null
      || p.balance_payout_usd === null || p.total_payout_usd === null)) fail();
    if (!salesVerified && (p.lookback_days !== null || p.trend_request_count !== null
      || p.trend_row_count !== null || p.paid_sales_day_count !== null || p.order_count !== null
      || p.gross_sales_usd !== null || p.net_sales_usd !== null || p.refund_amount_usd !== null
      || p.latest_order_date !== null || p.latest_paid_sale_date !== null)) fail();
    if (!payoutVerified && (p.payout_record_count !== null || p.paid_payout_record_count !== null
      || p.balance_pending_usd !== null || p.balance_confirmed_usd !== null
      || p.balance_payout_usd !== null || p.total_payout_usd !== null)) fail();
    if (salesVerified && p.net_sales_usd !== null && p.gross_sales_usd !== null
      && scaledAmount(p.net_sales_usd) > scaledAmount(p.gross_sales_usd)) fail();
    if (salesVerified && p.paid_sales_day_count !== null && p.order_count !== null
      && p.paid_sales_day_count > p.order_count) fail();
    if (payoutVerified && p.paid_payout_record_count > p.payout_record_count) fail();
    if (p.payout_status === "provider_reported_paid" && isZero(p.total_payout_usd)) fail();
    if (p.payout_status === "provider_reported_unpaid" && !isZero(p.total_payout_usd)) fail();

    const exceptions = new Set([
      "bank_landed_unknown",
      "direct_api_cost_unknown",
      "human_cost_unknown",
      "capital_unknown",
      "profit_disabled_until_cost_reconciliation",
      "roi_disabled_until_cost_reconciliation",
      "seller_take_and_gross_scope_separate",
      "sales_scope_is_bounded_lookback"
    ]);
    if (!salesVerified) exceptions.add("sales_receipt_unknown");
    if (!payoutVerified) exceptions.add("payout_receipt_unknown");
    if (p.payout_status !== "provider_reported_paid") exceptions.add("payout_not_landed");
    if (input.runtime.run_state !== "SUCCEEDED" || !input.runtime.truth_verified) {
      exceptions.add("runtime_truth_unverified");
    }

    const money = (value, evidenceStatus = "provider_reported") => value === null ? null : {
      currency: "USD", amount_decimal: value, evidence_status: evidenceStatus
    };
    return freeze({
      schema_version: 1,
      financial_unit_id: "capafy_marketplace",
      observed_at: input.observed_at,
      status: "partial",
      scope: "capafy_publisher_provider_receipts",
      sales: {
        coverage_status: p.sales_coverage_status,
        lookback_days: p.lookback_days,
        trend_request_count: p.trend_request_count,
        trend_row_count: p.trend_row_count,
        paid_sales_day_count: p.paid_sales_day_count,
        order_count: p.order_count,
        gross: money(p.gross_sales_usd),
        net: money(p.net_sales_usd),
        refunds: money(p.refund_amount_usd),
        latest_order_date: p.latest_order_date,
        latest_paid_sale_date: p.latest_paid_sale_date,
        evidence_status: salesVerified ? "provider_sales_trend" : "unknown"
      },
      payout: {
        coverage_status: p.payout_coverage_status,
        record_count: p.payout_record_count,
        paid_record_count: p.paid_payout_record_count,
        status: p.payout_status,
        balance_pending: money(p.balance_pending_usd),
        balance_confirmed: money(p.balance_confirmed_usd),
        balance_payout: money(p.balance_payout_usd),
        total_paid: money(p.total_payout_usd, "provider_payout_record"),
        bank_landed_status: "unknown",
        evidence_status: payoutVerified ? "provider_payout_info_and_records" : "unknown"
      },
      cost: {
        runtime: {
          coverage_status: input.runtime.run_state === "SUCCEEDED" && input.runtime.truth_verified
            ? "verified"
            : input.runtime.duration_ms === null ? "unknown" : "measured_failed",
          observations: [{
            observed_at: input.runtime.observed_at,
            duration_seconds: input.runtime.duration_ms === null
              ? null : String(input.runtime.duration_ms / 1000),
            evidence_status: input.runtime.truth_verified ? "runtime_measured" : "runtime_unverified"
          }]
        },
        direct_api: { coverage_status: "unknown", amount: null },
        human: { coverage_status: "unknown", amount: null }
      },
      capital: { coverage_status: "unknown", amount: null },
      profit: null,
      roi: null,
      coverage_exceptions: [...exceptions].sort()
    });
  } catch { throw new Error(ERROR); }
}

module.exports = { composeCapafyBusinessFact };
