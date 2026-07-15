// CDP Bazaar の実カタログから「何がいくらで売られているか」を測る（我々の物ではなく市場全体）
const LIMIT = 100; let offset = 0, total = Infinity, seen = 0;
const rows = [];
while (offset < total && offset < 3000) {
  const url = `https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources?limit=${LIMIT}&offset=${offset}`;
  const r = await fetch(url, { signal: AbortSignal.timeout(25_000) });
  if (!r.ok) { console.error("HTTP", r.status, "at", offset); break; }
  const j = await r.json();
  const items = j.items || []; total = j.pagination?.total ?? total; seen += items.length;
  for (const it of items) {
    const a = it.accepts?.[0] || {};
    rows.push({ res: it.resource || "", amt: Number(a.amount) || 0, desc: (a.description || "").slice(0, 70) });
  }
  if (!items.length) break;
  offset += items.length;
}
// 価格分布（amount は USDC の最小単位 = 1e-6）
const usd = rows.map(r => r.amt / 1e6).filter(v => v > 0).sort((a,b)=>a-b);
const q = p => usd[Math.floor(usd.length * p)] ?? 0;
console.log(JSON.stringify({ catalogTotal: total, scanned: seen, priced: usd.length,
  min: usd[0], p25: q(.25), median: q(.5), p75: q(.75), p90: q(.9), p99: q(.99), max: usd[usd.length-1] }, null, 1));
// 高額帯 = 実需がある証拠
console.log("\n--- 高額 top12（= 買い手が金を払う価値があると認めた物）");
[...rows].sort((a,b)=>b.amt-a.amt).slice(0,12).forEach(r =>
  console.log(`  $${(r.amt/1e6).toFixed(3).padStart(8)}  ${r.desc || r.res.slice(0,60)}`));
