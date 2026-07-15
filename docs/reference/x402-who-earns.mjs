// 「言い値」ではなく「誰が実際に受け取っているか」。payTo を集計する。
const LIMIT = 100; let offset = 0, total = Infinity;
const byPayTo = new Map();
while (offset < total && offset < 3000) {
  const r = await fetch(`https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources?limit=${LIMIT}&offset=${offset}`, { signal: AbortSignal.timeout(25_000) });
  if (!r.ok) break;
  const j = await r.json(); const items = j.items || []; total = j.pagination?.total ?? total;
  for (const it of items) {
    const a = it.accepts?.[0] || {};
    if (!a.payTo) continue;
    const k = a.payTo.toLowerCase();
    const e = byPayTo.get(k) || { n: 0, maxUsd: 0, host: "" };
    e.n++; e.maxUsd = Math.max(e.maxUsd, (Number(a.amount)||0)/1e6);
    try { e.host = new URL(it.resource).host; } catch {}
    byPayTo.set(k, e);
  }
  if (!items.length) break;
  offset += items.length;
}
console.log("--- 掲載数が多い payTo top10（= 本気で店を出してる主体）");
[...byPayTo.entries()].sort((a,b)=>b[1].n-a[1].n).slice(0,10)
  .forEach(([k,v]) => console.log(`  ${v.n.toString().padStart(4)}本  max$${v.maxUsd.toFixed(3).padStart(9)}  ${v.host.padEnd(30)} ${k.slice(0,10)}…`));
console.log(`\n  ユニーク payTo = ${byPayTo.size}（3000本中）`);
