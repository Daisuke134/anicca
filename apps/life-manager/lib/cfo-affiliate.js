"use strict";

const ERROR = "cfo_affiliate_invalid:business_fact";
const STATES = new Set(["AUTHENTICATED", "UNAUTHENTICATED", "UNKNOWN"]);
const ROW_STATES = new Set(["EMPTY", "ROWS_PRESENT", "UNKNOWN"]);
const NET_STATES = new Set(["NO_APPROVED_OR_PAID_ROWS", "ROWS_PRESENT", "UNKNOWN"]);
const MONEY_STATES = new Set(["NO_TRANSACTIONS", "TRANSACTIONS_PRESENT", "UNKNOWN"]);
const PAYOUT_STATES = new Set(["PAYOUT_BLOCKED_BY_TAX_SETUP", "READY", "UNKNOWN"]);
const TAX_STATES = new Set(["REQUIRED", "COMPLETE", "UNKNOWN"]);
const PAYMENT_STATES = new Set(["SELECTION_REQUIRED", "SELECTED", "UNKNOWN"]);
const RUN_STATES = new Set(["SUCCEEDED", "FAILED", "UNKNOWN"]);

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
function iso(value) { return typeof value === "string" && value.length <= 64 && Number.isFinite(Date.parse(value)); }
function safeCount(value) { return Number.isSafeInteger(value) && value >= 0; }
function state(value, allowed) { return typeof value === "string" && allowed.has(value); }

/**
 * Projects provider receipts and measured loop runtime into a privacy-safe CFO
 * observation. Provider-reported empty rows are kept as an observation; they
 * never become an Affiliate-wide zero or a profit/ROI input.
 */
function composeAffiliateBusinessFact(input) {
  try {
    if (!plain(input) || !iso(input.observed_at) || !plain(input.provider)
      || input.provider.name !== "partnerstack"
      || !state(input.provider.authentication_state, STATES)
      || !state(input.provider.commission_row_state, ROW_STATES)
      || !state(input.provider.net_state, NET_STATES)
      || !state(input.provider.money_state, MONEY_STATES)
      || !safeCount(input.provider.commission_row_count)
      || !plain(input.provider.status_counts)
      || !["approved", "paid", "pending", "reversed"].every((key) => safeCount(input.provider.status_counts[key]))
      || !state(input.provider.payout_readiness, PAYOUT_STATES)
      || !state(input.provider.tax_information_state, TAX_STATES)
      || !state(input.provider.payment_provider_state, PAYMENT_STATES)
      || !plain(input.runtime)
      || !iso(input.runtime.observed_at)
      || !safeCount(input.runtime.duration_ms)
      || !state(input.runtime.run_state, RUN_STATES)) fail();

    const rowStatus = input.provider.commission_row_count === 0
      && input.provider.commission_row_state === "EMPTY"
      ? "provider_reported_empty" : input.provider.commission_row_count > 0
        ? "provider_reported" : "unknown";
    const exceptions = [
      "affiliate_total_not_closed",
      "capital_unknown",
      "direct_cost_unknown",
      "human_cost_unknown",
      "landed_cash_unknown",
      "profit_disabled_until_reconciliation",
      "roi_disabled_until_reconciliation",
      "payout_unknown"
    ];
    if (rowStatus === "unknown" || input.provider.net_state === "UNKNOWN") exceptions.push("commission_receipts_unknown");
    if (input.provider.payout_readiness !== "READY") exceptions.push("payout_not_ready");
    if (input.runtime.run_state !== "SUCCEEDED") exceptions.push("runtime_run_not_succeeded");

    return freeze({
      schema_version: 1,
      financial_unit_id: "affiliate_agent",
      observed_at: input.observed_at,
      status: "partial",
      provider: {
        name: "partnerstack",
        authentication_status: input.provider.authentication_state,
        commission: {
          coverage_status: rowStatus,
          row_count: input.provider.commission_row_count,
          status_counts: { ...input.provider.status_counts },
          net_state: input.provider.net_state,
          money_state: input.provider.money_state,
          gross: null,
          net: null,
          landed_cash_status: "unknown"
        },
        payout: {
          readiness: input.provider.payout_readiness,
          tax_information: input.provider.tax_information_state,
          payment_provider: input.provider.payment_provider_state
        }
      },
      cost: {
        runtime: {
          coverage_status: input.runtime.run_state === "SUCCEEDED" ? "verified" : "partial",
          observations: [{
            observed_at: input.runtime.observed_at,
            duration_seconds: String(input.runtime.duration_ms / 1000),
            evidence_status: "runtime_measured"
          }]
        },
        direct_api: { coverage_status: "unknown", amount: null },
        human: { coverage_status: "unknown", amount: null }
      },
      capital: { coverage_status: "unknown", amount: null },
      profit: null,
      roi: null,
      coverage_exceptions: [...new Set(exceptions)].sort()
    });
  } catch { throw new Error(ERROR); }
}

module.exports = { composeAffiliateBusinessFact };
