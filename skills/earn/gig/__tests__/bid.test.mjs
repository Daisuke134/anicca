// node:test — BID rail pure logic (RED). Real POST is the E2E wake (#10).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { pickJob, buildProposal, loadBidLedger } from '../lib/bid.mjs';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const feed = { jobs: [
  { rail: 'laborx', id: 'L1', title: 'Python script' },          // not dealwork → skip
  { rail: 'dealwork', id: 'D1', title: 'Logo design' },          // not AI-doable text → skip
  { rail: 'dealwork', id: 'D2', title: 'Python data pipeline' }, // ← pick this
  { rail: 'dealwork', id: 'D3', title: 'Web scraping' },
] };

test('pickJob selects the first unbid AI-doable dealwork job', () => {
  const j = pickJob(feed, new Set());
  assert.equal(j.id, 'D2');
});

test('pickJob is idempotent — skips already-bid jobs (no double-bid)', () => {
  const j = pickJob(feed, new Set(['D2']));
  assert.equal(j.id, 'D3');
});

test('pickJob returns null when nothing biddable', () => {
  assert.equal(pickJob({ jobs: [{ rail: 'dealwork', id: 'X', title: 'painting' }] }, new Set()), null);
  assert.equal(pickJob({ jobs: [] }, new Set()), null);
});

test('buildProposal is tailored (contains the job title) and substantial', () => {
  const p = buildProposal({ title: 'Python data pipeline' });
  assert.ok(p.includes('Python data pipeline'));
  assert.ok(p.length > 120);
});

test('loadBidLedger reads recorded jobIds for idempotency', () => {
  const f = path.join(os.tmpdir(), 'bids-' + Date.now() + '.jsonl');
  fs.writeFileSync(f, JSON.stringify({ jobId: 'D2', ts: 1 }) + '\n' + JSON.stringify({ jobId: 'D5', ts: 2 }) + '\n');
  const s = loadBidLedger(f);
  assert.ok(s.has('D2') && s.has('D5') && !s.has('D9'));
});
