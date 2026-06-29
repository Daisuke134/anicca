/**
 * detect.mjs — D2 verified-live detection for the earn/gig slot.
 *
 * Bounded, no-side-effect refresh: poll the VERIFIED-LIVE rails for AI-doable open jobs,
 * write state/guild_feed.json. Only rails we have actually onboarded + E2E-proven are
 * polled (dealwork API). Unverified/dead rails (abillio) and not-yet-coded rails (laborx) are
 * NOT polled (D2: never pretend a rail works before its action code exists). network in, file out; earns 0.
 *
 * Creds are read from the creds file (~/.openclaw/.env) — the loop scrubs *_WALLET_KEY
 * from env, and we never need a wallet key to DETECT (read-only public/auth-token calls).
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { AI_HINT } from './ai-hint.mjs';


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
