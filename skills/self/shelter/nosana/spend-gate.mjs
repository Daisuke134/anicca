// spend-gate.mjs — pure money-safety gate for Nosana job spend. Mirrors the cap semantics of
// skills/earn/funding/lib/caps.py (per-transfer / daily / cumulative caps, tx-hash dedupe with a
// status-priority "most terminal row wins" rule) applied to Nosana deploy spend instead of the
// claude-p -> Franklin funding pipeline. caps.py is Python and this executor is JS, so this is a
// deliberate parallel re-expression, not a shared import — unifying the two implementations into
// one cap engine is noted as follow-up work in README.md rather than attempted here.
//
// No I/O: every function takes already-fetched balances/history/config and returns plain data.

export const DEFAULT_MAX_SPEND_USD = 0.5;
export const DEFAULT_SOL_FEE_FLOOR = 0.005; // SOL reserved for tx fees, matches nosana CLI's own low-balance threshold

// caps.py's status precedence for dedupe-by-tx-hash: higher wins. "pending" = broadcast
// happened, confirmation not yet resolved (may already have moved real money — must still
// consume headroom, caps.py Finding A). "sent"/"settled" = confirmed terminal outcome.
const SPEND_STATUS_PRIORITY = { pending: 1, sent: 2, settled: 2 };

/**
 * Pure: rows from `history` that represent real (or possibly-real) NOS/USD outflow, counted
 * exactly once per tx (by txHash), keeping only the most-terminal status per hash. Rows with no
 * txHash (e.g. legacy/manual entries) are each counted individually — mirrors caps.py's
 * `_outflow_rows` exactly, translated to JS/camelCase field names.
 */
export function outflowRows(history) {
  const candidates = (history || []).filter(
    (r) => r && Object.prototype.hasOwnProperty.call(SPEND_STATUS_PRIORITY, r.status),
  );
  const bestByHash = new Map();
  const untracked = [];
  for (const r of candidates) {
    if (!r.txHash) {
      untracked.push(r);
      continue;
    }
    const prev = bestByHash.get(r.txHash);
    if (!prev || SPEND_STATUS_PRIORITY[r.status] > SPEND_STATUS_PRIORITY[prev.status]) {
      bestByHash.set(r.txHash, r);
    }
  }
  return [...untracked, ...bestByHash.values()];
}

/**
 * Pure: evaluate `amountUsd` against per-job / daily / cumulative USD caps in `config`, given a
 * spend history. Mirrors caps.py's `check_caps` exactly (same three checks, same ordering, same
 * "amount must be positive" precondition). Any of the three caps may be null/absent to mean
 * "no cap".
 *
 * @returns {{allowed: boolean, reason: string, amountUsd: number}}
 */
export function checkSpendCaps({ amountUsd, history = [], config = {}, nowTs }) {
  if (typeof amountUsd !== "number" || !Number.isFinite(amountUsd) || amountUsd <= 0) {
    return { allowed: false, reason: "amountUsd must be a positive number", amountUsd };
  }
  if (typeof nowTs !== "number" || !Number.isFinite(nowTs)) {
    return { allowed: false, reason: "nowTs must be a finite number (epoch seconds)", amountUsd };
  }

  const perJobCap = config.perJobUsdCap;
  if (perJobCap != null && amountUsd > perJobCap) {
    return {
      allowed: false,
      reason: `amount $${amountUsd} exceeds per-job cap $${perJobCap}`,
      amountUsd,
    };
  }

  const outflow = outflowRows(history);
  const dayAgo = nowTs - 86400;
  const dailySpent = outflow
    .filter((r) => Number(r.ts || 0) >= dayAgo)
    .reduce((sum, r) => sum + Number(r.amountUsd || 0), 0);
  const dailyCap = config.dailyUsdCap;
  if (dailyCap != null && dailySpent + amountUsd > dailyCap) {
    return {
      allowed: false,
      reason: `amount $${amountUsd} would exceed daily cap $${dailyCap} (already spent $${dailySpent} in the last 24h)`,
      amountUsd,
    };
  }

  const cumulativeSpent = outflow.reduce((sum, r) => sum + Number(r.amountUsd || 0), 0);
  const cumulativeCap = config.cumulativeUsdCap;
  if (cumulativeCap != null && cumulativeSpent + amountUsd > cumulativeCap) {
    return {
      allowed: false,
      reason: `amount $${amountUsd} would exceed cumulative cap $${cumulativeCap} (already spent $${cumulativeSpent} total)`,
      amountUsd,
    };
  }

  return { allowed: true, reason: "within all caps", amountUsd };
}

/**
 * Pure: the single combined preflight gate deploy.mjs consults before any spend — caps (via
 * checkSpendCaps) AND balance sufficiency (spec hard constraint 3: refuse if cost exceeds the
 * configured max spend, NOS balance is insufficient, or SOL balance is below the fee floor).
 * Fails closed on missing/non-finite balances rather than treating "unknown" as "zero cost is
 * fine".
 *
 * @param {{costUsd: number, costNos: number, solBalance: number, nosBalance: number, history?: Array, config?: object, nowTs: number}} opts
 * @returns {{allowed: boolean, reason: string}}
 */
export function evaluateSpendGate({
  costUsd,
  costNos,
  solBalance,
  nosBalance,
  history = [],
  config = {},
  nowTs,
}) {
  const effectiveConfig = {
    perJobUsdCap: config.perJobUsdCap ?? DEFAULT_MAX_SPEND_USD,
    dailyUsdCap: config.dailyUsdCap ?? null,
    cumulativeUsdCap: config.cumulativeUsdCap ?? null,
    solFeeFloor: config.solFeeFloor ?? DEFAULT_SOL_FEE_FLOOR,
  };

  const capDecision = checkSpendCaps({ amountUsd: costUsd, history, config: effectiveConfig, nowTs });
  if (!capDecision.allowed) {
    return { allowed: false, reason: capDecision.reason };
  }

  if (typeof costNos !== "number" || !Number.isFinite(costNos) || costNos <= 0) {
    return { allowed: false, reason: "costNos must be a positive number (fail-closed)" };
  }
  if (typeof nosBalance !== "number" || !Number.isFinite(nosBalance)) {
    return { allowed: false, reason: "nosBalance is unavailable (fail-closed)" };
  }
  if (nosBalance < costNos) {
    return {
      allowed: false,
      reason: `insufficient NOS balance: have ${nosBalance}, need ${costNos}`,
    };
  }

  if (typeof solBalance !== "number" || !Number.isFinite(solBalance)) {
    return { allowed: false, reason: "solBalance is unavailable (fail-closed)" };
  }
  if (solBalance < effectiveConfig.solFeeFloor) {
    return {
      allowed: false,
      reason: `SOL balance ${solBalance} is below the fee floor ${effectiveConfig.solFeeFloor}`,
    };
  }

  return { allowed: true, reason: "within caps and sufficient balances" };
}
