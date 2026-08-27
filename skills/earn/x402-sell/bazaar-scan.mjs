// scan the whole CDP Bazaar discovery catalog (offset pagination) for our resources
const NEEDLE = process.argv[2] || "tail7a0ba4";
const LIMIT = 100;
let offset = 0, total = Infinity, seen = 0;
const ours = [];
while (offset < total) {
  const url = `https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources?limit=${LIMIT}&offset=${offset}`;
  const r = await fetch(url, { signal: AbortSignal.timeout(20_000) });
  if (!r.ok) { console.error("HTTP", r.status, "at offset", offset); break; }
  const j = await r.json();
  const items = j.items || [];
  total = j.pagination?.total ?? total;
  seen += items.length;
  for (const it of items) if ((it.resource || "").includes(NEEDLE)) ours.push(it);
  if (!items.length) break;
  offset += items.length;
}
console.log(JSON.stringify({ scanned: seen, catalogTotal: total, oursCount: ours.length }));
for (const o of ours)
  console.log(JSON.stringify({ resource: o.resource, amount: o.accepts?.[0]?.amount, payTo: o.accepts?.[0]?.payTo, lastUpdated: o.lastUpdated }));
