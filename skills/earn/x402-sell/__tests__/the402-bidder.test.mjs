import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { openThe402Inbox } from '../lib/the402-inbox.mjs';
import { runThe402BidderOnce } from '../lib/the402-bidder.mjs';

const NOW_MS = 1_784_756_503_000;

test('bids only a matched open x402 research request and completes its durable event', async () => {
  const dir = mkdtempSync(join(tmpdir(), 'anicca-the402-bidder-'));
  const inbox = openThe402Inbox(join(dir, 'inbox.sqlite'));
  try {
    inbox.enqueue({
      eventId: 'request.created:post_match',
      type: 'request.created',
      payload: { type: 'request.created', posting_id: 'post_match' },
      receivedAtMs: NOW_MS,
    });
    const calls = [];
    const result = await runThe402BidderOnce({
      inbox,
      apiKey: 'sk_test_agent_only',
      researchServiceId: 'svc_research',
      explainerServiceId: 'svc_explainer',
      nowMs: NOW_MS,
      fetchImpl: async (url, init = {}) => {
        calls.push({ url, init });
        if (!init.method) {
          return Response.json({
            posting_id: 'post_match',
            status: 'open',
            category: 'research',
            title: 'Research x402 adoption for AI agents',
            brief: { objective: 'Compare machine-payment adoption' },
            budget_min_usd: 1,
            budget_max_usd: 10,
          });
        }
        return Response.json({ bid_id: 'bid_match', status: 'pending' }, { status: 201 });
      },
    });

    assert.deepEqual(result, {
      worked: true,
      eventId: 'request.created:post_match',
      status: 'bid',
      postingId: 'post_match',
      bidId: 'bid_match',
    });
    assert.equal(calls.length, 2);
    assert.equal(calls[0].url, 'https://api.the402.ai/v1/postings/post_match');
    assert.equal(calls[1].url, 'https://api.the402.ai/v1/postings/post_match/bids');
    assert.deepEqual(JSON.parse(calls[1].init.body), {
      price_usd: 3,
      eta_hours: 1,
      service_id: 'svc_research',
      pitch: 'Automated evidence-backed x402 adoption brief with primary-source links and the requested structure.',
    });
    assert.equal(inbox.audit('request.created:post_match').status, 'completed');
  } finally {
    inbox.close();
    rmSync(dir, { recursive: true, force: true });
  }
});

test('skips an unrelated request without posting a bid', async () => {
  const dir = mkdtempSync(join(tmpdir(), 'anicca-the402-bidder-skip-'));
  const inbox = openThe402Inbox(join(dir, 'inbox.sqlite'));
  try {
    inbox.enqueue({
      eventId: 'request.created:post_unrelated',
      type: 'request.created',
      payload: { type: 'request.created', posting_id: 'post_unrelated' },
      receivedAtMs: NOW_MS,
    });
    let calls = 0;
    const result = await runThe402BidderOnce({
      inbox,
      apiKey: 'sk_test_agent_only',
      researchServiceId: 'svc_research',
      explainerServiceId: 'svc_explainer',
      nowMs: NOW_MS,
      fetchImpl: async () => {
        calls += 1;
        return Response.json({
          posting_id: 'post_unrelated',
          status: 'open',
          category: 'research',
          title: 'Research local restaurant menus',
          brief: { objective: 'Compare seasonal lunch menus' },
          budget_min_usd: 1,
          budget_max_usd: 10,
        });
      },
    });

    assert.equal(result.status, 'skipped');
    assert.equal(calls, 1);
    assert.equal(inbox.audit('request.created:post_unrelated').status, 'completed');
  } finally {
    inbox.close();
    rmSync(dir, { recursive: true, force: true });
  }
});
