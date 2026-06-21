// ubi.mjs — pure UBI decision core. Given a PROFITABLE earn line + recipient sets + config,
// it computes the distribution plan (who, how much each, idempotency, dry/skip reasons).
// No network, no fs writes here (distribute-ubi.mjs does IO; execute-ubi.py does the on-chain send).
//
// CONSTITUTIONAL WALL (spec 28 §3): UBI distributes ONLY Anicca's OWN earnings to recipient WALLETS.
// Inputs are wallet addresses + numbers — NEVER a user email/name/phone/calendar. This module has no
// access to, and no parameter for, any user identity. It is the earn-side of the wall by construction.
import { isProfitable } from "../../_shared/lib/ledger.mjs";
import { shareBaseUnits, splitPool, toBaseUnits } from "../../_shared/lib/transfer.mjs";

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
  // CREATOR bucket (the operator who runs this anicca) — distinct from the UBI pool.
  // creatorWallet + creatorShareBps are per-anicca config (autonomous: the automaton may set them).
  const creatorWallet = (typeof cfg.creatorWallet === "string" && ADDR_RE.test(cfg.creatorWallet)
    && norm(cfg.creatorWallet) !== norm(fundingLine.wallet || "")) ? cfg.creatorWallet : null;
  const creatorShareBps = Number.isInteger(cfg.creatorShareBps) ? cfg.creatorShareBps : 0;
  const creatorBase = creatorWallet && creatorShareBps > 0
    ? shareBaseUnits(fundingLine.net_usdc, creatorShareBps) : 0n;
  const haveCreator = creatorBase > 0n;

  const poolBase = shareBaseUnits(fundingLine.net_usdc, shareBps);
  const poolUsdc = Number(poolBase) / 1e6;
  const poolPayable = poolUsdc >= minPoolUsdc && !!recipients && recipients.length > 0;
  // skip entirely only if NEITHER a creator payment NOR a payable pool exists.
  if (!poolPayable && !haveCreator) {
    const reason = poolUsdc < minPoolUsdc ? "below_min_pool" : "no_recipients";
    return { outcome: "skipped", reason, wake, pool_usdc: poolUsdc, transfers: [] };
  }
  // never overspend: live balance must cover creator + pool TOGETHER (no partial spend).
  const totalBase = creatorBase + (poolPayable ? poolBase : 0n);
  if (cfg.walletBalanceUsdc != null && toBaseUnits(cfg.walletBalanceUsdc) < totalBase) {
    return { outcome: "skipped", reason: "insufficient_balance", wake, pool_usdc: poolUsdc, transfers: [] };
  }
  const transfers = [];
  if (haveCreator) transfers.push({ to: creatorWallet, amount_base: creatorBase.toString(), bucket: "creator" });
  let per = 0n, dust = 0n;
  if (poolPayable) {
    ({ per, dust } = splitPool(poolBase, recipients.length));
    if (per > 0n) for (const to of recipients) transfers.push({ to, amount_base: per.toString(), bucket: "ubi" });
  }
  if (transfers.length === 0) {
    return { outcome: "skipped", reason: "per_recipient_zero", wake, pool_usdc: poolUsdc, transfers: [] };
  }
  return {
    outcome: cfg.dryRun ? "dry" : "send",
    wake,
    share_bps: shareBps,
    creator_share_bps: creatorShareBps,
    creator_base: creatorBase.toString(),
    pool_usdc: poolUsdc,
    pool_base: poolBase.toString(),
    per_base: per.toString(),
    dust_base: dust.toString(),
    transfers,
  };
}
