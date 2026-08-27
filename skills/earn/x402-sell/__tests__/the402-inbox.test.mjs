import test from 'node:test';
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { mkdtempSync, rmSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { acceptThe402Webhook, openThe402Inbox } from '../lib/the402-inbox.mjs';

function withTempInbox(run) {
  const dir = mkdtempSync(join(tmpdir(), 'anicca-the402-inbox-'));
  try { return run(join(dir, 'inbox.sqlite')); }
  finally { rmSync(dir, { recursive: true, force: true }); }
}

test('durably deduplicates a verified event across process restarts', () => withTempInbox((dbPath) => {
  const event = {
    eventId: 'request.created:post_abc123',
    type: 'request.created',
    payload: { type: 'request.created', posting_id: 'post_abc123', title: 'Research x402' },
    receivedAtMs: 1_784_756_503_000,
  };

  const first = openThe402Inbox(dbPath);
  assert.equal(statSync(dbPath).mode & 0o777, 0o600);
  assert.deepEqual(first.enqueue(event), {
    accepted: true,
    duplicate: false,
    eventId: event.eventId,
    status: 'pending',
  });
  first.close();

  const reopened = openThe402Inbox(dbPath);
  assert.deepEqual(reopened.enqueue(event), {
    accepted: true,
    duplicate: true,
    eventId: event.eventId,
    status: 'pending',
  });
  assert.deepEqual(reopened.stats(), {
    total: 1,
    pending: 1,
    processing: 0,
    completed: 0,
    dead: 0,
  });
  reopened.close();
}));

test('leases one job at a time, reclaims expired work, and rejects a stale worker completion', () => withTempInbox((dbPath) => {
  const nowMs = 1_784_756_503_000;
  const inbox = openThe402Inbox(dbPath);
  inbox.enqueue({
    eventId: 'job_dispatch:job_abc123',
    type: 'job_dispatch',
    payload: { type: 'job_dispatch', job_id: 'job_abc123', brief: { objective: 'private' } },
    receivedAtMs: nowMs,
  });

  const first = inbox.claimNext({ nowMs, leaseMs: 1_000 });
  assert.equal(first.eventId, 'job_dispatch:job_abc123');
  assert.equal(first.attempt, 1);
  assert.equal(first.leaseUntilMs, nowMs + 1_000);
  assert.deepEqual(first.payload.brief, { objective: 'private' });
  assert.equal(inbox.claimNext({ nowMs: nowMs + 999, leaseMs: 1_000 }), null);

  const reclaimed = inbox.claimNext({ nowMs: nowMs + 1_000, leaseMs: 1_000 });
  assert.equal(reclaimed.eventId, first.eventId);
  assert.equal(reclaimed.attempt, 2);
  assert.notEqual(reclaimed.leaseToken, first.leaseToken);
  assert.deepEqual(inbox.complete({
    eventId: first.eventId,
    leaseToken: first.leaseToken,
    nowMs: nowMs + 1_001,
  }), { completed: false, eventId: first.eventId });
  assert.deepEqual(inbox.complete({
    eventId: reclaimed.eventId,
    leaseToken: reclaimed.leaseToken,
    nowMs: nowMs + 1_002,
  }), { completed: true, eventId: reclaimed.eventId });
  assert.equal(inbox.claimNext({ nowMs: nowMs + 2_001, leaseMs: 1_000 }), null);
  assert.deepEqual(inbox.stats(), {
    total: 1,
    pending: 0,
    processing: 0,
    completed: 1,
    dead: 0,
  });
  inbox.close();
}));

test('retries with a durable delay, dead-letters at the cap, and exposes only privacy-safe audit fields', () => withTempInbox((dbPath) => {
  const nowMs = 1_784_756_503_000;
  const inbox = openThe402Inbox(dbPath);
  inbox.enqueue({
    eventId: 'job_dispatch:job_retry',
    type: 'job_dispatch',
    payload: {
      type: 'job_dispatch',
      job_id: 'job_retry',
      brief: { objective: 'private buyer prompt' },
      callback_url: 'https://api.the402.ai/private-callback',
    },
    receivedAtMs: nowMs,
  });

  const first = inbox.claimNext({ nowMs, leaseMs: 1_000 });
  assert.deepEqual(inbox.fail({
    eventId: first.eventId,
    leaseToken: first.leaseToken,
    nowMs: nowMs + 100,
    retryDelayMs: 500,
    maxAttempts: 2,
    errorCode: 'upstream_timeout',
  }), { updated: true, eventId: first.eventId, status: 'pending', availableAtMs: nowMs + 600 });
  assert.equal(inbox.claimNext({ nowMs: nowMs + 599, leaseMs: 1_000 }), null);

  const second = inbox.claimNext({ nowMs: nowMs + 600, leaseMs: 1_000 });
  assert.equal(second.attempt, 2);
  assert.deepEqual(inbox.fail({
    eventId: second.eventId,
    leaseToken: second.leaseToken,
    nowMs: nowMs + 700,
    retryDelayMs: 500,
    maxAttempts: 2,
    errorCode: 'upstream_timeout',
  }), { updated: true, eventId: second.eventId, status: 'dead', availableAtMs: null });
  assert.equal(inbox.claimNext({ nowMs: nowMs + 10_000, leaseMs: 1_000 }), null);

  const audit = inbox.audit(second.eventId);
  assert.deepEqual(audit, {
    eventId: second.eventId,
    type: 'job_dispatch',
    status: 'dead',
    attempts: 2,
    receivedAtMs: nowMs,
    availableAtMs: null,
    leaseUntilMs: null,
    completedAtMs: null,
    lastErrorCode: 'upstream_timeout',
  });
  assert.doesNotMatch(JSON.stringify(audit), /private|prompt|callback|header|secret/i);
  assert.deepEqual(inbox.stats(), {
    total: 1,
    pending: 0,
    processing: 0,
    completed: 0,
    dead: 1,
  });
  inbox.close();
}));

test('authenticates before durable enqueue and returns no buyer payload or secret', () => withTempInbox((dbPath) => {
  const nowMs = 1_784_756_503_000;
  const apiKey = 'sk_test_agent_only';
  const webhookSecret = 'whsec_test_agent_only';
  const rawBody = JSON.stringify({
    type: 'job_dispatch',
    job_id: 'job_signed',
    brief: { objective: 'private buyer prompt' },
  });
  const timestamp = String(nowMs / 1_000);
  const signature = createHmac('sha256', webhookSecret)
    .update(`${timestamp}.${rawBody}`)
    .digest('hex');
  const headers = {
    'x-platform-secret': apiKey,
    'x-webhook-timestamp': timestamp,
    'x-webhook-signature': `sha256=${signature}`,
  };
  const inbox = openThe402Inbox(dbPath);

  const first = acceptThe402Webhook({
    inbox, rawBody, headers, apiKey, webhookSecret, nowMs,
  });
  assert.deepEqual(first, {
    ok: true,
    accepted: true,
    duplicate: false,
    type: 'job_dispatch',
    eventId: 'job_dispatch:job_signed',
    status: 'pending',
  });
  const duplicate = acceptThe402Webhook({
    inbox, rawBody, headers, apiKey, webhookSecret, nowMs,
  });
  assert.equal(duplicate.duplicate, true);
  assert.equal(inbox.stats().total, 1);
  assert.doesNotMatch(JSON.stringify({ first, duplicate }), /private|prompt|sk_test|whsec|signature/i);

  assert.throws(() => acceptThe402Webhook({
    inbox,
    rawBody,
    headers: { ...headers, 'x-webhook-signature': `sha256=${'0'.repeat(64)}` },
    apiKey,
    webhookSecret,
    nowMs,
  }), /the402 webhook rejected: signature mismatch/);
  assert.equal(inbox.stats().total, 1);
  inbox.close();
}));
