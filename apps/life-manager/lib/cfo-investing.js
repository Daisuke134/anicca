"use strict";

const ERROR = "cfo_investing_invalid:business_fact";
const REALIZED_COVERAGE = new Set([
  "verified_append_only_ledger", "provider_reported_empty", "unknown",
]);
const MARK_TO_MARKET = new Set(["verified_mark_to_market", "unknown"]);
const CAPITAL_COVERAGE = new Set(["verified_capital_snapshot", "unknown"]);
const RECONCILIATION = new Set(["matched", "unknown"]);
const RUN_STATES = new Set(["SUCCEEDED", "FAILED", "UNKNOWN"]);
const AMOUNT = /^(?:0|[1-9][0-9]*)(?:\.[0-9]{1,8})?$/;
const SIGNED_AMOUNT = /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]{1,8})?$/;

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
function amount(value) { return typeof value === "string" && value.length <= 32 && AMOUNT.test(value); }
function nullableAmount(value) { return value === null || amount(value); }
function signedAmount(value) {
  return typeof value === "string" && value.length <= 32 && SIGNED_AMOUNT.test(value);
}
function nullableSignedAmount(value) { return value === null || signedAmount(value); }
function scaled(value) {
  const [whole, fraction = ""] = value.split(".");
  return BigInt(whole + fraction.padEnd(8, "0"));
}
function signedScaled(value) {
  if (value[0] !== "-") return scaled(value);
  return -scaled(value.slice(1));
}
function decimal(value) {
  const negative = value < 0n;
  const absolute = negative ? -value : value;
  const whole = absolute / 100000000n;
  const fraction = String(absolute % 100000000n).padStart(8, "0").replace(/0+$/, "");
  return `${negative ? "-" : ""}${whole}${fraction ? `.${fraction}` : ".00"}`;
}
function money(value, evidenceStatus) {
  return value === null ? null : {
    currency: "USD", amount_decimal: value, evidence_status: evidenceStatus,
  };
}

/**
 * Projects only reconciled realized investing P&L. Deposits, withdrawals,
 * internal moves, open positions, and wallet balances never become revenue.
 * A ledger receipt is not bank-landed cash, and absent cost/capital evidence
 * keeps contribution profit and ROI null for CFO-2c.
 */
