"use strict";

const ERROR = "cfo_gig_invalid:business_fact";
const COVERAGE = new Set(["verified_external_read", "unknown", "failed"]);
const FRESHNESS = new Set(["fresh", "stale", "unknown"]);
const PAYOUT = new Set(["pending", "paid", "unknown"]);
const RUN = new Set(["SUCCEEDED", "FAILED", "UNKNOWN"]);

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
function amount(value) { return typeof value === "string" && /^(?:0|[1-9][0-9]*)$/.test(value) && value.length <= 32; }
function count(value) { return Number.isSafeInteger(value) && value >= 0; }

/**
 * Keeps the external Coconala receipt, local earnings ledger, and runtime
 * observation separate. A local earnings file never overrides an external
 * mismatch, and neither source can produce profit or ROI before reconciliation.
 */
function composeGigBusinessFact(input) {
  try {
    if (!plain(input) || !iso(input.observed_at) || !plain(input.provider)
      || input.provider.name !== "coconala"
      || !iso(input.provider.observed_at)
      || !COVERAGE.has(input.provider.coverage_status)
      || !FRESHNESS.has(input.provider.freshness_status)
      || !count(input.provider.sales_row_count)
      || !amount(input.provider.sales_total_jpy)
      || !amount(input.provider.balance_jpy)
      || !amount(input.provider.pending_payout_jpy)
      || !PAYOUT.has(input.provider.payout_status)
      || !plain(input.ledger)
      || !count(input.ledger.row_count)
      || !count(input.ledger.evidence_pointer_count)
      || !amount(input.ledger.total_jpy)
      || !plain(input.runtime)
      || !iso(input.runtime.observed_at)
      || !count(input.runtime.duration_ms)
      || !RUN.has(input.runtime.run_state)
      || typeof input.runtime.truth_verified !== "boolean") fail();

    const providerTotal = BigInt(input.provider.sales_total_jpy);
    const ledgerTotal = BigInt(input.ledger.total_jpy);
    const delta = providerTotal >= ledgerTotal ? providerTotal - ledgerTotal : ledgerTotal - providerTotal;
    const reconciliationStatus = providerTotal === ledgerTotal ? "matched" : "mismatch";
    const exceptions = new Set([
      "bank_landed_unknown",
      "capital_unknown",
      "direct_cost_unknown",
      "human_cost_unknown",
      "profit_disabled_until_reconciliation",
      "roi_disabled_until_reconciliation"
    ]);
    if (reconciliationStatus === "mismatch") {
      exceptions.add("external_vs_local_ledger_mismatch");
      exceptions.add("local_ledger_not_authoritative");
    }
    if (input.provider.coverage_status !== "verified_external_read") exceptions.add("external_receipt_unknown");
    if (input.provider.freshness_status !== "fresh") exceptions.add("provider_snapshot_stale_or_unknown");
    if (input.provider.payout_status !== "paid") exceptions.add("payout_not_landed");
    if (input.runtime.run_state !== "SUCCEEDED" || !input.runtime.truth_verified) exceptions.add("runtime_truth_unverified");

    return freeze({
      schema_version: 1,
      financial_unit_id: "gig_work",
      observed_at: input.observed_at,
      status: "partial",
      provider: {
        name: "coconala",
        observation: {
          coverage_status: input.provider.coverage_status,
          freshness_status: input.provider.freshness_status,
          observed_at: input.provider.observed_at,
          sales_row_count: input.provider.sales_row_count,
          sales_total: { currency: "JPY", amount_decimal: input.provider.sales_total_jpy, basis: "provider_sales_total" }
        },
        payout: {
          status: input.provider.payout_status,
          provider_balance: { currency: "JPY", amount_decimal: input.provider.balance_jpy, evidence_status: "provider_reported" },
          pending_payout: { currency: "JPY", amount_decimal: input.provider.pending_payout_jpy, evidence_status: "provider_reported" },
          bank_landed_status: "unknown"
        }
      },
      local_ledger: {
        source: "earnings.jsonl",
        coverage_status: input.ledger.evidence_pointer_count === input.ledger.row_count ? "row_evidence_pointers" : "partial",
        row_count: input.ledger.row_count,
        evidence_pointer_count: input.ledger.evidence_pointer_count,
        total: { currency: "JPY", amount_decimal: input.ledger.total_jpy }
      },
      reconciliation: {
        status: reconciliationStatus,
        currency: "JPY",
        absolute_delta_decimal: String(delta)
      },
      cost: {
        runtime: {
          coverage_status: input.runtime.run_state === "SUCCEEDED" && input.runtime.truth_verified ? "verified" : "measured_failed",
          observations: [{ observed_at: input.runtime.observed_at, duration_seconds: String(input.runtime.duration_ms / 1000), evidence_status: input.runtime.truth_verified ? "runtime_measured" : "runtime_measured_failed" }]
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

module.exports = { composeGigBusinessFact };
