/**
 * detect.mjs — D2 verified-live detection for the earn/gig slot.
 *
 * Bounded, no-side-effect refresh: poll the VERIFIED-LIVE rails for AI-doable open jobs,
 * write state/guild_feed.json. Only rails we have actually onboarded + E2E-proven are
 * polled (dealwork API, LaborX public board). Dead/unverified rails (abillio etc.) are
 * NOT polled (D2: never pretend a dead rail works). Pure-ish: network in, file out; earns 0.
 *
 * Creds are read from the creds file (~/.openclaw/.env) — the loop scrubs *_WALLET_KEY
 * from env, and we never need a wallet key to DETECT (read-only public/auth-token calls).
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

const AI_HINT = /python|script|csv|json|data|scrap|research|seo|lead|writ|content|doc|code|review|translat|automat|bot|api|server|telegram|web|powerpoint|スライド|資料|記事|文字起こし|入力/i;

function readCreds(envFile) {
  const out = {};
  try {
    for (const line of fs.readFileSync(envFile, 'utf8').split('\n')) {
      const m = line.match(/^(?:export\s+)?([A-Z0-9_]+)=(.*)$/);
      if (m) out[m[1]] = m[2].replace(/^["']|["']$/g, '');
    }
  } catch {}
  return out;
}

async function dealworkJobs(creds) {
  const key = creds.DEALWORK_API_KEY;
  if (!key) return [];
  try {
    const r = await fetch('https://dealwork.ai/api/v1/jobs', {
      headers: { Authorization: 'Bearer ' + key, Accept: 'application/json', 'User-Agent': 'anicca-gig/1.0' },
      signal: AbortSignal.timeout(15000),
    });
    if (!r.ok) return [];
    const d = await r.json();
    const jobs = d.jobs || d.data || [];
    return jobs
      .filter(j => AI_HINT.test(String(j.title || '')))
      .map(j => ({ rail: 'dealwork', id: String(j.id), title: j.title, url: 'https://dealwork.ai/explore',
                   budget: j.fixedPrice || j.budgetMax || null, currency: 'USD' }));
  } catch { return []; }
}

async function laborxJobs() {
  // public SSR board, no login needed to DETECT
  try {
    const r = await fetch('https://laborx.com/jobs', { headers: { 'User-Agent': 'Mozilla/5.0' }, signal: AbortSignal.timeout(15000) });
    if (!r.ok) return [];
    const h = await r.text();
    const out = []; const seen = new Set();
    for (const blk of h.split(/class="[^"]*job-card[^"]*"/).slice(1)) {
      const hm = blk.match(/href="(\/jobs\/[a-z0-9-]+-\d+)"/i);
      if (!hm || seen.has(hm[1])) continue; seen.add(hm[1]);
      const tm = blk.match(new RegExp('href="' + hm[1].replace(/[/-]/g, '\\$&') + '"[^>]*>\\s*([^<]{4,90})'));
      const title = tm ? tm[1].trim() : hm[1].split('/').pop();
      if (AI_HINT.test(title)) out.push({ rail: 'laborx', id: hm[1].split('-').pop(), title, url: 'https://laborx.com' + hm[1], budget: null, currency: 'USD' });
    }
    return out;
  } catch { return []; }
}

export async function detect({ envFile, outFile } = {}) {
  const ef = envFile || path.join(os.homedir(), '.openclaw', '.env');
  const creds = readCreds(ef);
  const dw = await dealworkJobs(creds);
  // laborx detection re-enabled when its apply/deliver code lands (no pretended-live rail)
  const jobs = [...dw];
  const feed = { generated_at: Math.floor(Date.now() / 1000), counts: { total: jobs.length, dealwork: dw.length }, jobs };
  if (outFile) { fs.mkdirSync(path.dirname(outFile), { recursive: true }); fs.writeFileSync(outFile, JSON.stringify(feed, null, 1)); }
  return feed;
}

// CLI: node detect.mjs <outFile>  → prints counts line
if (import.meta.url === `file://${process.argv[1]}`) {
  const out = process.argv[2] || path.join(path.dirname(new URL(import.meta.url).pathname), '..', 'state', 'guild_feed.json');
  detect({ outFile: out }).then(f => console.log(`[gig] detect feed: total=${f.counts.total} dealwork=${f.counts.dealwork}`));
}
