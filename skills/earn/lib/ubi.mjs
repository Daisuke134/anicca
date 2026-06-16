// ubi.mjs — pure UBI decision core. Given a PROFITABLE earn line + recipient sets + config,
// it computes the distribution plan (who, how much each, idempotency, dry/skip reasons).
// No network, no fs writes here (distribute-ubi.mjs does IO; execute-ubi.py does the on-chain send).
//
// CONSTITUTIONAL WALL (spec 28 §3): UBI distributes ONLY Anicca's OWN earnings to recipient WALLETS.
// Inputs are wallet addresses + numbers — NEVER a user email/name/phone/calendar. This module has no
// access to, and no parameter for, any user identity. It is the earn-side of the wall by construction.
import { isProfitable } from "./ledger.mjs";
import { shareBaseUnits, splitPool, toBaseUnits } from "./transfer.mjs";

const ADDR_RE = /^0x[0-9a-fA-F]{40}$/;
const norm = (a) => String(a).toLowerCase();

// Build the recipient list: active sibling-AI child wallets ∪ human allow-list, deduped,
// with the sender (Anicca's own wallet) excluded. Invalid addresses are dropped (fail-closed).
export function buildRecipients({ childWallets = [], humanWallets = [], sender }) {
  const senderLc = sender ? norm(sender) : null;
  const seen = new Set();
  const out = [];
  for (const a of [...childWallets, ...humanWallets]) {
    if (typeof a !== "string" || !ADDR_RE.test(a)) continue;
    const lc = norm(a);
    if (lc === senderLc || seen.has(lc)) continue;
    seen.add(lc);
    out.push(a);
  }
  return out;
}

// alreadyDone: has this funding wake already been distributed (or explicitly skipped/dry)?
export function alreadyDone(ubiLines, wake) {
  return (ubiLines || []).some(
    (l) => l && l.wake === wake && (l.kind === "ubi") &&
      (l.outcome === "done" || l.outcome === "skipped" || l.outcome === "dry"),
  );
}

// planUbi: the single decision fn run.sh's bridge calls. Returns a plan object; it NEVER sends.
//   fundingLine : the just-recorded earn line (must be isProfitable()).
//   recipients  : output of buildRecipients (addresses only).
//   cfg         : { shareBps, minPoolUsdc, dryRun, walletBalanceUsdc }
//   ubiLines    : prior ubi-ledger lines (for idempotency).
export function planUbi({ fundingLine, recipients, cfg = {}, ubiLines = [] }) {
  const shareBps = Number.isInteger(cfg.shareBps) ? cfg.shareBps : 1000; // 10.00%
  const minPoolUsdc = Number(cfg.minPoolUsdc ?? 0.10);
  const wake = fundingLine && fundingLine.wake;
  if (!fundingLine || !isProfitable(fundingLine)) {
    return { outcome: "skipped", reason: "funding_not_profitable", wake, transfers: [] };
  }
  if (alreadyDone(ubiLines, wake)) {
    return { outcome: "skipped", reason: "already_distributed", wake, transfers: [] };
  }
  const poolBase = shareBaseUnits(fundingLine.net_usdc, shareBps);
  const poolUsdc = Number(poolBase) / 1e6;
  if (poolUsdc < minPoolUsdc) {
    return { outcome: "skipped", reason: "below_min_pool", wake, pool_usdc: poolUsdc, transfers: [] };
  }
  if (!recipients || recipients.length === 0) {
    return { outcome: "skipped", reason: "no_recipients", wake, pool_usdc: poolUsdc, transfers: [] };
  }
  // never overspend: if the live wallet balance can't cover the pool, abort (no partial spend).
  if (cfg.walletBalanceUsdc != null && toBaseUnits(cfg.walletBalanceUsdc) < poolBase) {
    return { outcome: "skipped", reason: "insufficient_balance", wake, pool_usdc: poolUsdc, transfers: [] };
  }
  const { per, dust } = splitPool(poolBase, recipients.length);
  if (per <= 0n) {
    return { outcome: "skipped", reason: "per_recipient_zero", wake, pool_usdc: poolUsdc, transfers: [] };
  }
  const transfers = recipients.map((to) => ({ to, amount_base: per.toString() }));
  return {
    outcome: cfg.dryRun ? "dry" : "send",
    wake,
    share_bps: shareBps,
    pool_usdc: poolUsdc,
    pool_base: poolBase.toString(),
    per_base: per.toString(),
    dust_base: dust.toString(),
    transfers,
  };
}
