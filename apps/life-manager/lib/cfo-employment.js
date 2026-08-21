"use strict";

const ERROR = "cfo_employment_invalid:business_fact";
const COVERAGE = new Set([
  "verified_payroll_receipt",
  "verified_bank_landed",
  "no_payroll_receipt",
  "unknown"
]);
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

function iso(value) {
  return typeof value === "string" && value.length <= 64 && Number.isFinite(Date.parse(value));
}

function count(value) { return Number.isSafeInteger(value) && value >= 0; }
function nullableCount(value) { return value === null || count(value); }
function amount(value) {
  return typeof value === "string"
    && /^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/.test(value)
    && value.length <= 32;
}
function nullableAmount(value) { return value === null || amount(value); }

/**
 * Projects the job-search funnel without treating a job posting, desired
 * compensation, offer, or application state as earned employment income.
 * Payroll or bank evidence is the only path that can produce an amount.
 */
function composeEmploymentBusinessFact(input) {
  try {
    if (!plain(input) || !iso(input.observed_at) || !plain(input.provider)
      || input.provider.name !== "job_search"
      || !iso(input.provider.observed_at)
      || !COVERAGE.has(input.provider.coverage_status)
      || !nullableCount(input.provider.application_count)
      || !nullableCount(input.provider.confirmed_application_count)
      || !nullableCount(input.provider.offer_count)
      || !nullableCount(input.provider.accepted_count)
      || !nullableCount(input.provider.started_count)
      || !nullableCount(input.provider.payroll_receipt_count)
      || !nullableCount(input.provider.bank_receipt_count)
      || !nullableAmount(input.provider.payroll_amount_jpy)
      || !nullableAmount(input.provider.bank_landed_amount_jpy)
      || (input.provider.latest_payroll_at !== null && !iso(input.provider.latest_payroll_at))
      || (input.provider.latest_bank_landed_at !== null && !iso(input.provider.latest_bank_landed_at))
      || !plain(input.runtime)
      || !iso(input.runtime.observed_at)
      || !(input.runtime.duration_ms === null || count(input.runtime.duration_ms))
      || !RUN_STATES.has(input.runtime.run_state)
      || typeof input.runtime.truth_verified !== "boolean") fail();

    const p = input.provider;
    const verifiedPayroll = p.coverage_status === "verified_payroll_receipt";
    const verifiedBank = p.coverage_status === "verified_bank_landed";
    const hasVerifiedIncome = verifiedPayroll || verifiedBank;
    if (p.coverage_status === "no_payroll_receipt"
      && (p.payroll_receipt_count !== 0 || p.bank_receipt_count !== 0
        || p.payroll_amount_jpy !== null || p.bank_landed_amount_jpy !== null
        || p.latest_payroll_at !== null || p.latest_bank_landed_at !== null)) fail();
    if (p.coverage_status === "unknown"
      && (p.payroll_receipt_count !== null || p.bank_receipt_count !== null
        || p.payroll_amount_jpy !== null || p.bank_landed_amount_jpy !== null
        || p.latest_payroll_at !== null || p.latest_bank_landed_at !== null)) fail();
    if (verifiedPayroll && (p.payroll_receipt_count === null || p.payroll_receipt_count < 1
      || p.payroll_amount_jpy === null || /^0(?:\.0*)?$/.test(p.payroll_amount_jpy))) fail();
    if (verifiedBank && (p.bank_receipt_count === null || p.bank_receipt_count < 1
      || p.bank_landed_amount_jpy === null || /^0(?:\.0*)?$/.test(p.bank_landed_amount_jpy))) fail();
    if (p.payroll_receipt_count !== null && p.payroll_receipt_count === 0
      && p.payroll_amount_jpy !== null) fail();
    if (p.bank_receipt_count !== null && p.bank_receipt_count === 0
      && p.bank_landed_amount_jpy !== null) fail();

    const exceptions = new Set([
      "employment_income_not_business_revenue",
      "job_posting_compensation_excluded",
      "bank_landed_unknown",
      "capital_unknown",
      "direct_cost_unknown",
      "human_cost_unknown",
      "profit_disabled_until_cost_reconciliation",
      "roi_disabled_until_cost_reconciliation",
      "income_scope_not_closed"
    ]);
    if (!hasVerifiedIncome) exceptions.add("payroll_receipt_missing");
    if (!verifiedBank) exceptions.add("bank_receipt_missing");
    if (input.runtime.run_state !== "SUCCEEDED" || !input.runtime.truth_verified) {
      exceptions.add("runtime_truth_unverified");
    }

    const payrollAmount = p.payroll_amount_jpy === null ? null : {
      currency: "JPY",
      amount_decimal: p.payroll_amount_jpy,
      evidence_status: "payroll_receipt"
    };
    const bankAmount = p.bank_landed_amount_jpy === null ? null : {
      currency: "JPY",
      amount_decimal: p.bank_landed_amount_jpy,
      evidence_status: "bank_receipt"
    };

    return freeze({
      schema_version: 1,
      financial_unit_id: "employment_income",
      observed_at: input.observed_at,
      status: "partial",
      scope: "personal_employment_income",
      employment_pipeline: {
        provider: "job_search",
        observed_at: p.observed_at,
        application_count: p.application_count,
        confirmed_application_count: p.confirmed_application_count,
        offer_count: p.offer_count,
        accepted_count: p.accepted_count,
        started_count: p.started_count,
        evidence_status: "application_funnel_only"
      },
      income: {
        coverage_status: p.coverage_status,
        payroll_receipt_count: p.payroll_receipt_count,
        bank_receipt_count: p.bank_receipt_count,
        payroll_amount: payrollAmount,
        bank_landed_amount: bankAmount,
        latest_payroll_at: p.latest_payroll_at,
        latest_bank_landed_at: p.latest_bank_landed_at,
        landed_cash_status: verifiedBank ? "confirmed_bank_landed" : "unknown",
        evidence_status: hasVerifiedIncome ? "provider_receipt" : "no_payroll_or_bank_receipt"
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

module.exports = { composeEmploymentBusinessFact };
