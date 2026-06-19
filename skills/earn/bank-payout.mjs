// bank-payout.mjs — A3 orchestrator for ③ bank-direct UBI. Ties the pure planner (lib/bank-fanout.mjs)
// to provider adapters (gmo-furikomi / rain / fern). Plans WHO-gets-WHAT, groups by rail, dispatches each
// batch to its adapter. Adapters are INJECTED so the orchestration is unit-tested with mocks; production
// passes the real adapters (which need live tokens — gated, the watcher's "bank/card handled elsewhere").
//
// Invariant (資金決済法): own-funds 給付 only. This module never holds/intermediates third-party money.

import { planBankFanout, groupByProvider } from "./lib/bank-fanout.mjs";

// adapters: { gmo: async (transfers, opts) => result, rain: ..., fern: ... }
// beforeDispatch(transfers): optional hook run AFTER planning, BEFORE any adapter call — lets the caller
// "claim" recipients (mark processing) so a later mark-paid failure can't leave them re-payable (idempotency).
export async function runBankPayout({ pool, recipients = [], opts = {}, adapters = {}, beforeDispatch } = {}) {
  const plan = planBankFanout({ pool, recipients, opts });
  if (plan.outcome !== "send") return { outcome: plan.outcome, reason: plan.reason, plan, results: [] };

  if (typeof beforeDispatch === "function") await beforeDispatch(plan.transfers);

  const groups = groupByProvider(plan.transfers);
  const results = [];
  for (const [provider, transfers] of Object.entries(groups)) {
    const adapter = adapters[provider];
    if (typeof adapter !== "function") { results.push({ provider, ok: false, count: transfers.length, error: "no_adapter" }); continue; }
    try {
      const res = await adapter(transfers, opts);
      results.push({ provider, ok: true, count: transfers.length, res });
    } catch (e) {
      results.push({ provider, ok: false, count: transfers.length, error: String((e && e.message) || e) });
    }
  }
  const allOk = results.length > 0 && results.every((r) => r.ok);
  return { outcome: allOk ? "sent" : "partial", plan, results };
}
