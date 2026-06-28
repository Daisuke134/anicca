#!/usr/bin/env node
// research-product.mjs — $0 web-research digest for the x402 seller.
// Zero paid keys, zero config, works on ANY fresh install. UNIVERSAL (not tech-only):
//   query -> [Wikipedia opensearch (general knowledge) + HN Algolia (tech/current)] merged, deduped
//         -> Jina Reader r.jina.ai (free read, with 429 backoff + content-quality gate)
//         -> JSON {query, sources, digest}.
// Used as X402_PRODUCT_CMD: a buyer pays USDC, gets real curated web research. No twitterapi/firecrawl/LLM key.
// Sources NOT used: DuckDuckGo/Bing/Google HTML — they bot-block keyless access (verified 2026-06-28).
import { pathToFileURL } from 'node:url';

const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// --- free, no-key, non-bot-blocked search backends ---
async function wikiSearch(query) {
  const u = 'https://en.wikipedia.org/w/api.php?action=opensearch&format=json&limit=4&search=' + encodeURIComponent(query);
  const r = await fetch(u, { headers: { 'User-Agent': UA } });
  if (!r.ok) return [];
  const j = await r.json();
  const titles = j[1] || [];
  const urls = j[3] || [];
  return urls.map((url, i) => ({ title: titles[i] || url, url })).filter((h) => /^https?:\/\//.test(h.url));
}
async function hnSearch(query) {
  const r = await fetch('https://hn.algolia.com/api/v1/search?tags=story&hitsPerPage=6&query=' + encodeURIComponent(query));
  if (!r.ok) return [];
  const j = await r.json();
  return (j.hits || [])
    .filter((h) => h.url && /^https?:\/\//.test(h.url))
    .map((h) => ({ title: h.title || h.url, url: h.url }));
}
async function search(query) {
  const [wiki, hn] = await Promise.all([wikiSearch(query).catch(() => []), hnSearch(query).catch(() => [])]);
  // interleave general (wiki) + tech/current (hn); dedup by url
  const merged = [];
  const seen = new Set();
  const max = Math.max(wiki.length, hn.length);
  for (let i = 0; i < max; i++) {
    for (const h of [wiki[i], hn[i]]) {
      if (h && !seen.has(h.url)) { seen.add(h.url); merged.push(h); }
    }
  }
  return merged;
}

// --- free reader with 429 backoff + content-quality gate (reject Jina error/placeholder bodies) ---
const ERROR_BODY_RE = /rate limit|too many requests|429|error code\s*\d|"code"\s*:\s*4|authentication is required|could not be reached/i;
function isRealContent(body) {
  if (!body || body.trim().length < 300) return false;
  if (ERROR_BODY_RE.test(body.slice(0, 400))) return false;
  return true;
}
async function jinaRead(url) {
  for (let attempt = 0; attempt < 3; attempt++) {
    const r = await fetch('https://r.jina.ai/' + url, { headers: { 'User-Agent': UA } });
    if (r.status === 429) { await sleep(1500 * (attempt + 1)); continue; }
    if (!r.ok) throw new Error('jina ' + r.status);
    const body = (await r.text()).slice(0, 4000);
    if (!isRealContent(body)) throw new Error('jina returned non-content/placeholder body');
    return body;
  }
  throw new Error('jina rate-limited (429) after retries');
}

export async function research(query) {
  const q = String(query || '').trim();
  if (!q) throw new Error('empty query');
  const hits = await search(q);
  if (hits.length === 0) throw new Error('no search results');
  const parts = [];
  const used = [];
  for (const h of hits) {
    if (used.length >= 3) break;
    try {
      const body = await jinaRead(h.url);
      parts.push('## SOURCE: ' + h.title + ' — ' + h.url + '\n' + body);
      used.push({ title: h.title, url: h.url });
    } catch { /* skip a failed/placeholder source, try the next */ }
  }
  if (parts.length === 0) throw new Error('all source reads failed (rate-limited or no real content)');
  return { query: q, sources: used, digest: parts.join('\n\n---\n\n') };
}

// CLI entrypoint — pathToFileURL handles spaces/non-ASCII paths correctly
const isEntry = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isEntry) {
  const q = process.argv.slice(2).join(' ');
  if (!q.trim()) { console.error('usage: research-product.mjs <query>'); process.exit(2); }
  research(q)
    .then((out) => process.stdout.write(JSON.stringify(out)))
    .catch((e) => { console.error(String(e && e.message ? e.message : e)); process.exit(1); });
}
