// bank-fanout.mjs — pure planner for ③ bank-direct UBI: split a pooled amount across N recipients
// as integer fiat (JPY has no sub-unit; USD cents handled by caller in minor units), provider-agnostic.
// The live transfer is done by a provider adapter (gmo-furikomi.mjs / rain / fern); this module ONLY
// decides WHO gets HOW MUCH (deterministic, testable, no network). Mirrors lib/ubi.mjs planUbi but for fiat.
//
// Invariant (資金決済法, spec §entity-decision): we GIVE our OWN funds (贈与/給付) — never intermediate
// third-party money. This planner never moves money; it only computes a distribution of our own pool.

const isPosInt = (n) => Number.isInteger(n) && n > 0;

// recipient: { id, provider:'gmo'|'rain'|'fern', currency:'JPY'|'USD', bank:{...} }
// opts: { reserve (minor units kept back), minPer (skip if per < this), feePerTransfer (deducted from OUR
//         balance per transfer, NOT from recipient amount), balance (our available; guard) }
export function planBankFanout({ pool, recipients = [], opts = {} } = {}) {
  const reserve = Number.isInteger(opts.reserve) && opts.reserve >= 0 ? opts.reserve : 0;
  const minPer = Number.isInteger(opts.minPer) && opts.minPer >= 0 ? opts.minPer : 1;
  const fee = Number.isInteger(opts.feePerTransfer) && opts.feePerTransfer >= 0 ? opts.feePerTransfer : 0;

  if (!isPosInt(pool)) return { outcome: 'skipped', reason: 'invalid_pool', transfers: [] };
  const valid = recipients.filter((r) => r && r.id && r.provider && r.currency && r.bank);
  if (valid.length === 0) return { outcome: 'skipped', reason: 'no_recipients', transfers: [] };

  const distributable = pool - reserve;
  if (distributable <= 0) return { outcome: 'skipped', reason: 'below_reserve', transfers: [] };

  const n = valid.length;
  // per-recipient amount = floor((distributable - total fees) / n). Fees are OUR cost on top of payouts.
  const afterFees = distributable - fee * n;
  if (afterFees <= 0) return { outcome: 'skipped', reason: 'fees_exceed_pool', transfers: [] };
  const per = Math.floor(afterFees / n);
  if (per < minPer) return { outcome: 'skipped', reason: 'below_min_per', transfers: [], per };

  const transfers = valid.map((r) => ({ to: r.id, provider: r.provider, currency: r.currency, bank: r.bank, amount: per }));
  const payoutTotal = per * n;           // total to recipients
  const feeTotal = fee * n;              // our fee cost
  const spend = payoutTotal + feeTotal;  // total leaving our balance
  const dust = distributable - spend;    // remainder kept

  // balance guard (best-effort; the adapter re-checks before any real send)
  if (Number.isInteger(opts.balance) && spend > opts.balance) {
    return { outcome: 'skipped', reason: 'insufficient_balance', transfers: [], spend, balance: opts.balance };
  }

  return { outcome: 'send', transfers, per, count: n, payoutTotal, feeTotal, spend, dust, reserve };
}

// group transfers by provider so the watcher can call each adapter once (batch per rail).
export function groupByProvider(transfers = []) {
  return transfers.reduce((acc, t) => { (acc[t.provider] ||= []).push(t); return acc; }, {});
}
