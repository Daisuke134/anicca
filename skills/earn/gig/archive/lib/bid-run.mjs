/**
 * bid-run.mjs — CLI: one BID bounded unit. Prints ONE structured JSON line.
 * argv: <feedFile> <bidsLedgerFile>. env: DEALWORK_API_KEY, GIG_JOB_ID?, GIG_PROPOSAL?,
 * GIG_AMOUNT?, WAKE_ID?. Idempotent: records each bid jobId; never double-bids.
 */
import fs from 'node:fs';
import { pickJob, buildProposal, loadBidLedger, postBid, shouldRecordBid } from './bid.mjs';

const [feedFile, bidsFile] = process.argv.slice(2);
const wake = process.env.WAKE_ID || String(Math.floor(Date.now() / 1000));
const key = process.env.DEALWORK_API_KEY || '';
const out = (o) => console.log(JSON.stringify({ source: 'gig', earn_usdc: 0, cost_usdc: 0, wake, ...o }));

let feed = { jobs: [] };
try { feed = JSON.parse(fs.readFileSync(feedFile, 'utf8')); } catch {}
const bid = loadBidLedger(bidsFile);

if (!key) { out({ task: 'bid-skip', reason: 'no_dealwork_key' }); process.exit(0); }

let job = null;
if (process.env.GIG_JOB_ID) job = (feed.jobs || []).find(j => String(j.id) === process.env.GIG_JOB_ID) || { id: process.env.GIG_JOB_ID, title: '' };
else job = pickJob(feed, bid);

if (!job) { out({ task: 'bid-skip', reason: 'no_biddable_job' }); process.exit(0); }
if (bid.has(String(job.id))) { out({ task: 'bid-skip', reason: 'already_bid', jobId: String(job.id) }); process.exit(0); }

const proposal = process.env.GIG_PROPOSAL || buildProposal(job);
const amount = process.env.GIG_AMOUNT || '40';

const r = await postBid({ apiKey: key, jobId: job.id, proposal, amount });
// Record for idempotency ONLY when the bid actually SUCCEEDED (r.ok). A failed POST must
// stay retryable on a later wake — recording intent would permanently skip it (FIND-004).
if (shouldRecordBid(r)) {
  try {
    fs.appendFileSync(bidsFile, JSON.stringify({ jobId: String(job.id), title: job.title, amount, status: r.status, bidId: r.bidId || null, ts: wake }) + '\n');
  } catch {}
}
out({ task: r.ok ? 'bid' : 'bid-failed', jobId: String(job.id), title: String(job.title || '').slice(0, 50), bid_ok: r.ok, http: r.status });