function composeInvestingBusinessFact(input) {
  try {
    if (!plain(input) || !iso(input.observed_at) || !plain(input.provider)
      || input.provider.name !== "proprietary_investing"
      || input.provider.source_ledger !== "lm_agent_earnings"
      || !iso(input.provider.observed_at)
      || !REALIZED_COVERAGE.has(input.provider.realized_coverage_status)
      || !RECONCILIATION.has(input.provider.ledger_reconciliation_status)
      || !nullableCount(input.provider.realized_row_count)
      || !nullableAmount(input.provider.realized_profit_usd)
      || !nullableAmount(input.provider.realized_loss_usd)
      || !nullableAmount(input.provider.realized_fees_usd)
      || (input.provider.latest_realized_at !== null && !iso(input.provider.latest_realized_at))
      || !MARK_TO_MARKET.has(input.provider.unrealized_coverage_status)
      || !nullableSignedAmount(input.provider.unrealized_pnl_usd)
      || !CAPITAL_COVERAGE.has(input.provider.capital_coverage_status)
      || !nullableAmount(input.provider.capital_usd)
      || !nullableCount(input.provider.deposit_count)
      || !nullableCount(input.provider.withdrawal_count)
      || !nullableCount(input.provider.internal_move_count)
      || !plain(input.runtime) || !iso(input.runtime.observed_at)
      || !(input.runtime.duration_ms === null || count(input.runtime.duration_ms))
      || !RUN_STATES.has(input.runtime.run_state)
      || typeof input.runtime.truth_verified !== "boolean") fail();

    const p = input.provider;
    const verified = p.realized_coverage_status === "verified_append_only_ledger";
    const empty = p.realized_coverage_status === "provider_reported_empty";
    const receiptFields = [p.realized_row_count, p.realized_profit_usd, p.realized_loss_usd,
      p.realized_fees_usd, p.latest_realized_at];
    if (verified && (p.realized_row_count === null || p.realized_row_count < 1
      || p.realized_profit_usd === null || p.realized_loss_usd === null
      || p.realized_fees_usd === null || p.latest_realized_at === null
      || p.ledger_reconciliation_status !== "matched")) fail();
    if (empty && (p.realized_row_count !== 0 || p.realized_profit_usd !== "0.00"
      || p.realized_loss_usd !== "0.00" || p.realized_fees_usd !== "0.00"
      || p.latest_realized_at !== null || p.ledger_reconciliation_status !== "matched")) fail();
    if (p.realized_coverage_status === "unknown"
      && receiptFields.some((value) => value !== null) || p.realized_coverage_status === "unknown"
      && p.ledger_reconciliation_status !== "unknown") fail();
    if (p.realized_row_count === 0 && [p.realized_profit_usd, p.realized_loss_usd, p.realized_fees_usd]
      .some((value) => value !== "0.00")) fail();
    if (p.unrealized_coverage_status === "unknown" && p.unrealized_pnl_usd !== null) fail();
    if (p.unrealized_coverage_status === "verified_mark_to_market" && p.unrealized_pnl_usd === null) fail();
    if (p.capital_coverage_status === "unknown" && p.capital_usd !== null) fail();
    if (p.capital_coverage_status === "verified_capital_snapshot" && p.capital_usd === null) fail();

    const profit = verified || empty ? scaled(p.realized_profit_usd) : null;
    const loss = verified || empty ? scaled(p.realized_loss_usd) : null;
    const fees = verified || empty ? scaled(p.realized_fees_usd) : null;
    const net = profit === null ? null : profit - loss - fees;
    const runtimeVerified = input.runtime.run_state === "SUCCEEDED" && input.runtime.truth_verified;
    const exceptions = new Set([
      "deposits_withdrawals_internal_moves_excluded_from_revenue",
      "bank_landed_unknown", "direct_api_cost_unknown", "human_cost_unknown",
      "profit_disabled_until_cfo_2c_reconciliation", "roi_disabled_until_cfo_2c_reconciliation",
      "unrealized_not_realized_pnl", "investing_scope_not_closed",
    ]);
    if (!verified && !empty) exceptions.add("realized_receipt_unknown");
    if (p.unrealized_coverage_status === "unknown") exceptions.add("unrealized_mark_to_market_unknown");
    if (p.capital_coverage_status === "unknown") exceptions.add("capital_unknown");
    if ([p.deposit_count, p.withdrawal_count, p.internal_move_count].some((value) => value === null)) {
      exceptions.add("capital_flow_coverage_unknown");
    }
    if (!runtimeVerified) exceptions.add("runtime_truth_unverified");

    return freeze({
      schema_version: 1,
      financial_unit_id: "proprietary_investing",
      observed_at: input.observed_at,
      status: "partial",
      scope: "personal_proprietary_investing",
      realized_pnl: {
        coverage_status: p.realized_coverage_status,
        ledger_reconciliation_status: p.ledger_reconciliation_status,
        row_count: p.realized_row_count,
        profit: money(p.realized_profit_usd, "append_only_lm_agent_earnings"),
        loss: money(p.realized_loss_usd, "append_only_lm_agent_earnings"),
        fees: money(p.realized_fees_usd, "append_only_lm_agent_earnings"),
        net: net === null ? null : { currency: "USD", amount_decimal: decimal(net), evidence_status: "reconciled_realized_ledger" },
        latest_realized_at: p.latest_realized_at,
        landed_cash_status: "unknown",
        evidence_status: verified || empty ? "append_only_lm_agent_earnings" : "unknown",
      },
      unrealized: {
        coverage_status: p.unrealized_coverage_status,
        pnl: p.unrealized_pnl_usd === null ? null : money(p.unrealized_pnl_usd, "provider_mark_to_market"),
        excluded_from_realized_pnl: true,
      },
      capital: {
        coverage_status: p.capital_coverage_status,
        amount: money(p.capital_usd, "provider_capital_snapshot"),
      },
      exclusions: {
        deposits: { status: "excluded_from_revenue", observed_count: p.deposit_count },
        withdrawals: { status: "excluded_from_revenue", observed_count: p.withdrawal_count },
        internal_moves: { status: "excluded_from_revenue", observed_count: p.internal_move_count },
      },
      cost: {
        runtime: {
          coverage_status: runtimeVerified ? "verified"
            : input.runtime.duration_ms === null ? "unknown" : "measured_failed",
          observations: [{
            observed_at: input.runtime.observed_at,
            duration_seconds: input.runtime.duration_ms === null ? null : String(input.runtime.duration_ms / 1000),
            evidence_status: runtimeVerified ? "runtime_measured" : "runtime_unverified",
          }],
        },
        direct_api: { coverage_status: "unknown", amount: null },
        human: { coverage_status: "unknown", amount: null },
      },
      profit: null,
      roi: null,
      coverage_exceptions: [...exceptions].sort(),
    });
  } catch { throw new Error(ERROR); }
}

module.exports = { composeInvestingBusinessFact };
