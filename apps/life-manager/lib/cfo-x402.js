"use strict";

const ERROR = "cfo_x402_invalid:business_fact";
const COVERAGE = new Set(["verified_external_settlements", "provider_reported_empty", "unknown"]);
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
function count(value) { return Number.isSafeInteger(value) && value >= 0; }
function nullableCount(value) { return value === null || count(value); }
function atomic(value) { return typeof value === "string" && /^(?:0|[1-9][0-9]*)$/.test(value) && value.length <= 40; }
function nullableAtomic(value) { return value === null || atomic(value); }
function usdDecimal(value) {
  const padded = value.padStart(7, "0");
  const whole = padded.slice(0, -6);
  const fraction = padded.slice(-6).replace(/0+$/, "");
  return fraction ? `${whole}.${fraction}` : whole;
}

/**
 * Projects finalized Base USDC x402 settlements into a privacy-safe CFO fact.
 * The input is a redacted summary produced by the existing observer; tx hashes,
 * wallet addresses, routes, and raw provider rows never cross this boundary.
 */
function composeX402BusinessFact(input) {
  try {
    if (!plain(input) || !iso(input.observed_at) || !plain(input.provider)
      || input.provider.name !== "x402" || input.provider.network !== "eip155:8453"
      || input.provider.asset !== "USDC" || input.provider.decimals !== 6
      || !iso(input.provider.observed_at) || !COVERAGE.has(input.provider.coverage_status)
      || !nullableCount(input.provider.settled_count) || !nullableCount(input.provider.external_count)
      || !nullableAtomic(input.provider.settled_usdc_atomic)
      || !nullableAtomic(input.provider.external_usdc_atomic)
      || !nullableCount(input.provider.self_transfer_count)
      || !nullableCount(input.provider.internal_move_count)
      || (input.provider.latest_settlement_at !== null && !iso(input.provider.latest_settlement_at))
      || !plain(input.runtime) || !iso(input.runtime.observed_at)
      || !(input.runtime.duration_ms === null || count(input.runtime.duration_ms))
      || !RUN_STATES.has(input.runtime.run_state) || typeof input.runtime.truth_verified !== "boolean") fail();

    const p = input.provider, verified = p.coverage_status === "verified_external_settlements";
    if (p.coverage_status === "provider_reported_empty"
      && (p.external_count !== 0 || p.external_usdc_atomic !== "0")) fail();
    if (verified && (!count(p.external_count) || p.external_count < 1 || !atomic(p.external_usdc_atomic) || p.external_usdc_atomic === "0")) fail();
    if (p.coverage_status === "unknown" && (p.external_count !== null || p.external_usdc_atomic !== null)) fail();
    if (count(p.settled_count) && count(p.external_count) && p.external_count > p.settled_count) fail();
    if (atomic(p.settled_usdc_atomic) && atomic(p.external_usdc_atomic) && BigInt(p.external_usdc_atomic) > BigInt(p.settled_usdc_atomic)) fail();

    const runtimeVerified = input.runtime.run_state === "SUCCEEDED" && input.runtime.truth_verified === true;
    const exceptions = new Set([
      "self_transfers_excluded", "internal_moves_excluded", "capital_unknown", "direct_api_cost_unknown",
      "human_cost_unknown", "profit_disabled_until_cost_reconciliation", "roi_disabled_until_cost_reconciliation",
      "x402_service_scope_not_closed"
    ]);
    if (!verified) exceptions.add("external_settlement_unknown");
    if (!runtimeVerified) exceptions.add("runtime_truth_unverified");

    return freeze({
      schema_version: 1,
      financial_unit_id: "x402_services",
      observed_at: input.observed_at,
      status: "partial",
      scope: "base_mainnet_external_inflow_ledger",
      settlement: {
        network: "eip155:8453",
        asset: "USDC",
        decimals: 6,
        coverage_status: p.coverage_status,
        settled_count: p.settled_count,
        external_count: p.external_count,
        settled_amount: p.settled_usdc_atomic === null ? null : { currency: "USD", amount_atomic: p.settled_usdc_atomic, amount_decimal: usdDecimal(p.settled_usdc_atomic) },
        external_amount: p.external_usdc_atomic === null ? null : { currency: "USD", amount_atomic: p.external_usdc_atomic, amount_decimal: usdDecimal(p.external_usdc_atomic) },
        latest_settlement_at: p.latest_settlement_at,
        landed_cash_status: verified ? "confirmed_agent_wallet" : "unknown",
        evidence_status: verified ? "onchain_finalized_external_settlement" : "unknown"
      },
      exclusions: {
        self_transfers: { status: "excluded", observed_count: p.self_transfer_count },
        internal_moves: { status: "excluded", observed_count: p.internal_move_count }
      },
      cost: {
        runtime: {
          coverage_status: runtimeVerified ? "verified" : input.runtime.duration_ms === null ? "unknown" : "measured_failed",
          observations: [{ observed_at: input.runtime.observed_at, duration_seconds: input.runtime.duration_ms === null ? null : String(input.runtime.duration_ms / 1000), evidence_status: runtimeVerified ? "runtime_measured" : "runtime_unverified" }]
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

module.exports = { composeX402BusinessFact };
