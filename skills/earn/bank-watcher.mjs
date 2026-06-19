// bank-watcher.mjs — A3 wiring: the daemon pass for ③ bank-direct. Reads method=bank recipients,
// plans + dispatches via runBankPayout, marks paid ONLY for rails that actually succeeded (idempotent,
// no-fake: a recipient is "paid" only after its rail's adapter returns ok). All deps INJECTED so this
// is unit-tested without a live token / DB; production wires the real reader, JPY pool, markPaid, and
// the real provider adapters (gmo-furikomi.submitBulkTransfer + token) — that live run is the E2E proof.
//
// Invariant (資金決済法): own-funds 給付 only.

import { runBankPayout } from "./bank-payout.mjs";

// deps: { readBankRecipients()->[{id,provider,currency,bank}], getPool()->int(JPY), markPaid(id,info),
//         claim(ids)->mark 'processing' BEFORE submit (idempotency), revert(id)->back to 'queued' on a
//         failed rail, adapters:{gmo,...}, opts }
// IDEMPOTENCY (FIND-002): claim() marks recipients non-queued BEFORE the adapter fires, so if submit
// succeeds but markPaid later fails, they are NOT re-read as queued next pass → no double-pay. Only a
// FAILED rail is reverted to queued for retry. claim/revert default to no-ops (unit tests inject them).
export async function bankWatcherPass({ readBankRecipients, getPool, markPaid, claim = async () => {}, revert = async () => {}, adapters = {}, opts = {} } = {}) {
  const recipients = await readBankRecipients();
  if (!Array.isArray(recipients) || recipients.length === 0) {
    return { outcome: "idle", reason: "no_bank_recipients", paid: [] };
  }
  const pool = await getPool();
  // FIND-003: activate the balance guard — distributing must never exceed the available pool.
  const guardedOpts = { ...opts, balance: Number.isInteger(opts.balance) ? opts.balance : pool };
  const out = await runBankPayout({
    pool,
    recipients,
    opts: guardedOpts,
    adapters,
    beforeDispatch: (transfers) => claim(transfers.map((t) => t.to)), // FIND-002: claim before submit
  });
  if (out.outcome === "skipped") return { outcome: "skipped", reason: out.reason, paid: [] };

  const okProviders = new Set(out.results.filter((r) => r.ok).map((r) => r.provider));
  const paid = [];
  for (const t of out.plan.transfers) {
    if (okProviders.has(t.provider)) {
      const res = out.results.find((r) => r.provider === t.provider);
      await markPaid(t.to, { provider: t.provider, amount: t.amount, currency: t.currency, res: res && res.res });
      paid.push(t.to);
    } else {
      await revert(t.to); // failed rail → back to queued for retry (claimed→queued)
    }
  }
  return { outcome: out.outcome, paid, results: out.results };
}
