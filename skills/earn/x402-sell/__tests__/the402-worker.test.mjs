import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { openThe402Inbox } from '../lib/the402-inbox.mjs';
import { runThe402WorkerOnce } from '../lib/the402-worker.mjs';

const NOW_MS = 1_784_756_503_000;

function withTempInbox(run) {
  const dir = mkdtempSync(join(tmpdir(), 'anicca-the402-worker-'));
  const inbox = openThe402Inbox(join(dir, 'inbox.sqlite'));
  return Promise.resolve(run(inbox)).finally(() => {
    inbox.close();
    rmSync(dir, { recursive: true, force: true });
  });
}

test('processes only job dispatches and completes through the pinned callback', () => withTempInbox(async (inbox) => {
  inbox.enqueue({
    eventId: 'request.created:post_waiting',
    type: 'request.created',
    payload: { type: 'request.created', posting_id: 'post_waiting' },
    receivedAtMs: NOW_MS - 1,
  });
  inbox.enqueue({
    eventId: 'job_dispatch:job_abc123',
    type: 'job_dispatch',
    payload: {
      type: 'job_dispatch',
      job_id: 'job_abc123',
      thread_id: 'thread_abc123',
      brief: { objective: 'Research x402 adoption' },
      callback_url: 'https://api.the402.ai/v1/threads/thread_abc123/update',
      deadline: '2026-07-23T23:00:00.000Z',
    },
    receivedAtMs: NOW_MS,
  });

  const calls = [];
  let processorCalls = 0;
  const result = await runThe402WorkerOnce({
    inbox,
    apiKey: 'sk_test_agent_only',
    nowMs: NOW_MS,
    processJob: async ({ jobId, brief }) => {
      processorCalls += 1;
      assert.equal(jobId, 'job_abc123');
      assert.deepEqual(brief, { objective: 'Research x402 adoption' });
      return {
        deliverables: { summary: 'Evidence-backed x402 adoption brief' },
        notes: 'Automated research delivery',
      };
    },
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return new Response('{}', { status: 200 });
    },
  });

  assert.deepEqual(result, {
    worked: true,
    eventId: 'job_dispatch:job_abc123',
    status: 'completed',
    attempt: 1,
  });
  assert.equal(processorCalls, 1);
  assert.equal(calls.length, 2);
  assert.deepEqual(calls.map(({ url, init }) => ({
    url,
    method: init.method,
    apiKey: init.headers['X-API-Key'],
    contentType: init.headers['Content-Type'],
    body: JSON.parse(init.body),
  })), [
    {
      url: 'https://api.the402.ai/v1/threads/thread_abc123/update',
      method: 'POST',
      apiKey: 'sk_test_agent_only',
      contentType: 'application/json',
      body: { status: 'in_progress' },
    },
    {
      url: 'https://api.the402.ai/v1/threads/thread_abc123/update',
      method: 'POST',
      apiKey: 'sk_test_agent_only',
      contentType: 'application/json',
      body: {
        status: 'completed',
        deliverables: { summary: 'Evidence-backed x402 adoption brief' },
        notes: 'Automated research delivery',
      },
    },
  ]);
  assert.equal(inbox.audit('job_dispatch:job_abc123').status, 'completed');
  assert.equal(inbox.audit('request.created:post_waiting').status, 'pending');
}));
