// reconcile.mjs — WALLET-ANCHORED LEDGER TRUTH (SSOT §10 N1 / TASKLIST #2).
//
// The earn-ledger only ever recorded WINS (redeem payouts); the original buy (cash out) and LOSING
// positions ($0 resolve) were never ledgered (redeem.py:172). Result: ledger showed +$10 while the
// wallet was actually -$7.84. This module fixes that by anchoring the ledger to the ONE truth —
// on-chain wallet balance. Each wake it reads the real balance and books a "reconcile" line for the
// drift between (actual wallet delta) and (real-earn nets recorded since the last snapshot). Losses
// therefore ALWAYS land in the ledger as a negative reconcile line, and by construction:
//     sum(all net_usdc of THIS wallet since a snapshot)  ==  actual wallet delta.
//
// A reconcile line is NEVER external:true — it is a truth anchor (may be + or -), not a proven
// external earn, so it can never create a false GATE-0 green. Realized-P&L readers (fitness /
// reporting) DO include it so losses count.
//
// WALLET-SCOPED (#2): a single ledger file can hold rows from more than one wallet (e.g. pm's
// __REPO_ROOT__/skills/earn/state/earn-ledger.jsonl carries both 0x904b pm rows and stray contaminant
// rows). When `ownWallet` is given, snapshot + earn-since are computed ONLY over rows whose wallet
// matches it (case-insensitive) — otherwise another wallet's rows would corrupt this wallet's drift
// math. Omit `ownWallet` for a single-wallet file (backward-compatible, unfiltered).
import { appendLedger, readLedger } from "../../_shared/lib/ledger.mjs";

const round = (n) => Math.round(Number(n) * 1e6) / 1e6; // 6dp USDC, kill fp noise
export const EPS = 0.01; // ignore sub-cent dust so we don't churn the ledger every wake

// PURE: keep only rows belonging to `ownWallet` (case-insensitive). ownWallet falsy -> all rows
// (single-wallet file). A row with no wallet field is excluded when a filter is requested (a
// reconcile line always carries its wallet, and every real pm earn row carries 0x904b).
export function scopeToWallet(rows, ownWallet) {
  if (!ownWallet) return rows || [];
  const w = String(ownWallet).toLowerCase();
  return (rows || []).filter((r) => r && String(r.wallet || "").toLowerCase() === w);
}

// PURE: drift that must be booked = actual wallet delta − real-earn already recorded since snapshot.
// A negative drift = unrecorded loss/cost (a naked leg resolving to $0). Positive = unrecorded gain
// or an external deposit.
export function computeDrift(currentBalance, lastSnapshotBalance, recordedEarnSinceUsd) {
  const actualDelta = Number(currentBalance) - Number(lastSnapshotBalance);
  return round(actualDelta - Number(recordedEarnSinceUsd || 0));
}

// PURE: sum net_usdc of REAL-earn lines (non-reconcile) recorded strictly after `sinceTs`.
export function recordedEarnSince(rows, sinceTs) {
  return round((rows || [])
    .filter((r) => r && r.source !== "reconcile" && Number(r.ts) > Number(sinceTs))
    .reduce((s, r) => s + Number(r.net_usdc || 0), 0));
}

// PURE: the most recent reconcile snapshot {ts, balance_after}, or null if none yet.
export function lastSnapshot(rows) {
  const recon = (rows || []).filter((r) => r && r.source === "reconcile" && r.balance_after != null);
  return recon.length ? recon[recon.length - 1] : null;
}

// PURE: assemble the reconcile ledger line (appended raw — deriveLine would strip balance_after).
export function buildReconcileLine(wallet, drift, currentBalance, ts) {
  return {
    ts: ts ?? Math.floor(Date.now() / 1000),
    wallet,
    source: "reconcile",
    task: drift < 0 ? "unrecorded loss/cost (wallet truth)" : "unrecorded gain/deposit (wallet truth)",
    earn_usdc: 0,
    cost_usdc: 0,
    net_usdc: round(drift),
    balance_after: round(currentBalance),
    // deliberately NO external:true — truth anchor, not a proven external earn.
  };
}

// I/O: read ledger, read real on-chain balance via injected `fetchBalance(wallet)`, book the drift.
// `fetchBalance` is injected so this module stays unit-testable with a mock. Fail-closed: a failed
// balance read books nothing. `ownWallet` (optional) scopes snapshot+earn-since to that wallet's rows.
export async function reconcile(wallet, ledgerPath, fetchBalance, nowTs, ownWallet) {
  const allRows = await readLedger(ledgerPath);
  const rows = scopeToWallet(allRows, ownWallet); // #2: only this wallet's history drives the math
  const current = await fetchBalance(wallet);
  if (typeof current !== "number" || !Number.isFinite(current)) {
    return { ok: false, reason: "balance-fetch-failed" };
  }
  const snap = lastSnapshot(rows);
  if (!snap) {
    // First ever: lay the baseline anchor (net 0) so future drifts are measured from real balance.
    const line = buildReconcileLine(wallet, 0, current, nowTs);
    await appendLedger(ledgerPath, line);
    return { ok: true, baseline: true, balance: current, drift: 0 };
  }
  const earnSince = recordedEarnSince(rows, snap.ts);
  const drift = computeDrift(current, snap.balance_after, earnSince);
  if (Math.abs(drift) < EPS) {
    return { ok: true, drift: 0, balance: current, note: "no material drift" };
  }
  const line = buildReconcileLine(wallet, drift, current, nowTs);
  await appendLedger(ledgerPath, line);
  return { ok: true, drift, balance: current };
}
