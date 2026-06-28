#!/usr/bin/env node
// research-product.mjs — $0 web-research digest for the x402 seller.
// Zero paid keys, zero config, works on ANY fresh install:
//   query -> HN Algolia search (free JSON API, no key, no bot-block) -> top story URLs
//         -> Jina Reader r.jina.ai (free read) -> JSON digest.
// Used as X402_PRODUCT_CMD: a buyer pays USDC, gets real curated web research. No twitterapi/firecrawl/LLM key.
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36';

// Free, reliable, no-key, non-bot-blocked search (tech-relevant — the x402 buyer audience).
async function hnSearch(query) {
  const r = await fetch(
    'https://hn.algolia.com/api/v1/search?tags=story&hitsPerPage=8&query=' + encodeURIComponent(query),
  );
  if (!r.ok) throw new Error('hn ' + r.status);
  const j = await r.json();
  return (j.hits || [])
    .filter((h) => h.url && /^https?:\/\//.test(h.url))
    .map((h) => ({ title: h.title || '', url: h.url, points: h.points || 0 }));
}

async function jinaRead(url) {
  const r = await fetch('https://r.jina.ai/' + url, { headers: { 'User-Agent': UA } });
  if (!r.ok) throw new Error('jina ' + r.status);
  return (await r.text()).slice(0, 4000);
}

export async function research(query) {
  const q = String(query || '').trim();
  if (!q) throw new Error('empty query');
  const hits = await hnSearch(q);
  if (hits.length === 0) throw new Error('no search results');
  const parts = [];
  const used = [];
  for (const h of hits.slice(0, 3)) {
    try {
      const body = await jinaRead(h.url);
      if (body && body.trim()) {
        parts.push('## SOURCE: ' + h.title + ' — ' + h.url + '\n' + body);
        used.push({ title: h.title, url: h.url, points: h.points });
      }
    } catch { /* skip a failed source, try the next */ }
  }
  if (parts.length === 0) throw new Error('all source reads failed');
  return { query: q, sources: used, digest: parts.join('\n\n---\n\n') };
}

// CLI entrypoint
const isEntry = import.meta.url === ('file://' + process.argv[1]);
if (isEntry) {
  const q = process.argv.slice(2).join(' ');
  if (!q.trim()) { console.error('usage: research-product.mjs <query>'); process.exit(2); }
  research(q)
    .then((out) => process.stdout.write(JSON.stringify(out)))
    .catch((e) => { console.error(String(e && e.message ? e.message : e)); process.exit(1); });
}
