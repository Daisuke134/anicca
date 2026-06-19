// bank-watcher.mjs — A3 daemon pass for ③ JP bank-direct. SAFE-BY-DEFAULT orchestration for IRREVERSIBLE
// bank transfers. Designed against the double-pay failure modes an adversarial review found (FIND-A/B):
//
//   read queued → ATOMIC claim (only ids WE flipped queued→processing) → plan over claimed → dispatch.
//   - FIND-A: claim() must be an atomic compare-and-swap returning ONLY the ids it actually claimed, so two
//     overlapping passes can never both submit the same recipient. We dispatch ONLY the claimed subset.
//   - FIND-B: after a submit ATTEMPT the outcome is UNKNOWN (a bulk transfer may have been accepted before a
//     timeout). So on adapter failure we DO NOT re-queue — recipients stay 'processing' for reconciliation,
//     never auto-resubmitted. release() returns to 'queued' ONLY on a pre-dispatch skip (nothing was sent).
//   - markPaid sets 'submitted' (accepted ≠ 振込完了, FIND-005); a separate completion poll promotes →'paid'.
//
// Invariant (資金決済法): own-funds 給付 only.
import { planBankFanout, groupByProvider } from "./lib/bank-fanout.mjs";

// deps:
//   readBankRecipients() -> [{id,provider,currency,bank}]   (queued only)
//   claim(ids) -> claimedIds[]                               (ATOMIC CAS queued->processing; returns ids WE got)
//   release(ids) -> void                                     (processing->queued; ONLY safe pre-dispatch)
//   getBalance() -> int (our REAL available JPY)             (NOT a config cap)
//   markPaid(id, info) -> void                               (processing->submitted; never 'paid' here)
//   adapters: { gmo: async (transfers, opts) => res, ... }
//   opts: { reserve, minPer, feePerTransfer }
export async function bankWatcherPass({ readBankRecipients, getBalance, claim, release = async () => {}, markPaid, adapters = {}, opts = {} } = {}) {
  const recipients = await readBankRecipients();
  if (!Array.isArray(recipients) || recipients.length === 0) {
    return { outcome: "idle", reason: "no_bank_recipients", paid: [], failed: [] };
  }

  // FIND-A: atomic claim. Only the subset we actually flipped queued->processing proceeds.
  const claimedIds = new Set(await claim(recipients.map((r) => r.id)));
  const claimed = recipients.filter((r) => claimedIds.has(r.id));
  if (claimed.length === 0) {
    return { outcome: "idle", reason: "nothing_claimed", paid: [], failed: [] };
  }

  const balance = await getBalance();
  // FIND-C: guard against the REAL balance. balance flows into the planner's insufficient_balance guard.
  const plan = planBankFanout({ pool: balance, recipients: claimed, opts: { ...opts, balance } });
  if (plan.outcome !== "send") {
    await release(claimed.map((r) => r.id)); // nothing dispatched -> safe to return to the queue
    return { outcome: "skipped", reason: plan.reason, paid: [], failed: [] };
  }

  const groups = groupByProvider(plan.transfers);
  const paid = [];
  const failed = [];
  for (const [provider, transfers] of Object.entries(groups)) {
    const adapter = adapters[provider];
    if (typeof adapter !== "function") {
      transfers.forEach((t) => failed.push(t.to)); // no adapter -> stays 'processing', not paid (no fake)
      continue;
    }
    let res;
    try {
      res = await adapter(transfers, opts);
    } catch {
      // FIND-B: UNKNOWN outcome after a submit attempt — leave 'processing' for reconciliation, NEVER re-queue.
      transfers.forEach((t) => failed.push(t.to));
      continue;
    }
    // Adapter SUCCEEDED (money submitted). Record per-recipient; FIND-007: a markPaid failure here must NOT
    // re-queue or double-count — the row simply stays 'processing' and the reconciliation poll resolves it.
    for (const t of transfers) {
      try {
        await markPaid(t.to, { provider, amount: t.amount, currency: t.currency, res });
        paid.push(t.to);
      } catch {
        failed.push(t.to); // submitted but not recorded -> stays 'processing' -> reconcileStuck/pollCompletions
      }
    }
  }
  return { outcome: failed.length ? (paid.length ? "partial" : "failed") : "sent", paid, failed };
}
