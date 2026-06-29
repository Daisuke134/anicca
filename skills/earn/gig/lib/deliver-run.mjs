/**
 * deliver-run.mjs — CLI: detect accepted contracts (V4 inbound). Prints ONE JSON line.
 * env: DEALWORK_API_KEY, WAKE_ID?. No earn claimed (settle is #7). Surfaces work for the brain.
 */
import { fetchContracts, pendingDeliveries } from './deliver.mjs';

const wake = process.env.WAKE_ID || String(Math.floor(Date.now() / 1000));
const key = process.env.DEALWORK_API_KEY || '';
const out = (o) => console.log(JSON.stringify({ source: 'gig', earn_usdc: 0, cost_usdc: 0, wake, ...o }));

if (!key) { out({ task: 'deliver-skip', reason: 'no_dealwork_key' }); process.exit(0); }

const r = await fetchContracts(key);
if (!r.ok) { out({ task: 'deliver-skip', reason: 'fetch_failed', http: r.status }); process.exit(0); }
const pending = pendingDeliveries(r.payload);
out({ task: 'deliver-detect', pending: pending.length, contracts: pending.slice(0, 5).map(c => ({ id: c.id, status: c.status, title: String(c.title).slice(0, 40) })) });
