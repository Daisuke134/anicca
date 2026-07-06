// earn-guard.mjs — P1: earn>spend fail-closed CUMULATIVE accounting
// (.vcsdd/features/anicca-agent-economy/specs/SPEC.md §3 P1 / §4 "earn>spend fail-closed").
//
// ledger.mjs already derives PER-PASS net_usdc and classifies ONE pass as profitable
// (isProfitable, GATE-0). This module is the missing CUMULATIVE layer: it sums net_usdc
// across every pass a skill/agent has ever recorded and returns a fail-closed HALT signal
// the instant that running total would go negative (or the instant any matching line's
// numbers can't be trusted) — the invariant is 稼ぐ額 >>> 使う額 over TIME, not per pass.
//
// Pure arithmetic + a fail-closed gate only — this module makes NO trading/strategy
// judgment (which market/side/amount to earn) and never decides WHETHER to earn, only
// whether the agent/skill can still AFFORD to keep trying. Same discipline as
// is-self-funded.mjs / identity-guard.mjs: never throws, missing/malformed data DENIES.
import { readLedger } from "./ledger.mjs";

// "cumulative net must never go negative" (spec §3 P1: "負なら停止"). A skill can set a
// small positive reserveUsdc to stop BEFORE hitting exactly zero (a safety margin), but the
// default is the literal spec ask: halt only once the running total is truly negative.
export const DEFAULT_RESERVE_USDC = 0;

function matchesScope(line, scope) {
  if (!line || typeof line !== "object") return false;
  if (scope.wallet != null && line.wallet !== scope.wallet) return false;
  if (scope.source != null && line.source !== scope.source) return false;
  return true;
}

// A line is trustworthy only if the numbers ledger.mjs derived from it are real, finite
// numbers. deriveLine() never throws — Number(garbage) collapses to NaN, so a malformed
// earn_usdc/cost_usdc surfaces here as a non-finite net_usdc, not as a missing field.
function isTrustworthy(line) {
  return (
    Number.isFinite(line.earn_usdc) &&
    Number.isFinite(line.cost_usdc) &&
    Number.isFinite(line.net_usdc)
  );
}

/**
 * Pure: cumulative net_usdc across every ledger line matching `scope`.
 * @param {object[]} lines ledger rows (as returned by readLedger)
 * @param {{wallet?: string, source?: string}} [scope]
 * @returns {{cumulativeNet: number, trustworthy: boolean}} trustworthy=false means at least
 *   one matching line has unusable numbers — the caller MUST treat that as fail-closed, it
 *   is never safe to just skip the bad line and sum the rest (that would hide a real loss).
 */
export function cumulativeNet(lines, scope = {}) {
  let total = 0;
  let trustworthy = true;
  for (const line of Array.isArray(lines) ? lines : []) {
    if (!matchesScope(line, scope)) continue;
    if (!isTrustworthy(line)) {
      trustworthy = false;
      continue;
    }
    total += Number(line.net_usdc);
  }
  return { cumulativeNet: +total.toFixed(6), trustworthy };
}

/**
 * Pure: fail-closed HALT decision for ONE scope.
 * @param {object[]} lines
 * @param {{wallet?: string, source?: string}} scope
 * @param {number} [reserveUsdc]
 * @returns {{halt: boolean, reason: string|null, cumulativeNet: number|null}}
 */
export function evaluateScope(lines, scope, reserveUsdc = DEFAULT_RESERVE_USDC) {
  const { cumulativeNet: net, trustworthy } = cumulativeNet(lines, scope);
  if (!trustworthy) {
    // Can't verify solvency -> assume insolvent, never assume the bad line was harmless.
    return { halt: true, reason: "malformed-ledger-data", cumulativeNet: null };
  }
  if (net < reserveUsdc) {
    return { halt: true, reason: "cumulative-net-below-reserve", cumulativeNet: net };
  }
  return { halt: false, reason: null, cumulativeNet: net };
}

/**
 * The one gate an earn pass calls: per-SKILL (this wallet+source pair) AND per-AGENT (this
 * wallet across every source) cumulative net must BOTH clear the reserve. HALT if EITHER
 * scope fails (the conservative union) — a profitable skill can't mask an insolvent wallet,
 * and a solvent wallet can't hide one specific skill quietly bleeding it dry.
 * @param {object[]} lines
 * @param {{wallet?: string, source?: string, reserveUsdc?: number}} [opts]
 * @returns {{halt: boolean, reason: string|null, bySkill: object|null, byAgent: object|null}}
 */
export function evaluateHalt(lines, { wallet, source, reserveUsdc = DEFAULT_RESERVE_USDC } = {}) {
  const bySkill = source != null ? evaluateScope(lines, { wallet, source }, reserveUsdc) : null;
  const byAgent = wallet != null ? evaluateScope(lines, { wallet }, reserveUsdc) : null;
  const halted = [bySkill, byAgent].find((r) => r && r.halt);
  return {
    halt: Boolean(halted),
    reason: halted ? halted.reason : null,
    bySkill,
    byAgent,
  };
}

// I/O wrapper: read the ledger off disk, then run the pure gate. `ledgerPath` is always
// explicit (this module is shared by every skill/ledger, so it never guesses a default path
// the way earn/lib/record.mjs does for ITS OWN ledger).
export async function checkHalt(ledgerPath, { wallet, source, reserveUsdc } = {}) {
  const lines = await readLedger(ledgerPath);
  return evaluateHalt(lines, { wallet, source, reserveUsdc });
}

// --- CLI entrypoint: `node earn-guard.mjs check <wallet> <source> <ledgerPath> [reserveUsdc]`
// so bash run.sh wrappers can use this exactly like the existing kill-switch idiom:
//   if ! node .../_shared/lib/earn-guard.mjs check "$WLOW" "$SRC" "$LEDGER"; then exit 0; fi
// Pass "" for <source> to check the per-agent (wallet-only) scope alone (e.g. a generic
// top-of-wake gate that doesn't yet know which specific source this pass will use).
// Exit 0 = OK, exit 1 = HALT (reason on stderr), exit 2 = usage error. Never throws uncaught —
// any unexpected error while checking is itself treated as a HALT (fail-closed).
import path from "node:path";
import { fileURLToPath } from "node:url";

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [cmd, wallet, source, ledgerPath, reserveArg] = process.argv.slice(2);
  if (cmd !== "check" || !wallet || !ledgerPath) {
    process.stderr.write("usage: earn-guard.mjs check <wallet> <source|''> <ledgerPath> [reserveUsdc]\n");
    process.exitCode = 2;
  } else {
    const reserveUsdc = reserveArg !== undefined ? Number(reserveArg) : DEFAULT_RESERVE_USDC;
    checkHalt(ledgerPath, { wallet, source: source || undefined, reserveUsdc })
      .then((result) => {
        if (result.halt) {
          process.stderr.write(
            `HALT: ${result.reason} bySkill=${JSON.stringify(result.bySkill)} byAgent=${JSON.stringify(result.byAgent)}\n`
          );
          process.exitCode = 1;
        } else {
          process.stderr.write(
            `OK: bySkill=${JSON.stringify(result.bySkill)} byAgent=${JSON.stringify(result.byAgent)}\n`
          );
          process.exitCode = 0;
        }
      })
      .catch((e) => {
        process.stderr.write(`HALT: guard-error:${e.message}\n`);
        process.exitCode = 1;
      });
  }
}
