/**
 * deliver.mjs — detect ACCEPTED dealwork contracts that need a deliverable (V4 inbound).
 *
 * One bounded unit: query dealwork /contracts?role=worker, surface contracts in an
 * accepted/working state. The actual deliverable (code/report/etc.) is produced by the
 * loop's brain + tools (model judgment); this lib detects + surfaces, never fakes work.
 * No earn is claimed here — earning is counted only at on-chain settle (record-earn, #7).
 */

/** Pure: from a contracts payload, return the ones needing our delivery. */
export function pendingDeliveries(payload) {
  const list = (payload && (payload.data || payload.contracts)) || [];
  const ACTIVE = /accept|in[_-]?progress|working|active|hired|started/i;
  return list
    .filter(c => ACTIVE.test(String(c.status || '')))
    .map(c => ({ id: String(c.id), title: c.title || c.jobTitle || '', status: c.status,
                 amount: c.amount || c.agreedAmount || null }));
}

/** Effectful: fetch worker contracts from dealwork. */
export async function fetchContracts(apiKey) {
  try {
    const r = await fetch('https://dealwork.ai/api/v1/contracts?role=worker', {
      headers: { Authorization: 'Bearer ' + apiKey, Accept: 'application/json', 'User-Agent': 'anicca-gig/1.0' },
      signal: AbortSignal.timeout(20000),
    });
    if (!r.ok) return { ok: false, status: r.status, contracts: [] };
    return { ok: true, status: r.status, payload: await r.json() };
  } catch (e) {
    return { ok: false, status: 0, err: String(e).slice(0, 120), contracts: [] };
  }
}
