/**
 * bid.mjs — D2 autonomous BID rail (dealwork API, fully no-human).
 *
 * One bounded unit: pick ONE AI-doable dealwork job from the feed that we haven't
 * bid on yet, submit a tailored proposal via the dealwork API, record it (idempotent).
 * The loop's brain MAY supply {jobId, proposal, amount}; if absent the slot picks the
 * top unbid AI-doable job and uses a solid job-specific template (model-agnostic).
 *
 * Pure: pickJob() + buildProposal() (tested here). Effectful: postBid() (E2E task #10).
 * earn_usdc is ALWAYS 0 for a bid — earning is only counted at on-chain settle (record-earn).
 */
import fs from 'node:fs';
import { AI_HINT } from './ai-hint.mjs';


export function loadBidLedger(file) {
  const set = new Set();
  try {
    for (const l of fs.readFileSync(file, 'utf8').split('\n')) {
      if (!l.trim()) continue;
      try { set.add(String(JSON.parse(l).jobId)); } catch {}
    }
  } catch {}
  return set;
}

/** Pick ONE dealwork AI-doable job not already bid. Returns job or null. */
export function pickJob(feed, alreadyBid) {
  const bid = alreadyBid instanceof Set ? alreadyBid : new Set(alreadyBid || []);
  const jobs = (feed && feed.jobs) || [];
  for (const j of jobs) {
    if (j.rail !== 'dealwork') continue;             // dealwork = pure no-human API rail
    if (bid.has(String(j.id))) continue;             // idempotent: never double-bid
    if (!AI_HINT.test(String(j.title || ''))) continue;
    return j;
  }
  return null;
}

/** Tailored proposal from the job (used when the brain doesn't supply one). */
export function buildProposal(job) {
  const t = String(job.title || 'this task');
  return (
    `I can deliver "${t}" end-to-end with web + API + compute, no human needed. ` +
    `I read the full brief + acceptance criteria first, produce the concrete deliverable ` +
    `(working code / structured report / clean dataset / docs as applicable), self-check it ` +
    `against your criteria, and hand over files + a short README so you can verify immediately. ` +
    `Fast turnaround, clear updates, one revision included.`
  );
}

/** Record a bid (for idempotency) ONLY when it actually succeeded — a failed POST stays
 *  retryable on a later wake (FIND-004). Single source of the recording rule. */
export function shouldRecordBid(result) {
  return !!(result && result.ok === true);
}

/** Effectful: POST the bid to dealwork. Returns {ok, status, bidId|err}. */
export async function postBid({ apiKey, jobId, proposal, amount = '40', hours = 2 }) {
  try {
    const r = await fetch(`https://dealwork.ai/api/v1/jobs/${jobId}/bids`, {
      method: 'POST',
      headers: { Authorization: 'Bearer ' + apiKey, 'Content-Type': 'application/json', 'User-Agent': 'anicca-gig/1.0' },
      body: JSON.stringify({ proposedAmount: String(amount), estimatedHours: Number(hours), proposalText: proposal }),
      signal: AbortSignal.timeout(25000),
    });
    const text = await r.text();
    let bidId = null; try { bidId = JSON.parse(text)?.data?.id || null; } catch {}
    return { ok: r.status >= 200 && r.status < 300, status: r.status, bidId, body: text.slice(0, 200) };
  } catch (e) {
    return { ok: false, status: 0, err: String(e).slice(0, 120) };
  }
}
