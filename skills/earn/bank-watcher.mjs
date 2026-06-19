// bank-watcher.mjs — A3 wiring: the daemon pass for ③ bank-direct. Reads method=bank recipients,
// plans + dispatches via runBankPayout, marks paid ONLY for rails that actually succeeded (idempotent,
// no-fake: a recipient is "paid" only after its rail's adapter returns ok). All deps INJECTED so this
// is unit-tested without a live token / DB; production wires the real reader, JPY pool, markPaid, and
// the real provider adapters (gmo-furikomi.submitBulkTransfer + token) — that live run is the E2E proof.
//
// Invariant (資金決済法): own-funds 給付 only.

import { runBankPayout } from "./bank-payout.mjs";

// deps: { readBankRecipients()->[{id,provider,currency,bank}], getPool()->int(JPY), markPaid(id,info),
//         adapters:{gmo,...}, opts }
export async function bankWatcherPass({ readBankRecipients, getPool, markPaid, adapters = {}, opts = {} } = {}) {
  const recipients = await readBankRecipients();
  if (!Array.isArray(recipients) || recipients.length === 0) {
    return { outcome: "idle", reason: "no_bank_recipients", paid: [] };
  }
  const pool = await getPool();
  const out = await runBankPayout({ pool, recipients, opts, adapters });
  if (out.outcome === "skipped") return { outcome: "skipped", reason: out.reason, paid: [] };

  const okProviders = new Set(out.results.filter((r) => r.ok).map((r) => r.provider));
  const paid = [];
  for (const t of out.plan.transfers) {
    if (!okProviders.has(t.provider)) continue;      // NO FAKE: only mark paid on a succeeded rail
    await markPaid(t.to, { provider: t.provider, amount: t.amount, currency: t.currency });
    paid.push(t.to);
  }
  return { outcome: out.outcome, paid, results: out.results };
}
