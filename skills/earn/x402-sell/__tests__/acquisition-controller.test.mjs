import { test } from 'node:test';
import assert from 'node:assert/strict';

import { runAcquisitionCycle } from '../lib/acquisition-controller.mjs';

const NOW_MS = 1_784_771_200_000;

test('each acquisition cycle durably enqueues at most one unseen eligible posting', async () => {
  const events = new Map();
  const actions = [];
  const inbox = {
    audit: (eventId) => events.get(eventId) || null,
    enqueue: (event) => {
      events.set(event.eventId, { status: 'pending' });
      return { accepted: true, duplicate: false, eventId: event.eventId, status: 'pending' };
    },
  };
  const postings = [
    { posting_id: 'post_unrelated', status: 'open', category: 'research', title: 'Compare restaurant menus', budget_min_usd: 1, budget_max_usd: 10 },
    { posting_id: 'post_research', status: 'open', category: 'research', title: 'Research x402 adoption for agents', budget_min_usd: 1, budget_max_usd: 10 },
    { posting_id: 'post_writing', status: 'open', category: 'writing', title: 'Explain HTTP 402 Payment Required', budget_min_usd: 1, budget_max_usd: 10 },
  ];
  let fetchCalls = 0;
  const fetchImpl = async () => {
    fetchCalls += 1;
    return Response.json({ data: { postings } });
  };
  const config = {
    inbox,
    apiKey: 'the402-secret',
    researchServiceId: 'svc_research',
    explainerServiceId: 'svc_explainer',
    fetchImpl,
    appendAction: (row) => actions.push(row),
  };

  const first = await runAcquisitionCycle({ ...config, nowMs: NOW_MS });
  const second = await runAcquisitionCycle({ ...config, nowMs: NOW_MS + 300_000 });

  assert.deepEqual(first, {
    action: 'enqueued_bid',
    postingId: 'post_research',
    eventId: 'request.created:post_research',
    openPostings: 3,
  });
  assert.deepEqual(second, {
    action: 'enqueued_bid',
    postingId: 'post_writing',
    eventId: 'request.created:post_writing',
    openPostings: 3,
  });
  assert.equal(events.size, 2);
  assert.equal(fetchCalls, 2);
  assert.deepEqual(actions, [
    { ts: new Date(NOW_MS).toISOString(), action: 'enqueue_bid', posting_id: 'post_research', event_id: 'request.created:post_research' },
    { ts: new Date(NOW_MS + 300_000).toISOString(), action: 'enqueue_bid', posting_id: 'post_writing', event_id: 'request.created:post_writing' },
  ]);
  assert.equal(JSON.stringify(actions).includes('title'), false);
});
